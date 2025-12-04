#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test of Twelve Data API integration
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set API key
os.environ["TWELVE_DATA_API_KEY"] = "5dc774532eee4b2face0ef560e128713"

from utils.api_clients import TwelveDataClient
from config.markets import MARKETS

def test_twelve_data():
    """Test Twelve Data API with our 25 markets"""
    print("=" * 80)
    print("🔍 TESTING TWELVE DATA API")
    print("=" * 80)

    # Initialize client
    try:
        client = TwelveDataClient()
        print("✅ TwelveDataClient initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return

    # Test each category
    test_cases = [
        ("FOREX", MARKETS["FOREX"][0]),      # EUR/USD
        ("CRYPTO", MARKETS["CRYPTO"][0]),    # BTC/USDT
        ("INDEX", MARKETS["INDEX"][0]),      # SPX
        ("COMMODITY", MARKETS["COMMODITY"][0]),  # XAU/USD
        ("STOCK_CFD", MARKETS["STOCK_CFD"][0]),  # NVDA
    ]

    for category, symbol in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Testing {category}: {symbol}")
        print(f"{'=' * 60}")

        try:
            # Test quote endpoint
            quote = client.get_quote(symbol, category=category)
            print(f"✅ Quote received:")
            print(f"   Symbol: {quote['symbol']}")
            print(f"   Price: ${quote['price']:,.4f}")
            print(f"   Change: {quote['change_percent']:+.2f}%")
            print(f"   Volume: {quote['volume']:,.0f}")

            # Test time series endpoint
            candles = client.get_time_series(symbol, interval="1h", outputsize=50, category=category)
            if candles:
                print(f"✅ Time series received: {len(candles)} candles")
                print(f"   Last candle:")
                print(f"     Open: ${candles[-1]['open']:,.4f}")
                print(f"     High: ${candles[-1]['high']:,.4f}")
                print(f"     Low: ${candles[-1]['low']:,.4f}")
                print(f"     Close: ${candles[-1]['close']:,.4f}")
            else:
                print(f"⚠️  No time series data")

        except Exception as e:
            print(f"❌ Failed: {e}")

    print("\n" + "=" * 80)
    print("✅ TWELVE DATA TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_twelve_data()
