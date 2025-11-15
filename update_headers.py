#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets başlıklarını Türkçe'ye güncelle
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import create_header_row

def main():
    """Google Sheets başlıklarını güncelle"""
    print("🔄 Google Sheets başlıkları güncelleniyor...")

    # Get secrets
    sheet_id = get_secret("GOOGLE_SHEET_ID")
    sheet_tab = os.getenv("SHEET_TAB", "MarketData")

    # Get Google Sheets client
    gc = get_gspread_client()
    ws = gc.open_by_key(sheet_id).worksheet(sheet_tab)

    print(f"✓ Bağlantı kuruldu: {sheet_tab}")

    # Create Turkish headers
    turkish_headers = create_header_row()

    # Update first row
    print(f"✓ {len(turkish_headers)} sütun başlığı güncelleniyor...")
    ws.update('A1:AL1', [turkish_headers], value_input_option='RAW')

    print("✅ TAMAMLANDI! Google Sheets başlıkları Türkçe'ye çevrildi.")
    print("\nGüncellenen başlıklar:")
    for i, header in enumerate(turkish_headers[:27], 1):  # İlk 27 göster
        col_letter = chr(64 + i) if i <= 26 else f"A{chr(64 + i - 26)}"
        print(f"  {col_letter}: {header}")

if __name__ == "__main__":
    main()
