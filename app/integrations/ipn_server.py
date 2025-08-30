from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json
import sqlite3

from app.core import settings as core_settings, get_sqlite_connection


app = FastAPI()


def verify_signature(secret: str, payload: bytes, signature: str) -> bool:
    if not secret or not signature:
        return False
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha512).hexdigest()
    return hmac.compare_digest(mac, signature)


@app.post("/ipn/nowpayments")
async def nowpayments_ipn(request: Request):
    raw = await request.body()
    signature = request.headers.get('x-nowpayments-sig') or request.headers.get('X-Nowpayments-Sig')
    if not verify_signature(core_settings.NOWPAYMENTS_IPN_SECRET or '', raw, signature or ''):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        data = json.loads(raw.decode())
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    payment_id = data.get('payment_id')
    payment_status = data.get('payment_status')
    if not payment_id:
        raise HTTPException(status_code=400, detail="missing payment_id")

    conn = get_sqlite_connection(core_settings.DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT order_id, product_id, seller_user_id, seller_revenue, partner_code, platform_commission, partner_commission FROM orders WHERE nowpayments_id = ?', (payment_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"ok": True}

        order_id, product_id, seller_user_id, seller_revenue, partner_code, platform_commission, partner_commission = row

        if payment_status in ['finished', 'confirmed']:
            cursor.execute('UPDATE orders SET payment_status = "completed", completed_at = CURRENT_TIMESTAMP, file_delivered = TRUE WHERE nowpayments_id = ?', (payment_id,))
            cursor.execute('UPDATE products SET sales_count = sales_count + 1 WHERE product_id = ?', (product_id,))
            cursor.execute('UPDATE users SET total_sales = total_sales + 1, total_revenue = total_revenue + ? WHERE user_id = ?', (seller_revenue, seller_user_id))
            # Partenariat désactivé: ignorer commissions partenaire
            conn.commit()
        conn.close()
    except sqlite3.Error:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail="db error")

    return {"ok": True}

