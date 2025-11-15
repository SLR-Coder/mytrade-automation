#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets başlıklarını HEMEN güncelle
"""

import sys
sys.path.insert(0, '/workspace')

from utils.secrets import get_secret
from utils.auth import get_gspread_client

# Get sheet ID
sheet_id = get_secret("GOOGLE_SHEET_ID")

# Connect
gc = get_gspread_client()
ws = gc.open_by_key(sheet_id).worksheet("MarketData")

# Mevcut başlıkları al
current_headers = ws.row_values(1)

# Yeni başlıklar ekle (AJ'den itibaren)
new_headers = {
    36: "Qwen Sinyali",      # AJ
    37: "DeepSeek Sinyali",  # AK
    38: "Grok Sinyali",      # AL
    39: "Asistan AI",        # AM
    40: "Komuta Merkezi",    # AN
    41: "KM Gerekçesi",      # AO
    42: "Consensus %",       # AP
}

# Eksik kolonları doldur
while len(current_headers) < 42:
    current_headers.append("")

# Yeni başlıkları ekle
for col_idx, header in new_headers.items():
    current_headers[col_idx - 1] = header

# Güncelle
ws.update('A1:AP1', [current_headers[:42]])

print("✅ Google Sheets başlıkları güncellendi!")
print("\nEklenen başlıklar:")
for col_idx, header in new_headers.items():
    col_letter = chr(64 + (col_idx // 26)) + chr(64 + (col_idx % 26)) if col_idx > 26 else chr(64 + col_idx)
    if col_idx > 26:
        col_letter = 'A' + chr(64 + (col_idx - 26))
    print(f"  {col_letter}: {header}")
