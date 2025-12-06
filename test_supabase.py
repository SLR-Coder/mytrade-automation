#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test script for Supabase connection
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.supabase_client import (
    test_connection,
    insert_signal,
    get_batch_summary,
    generate_batch_id
)

def main():
    print("=" * 50)
    print("SUPABASE CONNECTION TEST")
    print("=" * 50)

    # Test 1: Connection
    print("\n[TEST 1] Testing connection...")
    if test_connection():
        print("✅ Connection successful!")
    else:
        print("❌ Connection failed!")
        return 1

    # Test 2: Insert a test signal
    print("\n[TEST 2] Inserting test signal...")
    test_data = {
        "market": "TEST/USDT",
        "price": 100.50,
        "volume": 1000000,
        "rsi": 55.5,
        "robot1_status": "completed"
    }

    result = insert_signal(test_data)
    if result:
        print(f"✅ Insert successful! ID: {result.get('id')}")
        print(f"   Batch ID: {result.get('batch_id')}")
    else:
        print("❌ Insert failed!")
        return 1

    # Test 3: Get batch summary
    print("\n[TEST 3] Getting batch summary...")
    batch_id = generate_batch_id()
    summary = get_batch_summary(batch_id)
    print(f"✅ Batch summary: {summary}")

    print("\n" + "=" * 50)
    print("ALL TESTS PASSED! Supabase is ready.")
    print("=" * 50)

    return 0

if __name__ == "__main__":
    exit(main())
