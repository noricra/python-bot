#!/usr/bin/env python3
"""
Script de diagnostic pour tester les currencies NOWPayments
Vérifie si 'usdtspl' est le bon code pour USDT sur Solana
"""

import os
import sys
from dotenv import load_dotenv

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from app.integrations.nowpayments_client import NowPaymentsClient

def main():
    api_key = os.getenv("NOWPAYMENTS_API_KEY")
    if not api_key:
        print("❌ NOWPAYMENTS_API_KEY not found in .env")
        return

    client = NowPaymentsClient(api_key)

    print("=" * 60)
    print("🔍 DIAGNOSTIC NOWPAYMENTS - SOLANA CURRENCIES")
    print("=" * 60)

    # Get all Solana currencies
    print("\n1️⃣ Fetching all Solana-related currencies from NOWPayments API...")
    sol_currencies = client.get_all_solana_currencies()

    if sol_currencies:
        print(f"\n✅ Found {len(sol_currencies)} Solana currencies:")
        for currency in sorted(sol_currencies):
            print(f"   - {currency}")

        # Check for USDT variants
        print("\n2️⃣ USDT Solana variants found:")
        usdt_variants = [c for c in sol_currencies if 'usdt' in c.lower()]
        if usdt_variants:
            for variant in usdt_variants:
                print(f"   ✓ {variant}")
        else:
            print("   ❌ No USDT Solana variant found")

        # Check for USDC variants
        print("\n3️⃣ USDC Solana variants found:")
        usdc_variants = [c for c in sol_currencies if 'usdc' in c.lower()]
        if usdc_variants:
            for variant in usdc_variants:
                print(f"   ✓ {variant}")
        else:
            print("   ❌ No USDC Solana variant found")

        # Check if our codes are correct
        print("\n4️⃣ Validation:")
        if 'usdtspl' in sol_currencies:
            print("   ✅ 'usdtspl' is VALID")
        else:
            print("   ❌ 'usdtspl' is NOT VALID")

        if 'usdcspl' in sol_currencies:
            print("   ✅ 'usdcspl' is VALID")
        else:
            print("   ❌ 'usdcspl' is NOT VALID")
    else:
        print("❌ Failed to fetch currencies")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
