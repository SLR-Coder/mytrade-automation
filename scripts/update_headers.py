# scripts/update_headers.py
# -*- coding: utf-8 -*-
"""
Google Sheets başlıklarını yeni V2.0 şemasına göre günceller
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import create_header_row

SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")


def update_headers():
    """Google Sheets başlıklarını güncelle"""
    print("=" * 60)
    print("GOOGLE SHEETS BAŞLIK GÜNCELLEYİCİ - V2.0")
    print("=" * 60)

    try:
        # Connect to Google Sheets
        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)

        print(f"\n✓ Google Sheets bağlantısı kuruldu: {SHEET_TAB}")

        # Get new headers
        headers = create_header_row()
        print(f"\n📊 {len(headers)} sütun başlığı hazırlandı:")

        # Print header groups
        print(f"\n  Bölüm 1 (A-T):   Robot 1 - Temel Göstergeler")
        print(f"  Bölüm 2 (U-AF):  Robot 1 - SMC Göstergeleri ← YENİ!")
        print(f"  Bölüm 3 (AG-AH): Robot 8 - Kişisel AI")
        print(f"  Bölüm 4 (AI-AR): Robot 3 - AI Sinyalleri")
        print(f"  Bölüm 5 (AS-AX): Robot 7 - Komuta Merkezi")
        print(f"  Bölüm 6 (AY-BD): Risk Yönetimi")
        print(f"  Bölüm 7 (BE-BH): Robot 9 - TP/SL Takip")
        print(f"  Bölüm 8 (BI-BJ): Notlar")
        print(f"  Bölüm 9 (BK-BS): Robot Durumları")

        # Update header row (row 1)
        print(f"\n⏳ Başlıklar güncelleniyor...")

        # Use batch update for efficiency
        ws.update('A1:BS1', [headers])

        print(f"\n✅ BAŞLIKLAR BAŞARIYLA GÜNCELLENDİ!")
        print(f"   Toplam sütun: {len(headers)} (A-BS)")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ HATA: {e}")
        raise


if __name__ == "__main__":
    update_headers()
