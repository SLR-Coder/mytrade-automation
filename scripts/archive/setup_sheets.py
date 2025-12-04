#!/usr/bin/env python3
# setup_sheets.py
# -*- coding: utf-8 -*-
"""
Google Sheets setup script for MyTrade
Creates a new spreadsheet with proper schema
"""

import sys
from utils.auth import get_gspread_client
from utils.schema import create_header_row

def setup_sheet(sheet_name: str = "MyTrade Automation"):
    """
    Create a new Google Sheet with MyTrade schema

    Args:
        sheet_name: Name for the new spreadsheet

    Returns:
        Spreadsheet ID
    """
    print("=" * 60)
    print("MYTRADE - GOOGLE SHEETS SETUP")
    print("=" * 60)

    try:
        # Get authenticated client
        print("Authenticating with Google Sheets...")
        gc = get_gspread_client()

        # Create new spreadsheet
        print(f"Creating new spreadsheet: {sheet_name}")
        spreadsheet = gc.create(sheet_name)
        sheet_id = spreadsheet.id

        print(f"✓ Spreadsheet created!")
        print(f"  ID: {sheet_id}")
        print(f"  URL: https://docs.google.com/spreadsheets/d/{sheet_id}")

        # Get first worksheet
        worksheet = spreadsheet.sheet1
        worksheet.update_title("MarketData")

        # Add headers
        print("Adding column headers...")
        headers = create_header_row()
        worksheet.update('A1', [headers])

        # Format header row (bold, freeze)
        worksheet.format('A1:AL1', {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
            "horizontalAlignment": "CENTER"
        })
        worksheet.freeze(rows=1)

        print("✓ Headers added and formatted")

        # Share with yourself (optional, for visibility)
        # spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')

        print("\n" + "=" * 60)
        print("SETUP COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nNext steps:")
        print(f"1. Add this Sheet ID to your secrets:")
        print(f"   echo -n '{sheet_id}' | gcloud secrets create GOOGLE_SHEET_ID --data-file=-")
        print(f"\n2. Or add to .env file:")
        print(f"   GOOGLE_SHEET_ID={sheet_id}")
        print(f"\n3. Open the sheet:")
        print(f"   https://docs.google.com/spreadsheets/d/{sheet_id}")
        print()

        return sheet_id

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup Google Sheets for MyTrade")
    parser.add_argument(
        "--name",
        default="MyTrade Automation",
        help="Name for the new spreadsheet"
    )

    args = parser.parse_args()
    setup_sheet(args.name)