import asyncio
import types
import pytest


from bot_mlt import MarketplaceBot


class DummyUser:
    def __init__(self, user_id: int):
        self.id = user_id


class DummyMessage:
    def __init__(self):
        self.last_text = None
        self.last_reply_markup = None
        self.last_parse_mode = None
        self.photos = []

    async def reply_text(self, text, reply_markup=None, parse_mode=None):
        self.last_text = text
        self.last_reply_markup = reply_markup
        self.last_parse_mode = parse_mode

    async def reply_photo(self, photo=None, caption=None):
        self.photos.append((photo, caption))


class DummyQuery:
    def __init__(self, user_id: int, data: str):
        self.from_user = DummyUser(user_id)
        self.data = data
        self.message = DummyMessage()
        self.last_text = None
        self.last_reply_markup = None
        self.last_parse_mode = None

    async def answer(self):
        return

    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        # Store last edit for assertions
        self.last_text = text
        self.last_reply_markup = reply_markup
        self.last_parse_mode = parse_mode


class DummyUpdate:
    def __init__(self, query: DummyQuery):
        self.callback_query = query
        # For some code paths, handlers read effective_user
        self.effective_user = query.from_user
        # And message path on update
        self.message = query.message


@pytest.mark.asyncio
async def test_buy_to_crypto_options_keyboard_contains_pay_buttons(tmp_path):
    bot = MarketplaceBot()

    # Prepare DB with a buyer and a product
    conn = bot.get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO users (user_id, username, first_name, language_code, is_seller)
        VALUES (?, ?, ?, ?, ?)
        """,
        (1001, "buyer", "Buyer", "fr", 0),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO users (user_id, username, first_name, language_code, is_seller, seller_name)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (2002, "seller", "Seller", "fr", 1, "Vendeur Test"),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO products (product_id, seller_user_id, title, description, category, price_eur, price_usd, main_file_path, file_size_mb, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """,
        (
            "TBF-TEST-001",
            2002,
            "Produit Test",
            "Description",
            "Dev",
            10.0,
            11.0,
            "/tmp/f.pdf",
            1.0,
        ),
    )
    conn.commit()
    conn.close()

    # Simulate pressing Buy on the product
    query = DummyQuery(1001, data="buy_product_TBF-TEST-001")
    update = DummyUpdate(query)

    await bot.button_handler(update, context=None)

    # After buy_product_ handler, show_crypto_options must be displayed with pay_* buttons
    assert query.last_reply_markup is not None, "Expected a keyboard on crypto options screen"
    kb = getattr(query.last_reply_markup, "inline_keyboard", [])
    # Flatten and check any button has callback_data starting with 'pay_'
    has_pay = any(
        getattr(btn, "callback_data", "").startswith("pay_")
        for row in kb
        for btn in row
    )
    assert has_pay, "Crypto options should contain pay_* buttons"


@pytest.mark.asyncio
async def test_pay_usdc_displays_payment_screen_with_check_button(tmp_path):
    bot = MarketplaceBot()

    # Seed DB
    conn = bot.get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO users (user_id, username, first_name, language_code, is_seller)
        VALUES (?, ?, ?, ?, ?)
        """,
        (1002, "buyer2", "Buyer2", "fr", 0),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO users (user_id, username, first_name, language_code, is_seller, seller_name)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (2003, "seller2", "Seller2", "fr", 1, "Vendeur 2"),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO products (product_id, seller_user_id, title, description, category, price_eur, price_usd, main_file_path, file_size_mb, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """,
        (
            "TBF-TEST-002",
            2003,
            "Produit Test 2",
            "Description 2",
            "Dev",
            15.0,
            16.5,
            "/tmp/f2.pdf",
            1.2,
        ),
    )
    conn.commit()
    conn.close()

    # First, go to buy on product to set state
    query1 = DummyQuery(1002, data="buy_product_TBF-TEST-002")
    update1 = DummyUpdate(query1)
    await bot.button_handler(update1, context=None)

    # Monkeypatch payment creation and FX rate
    def fake_create_payment(self, amount_usd: float, currency: str, order_id: str):
        return {"pay_amount": 5.0, "payment_id": "NPTEST", "pay_address": "0xABC"}

    def fake_get_exchange_rate(self) -> float:
        return 1.0

    bot.create_payment = types.MethodType(fake_create_payment, bot)
    bot.get_exchange_rate = types.MethodType(fake_get_exchange_rate, bot)

    # Then, simulate pressing a crypto (usdc)
    query2 = DummyQuery(1002, data="pay_usdc")
    update2 = DummyUpdate(query2)
    await bot.button_handler(update2, context=None)

    # Expect a payment screen with a check_payment_* button
    assert query2.last_reply_markup is not None, "Expected a keyboard on payment screen"
    kb = getattr(query2.last_reply_markup, "inline_keyboard", [])
    has_check = any(
        getattr(btn, "callback_data", "").startswith("check_payment_")
        for row in kb
        for btn in row
    )
    assert has_check, "Payment screen should contain check_payment_* button"

