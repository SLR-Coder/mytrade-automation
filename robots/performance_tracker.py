# -*- coding: utf-8 -*-
"""
Robot 6: Performance Tracker (Sheets-Based)
Tracks signal success and calculates performance metrics from Google Sheets
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

from config.constants import (
    SHEETS_RATE_LIMIT_SLEEP,
    DEFAULT_SHEET_TAB,
)
from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.common import parse_float, status_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-6-PerformanceTracker")

SHEET_TAB = os.getenv("SHEET_TAB", DEFAULT_SHEET_TAB)


def calculate_pnl_percent(entry: float, exit_price: float, signal: str) -> float:
    """Calculate P&L percentage"""
    if not entry or entry == 0:
        return 0.0

    if signal == "BUY":
        return ((exit_price - entry) / entry) * 100
    else:  # SELL
        return ((entry - exit_price) / entry) * 100


def run():
    """Main execution function for Robot 6"""
    logger.info("=" * 60)
    logger.info("ROBOT 6: PERFORMANCE TRACKER - STARTING")
    logger.info("=" * 60)

    try:
        # Initialize services
        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        logger.info(f"Connected to Google Sheet")

        # Read all rows
        all_rows = ws.get_all_values()

        if len(all_rows) < 2:
            logger.info("No data in sheet")
            return

        # Skip header row
        data_rows = all_rows[1:]

        # Track signals
        total_signals = 0
        buy_signals = 0
        sell_signals = 0
        hold_signals = 0

        # Closed positions
        tp1_hits = 0
        tp2_hits = 0
        sl_hits = 0
        closed_positions = 0
        open_positions = 0

        # For detailed tracking
        signal_details: List[Dict] = []

        for i, row in enumerate(data_rows, start=2):
            # Get final signal from Robot 7 (AS column)
            if len(row) <= cols.AS - 1:
                continue

            final_signal = row[cols.AS - 1] if len(row) > cols.AS - 1 else ""
            market = row[cols.B - 1] if len(row) > cols.B - 1 else ""

            # Skip separator rows and empty
            if not market or "📊" in market or "RAPORU" in market:
                continue

            if not final_signal:
                continue

            # Count by signal type
            if final_signal == "BUY":
                buy_signals += 1
                total_signals += 1
            elif final_signal == "SELL":
                sell_signals += 1
                total_signals += 1
            elif final_signal == "HOLD":
                hold_signals += 1
                continue  # Don't count HOLD in performance

            # Get TP/SL hit status (BE-BH columns)
            tp1_hit = row[cols.BE - 1] if len(row) > cols.BE - 1 else ""
            tp2_hit = row[cols.BF - 1] if len(row) > cols.BF - 1 else ""
            sl_hit = row[cols.BG - 1] if len(row) > cols.BG - 1 else ""
            position_status = row[cols.BH - 1] if len(row) > cols.BH - 1 else ""

            # Get entry/exit prices
            entry_str = row[cols.AY - 1] if len(row) > cols.AY - 1 else ""
            entry_price = parse_float(entry_str.replace("$", "").replace(",", "")) if entry_str else None

            # Track position status
            if position_status == "CLOSED":
                closed_positions += 1

                if tp1_hit == "YES":
                    tp1_hits += 1
                if tp2_hit == "YES":
                    tp2_hits += 1
                if sl_hit == "YES":
                    sl_hits += 1

                signal_details.append({
                    "market": market,
                    "signal": final_signal,
                    "tp1_hit": tp1_hit == "YES",
                    "tp2_hit": tp2_hit == "YES",
                    "sl_hit": sl_hit == "YES",
                    "outcome": "WIN" if (tp1_hit == "YES" or tp2_hit == "YES") else "LOSS"
                })
            else:
                open_positions += 1

        # Calculate metrics
        successful_signals = tp1_hits + tp2_hits  # At least one TP hit
        failed_signals = sl_hits

        # Win rate (only for closed positions)
        if closed_positions > 0:
            win_rate = (len([s for s in signal_details if s['outcome'] == 'WIN']) / closed_positions) * 100
        else:
            win_rate = 0.0

        # Display results
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 PERFORMANS RAPORU")
        logger.info("=" * 60)
        logger.info("")
        logger.info(f"📈 TOPLAM SİNYALLER:")
        logger.info(f"  ├─ Toplam: {total_signals}")
        logger.info(f"  ├─ BUY: {buy_signals}")
        logger.info(f"  ├─ SELL: {sell_signals}")
        logger.info(f"  └─ HOLD: {hold_signals}")
        logger.info("")
        logger.info(f"📊 POZİSYON DURUMU:")
        logger.info(f"  ├─ Açık pozisyon: {open_positions}")
        logger.info(f"  └─ Kapalı pozisyon: {closed_positions}")
        logger.info("")

        if closed_positions > 0:
            logger.info(f"🎯 KAPALI POZİSYON SONUÇLARI:")
            logger.info(f"  ├─ TP1 Vurulan: {tp1_hits}")
            logger.info(f"  ├─ TP2 Vurulan: {tp2_hits}")
            logger.info(f"  ├─ SL Vurulan: {sl_hits}")
            logger.info(f"  └─ Win Rate: {win_rate:.1f}%")
            logger.info("")

            # Show individual closed trades
            logger.info(f"📋 KAPALI İŞLEMLER:")
            for detail in signal_details:
                emoji = "✅" if detail['outcome'] == 'WIN' else "❌"
                tp_status = "TP2" if detail['tp2_hit'] else ("TP1" if detail['tp1_hit'] else "SL")
                logger.info(f"  {emoji} {detail['market']} ({detail['signal']}) → {tp_status}")
        else:
            logger.info("⏳ Henüz kapalı pozisyon yok")

        # Update Robot 6 status (BP column) - write to row 2
        ws.update_cell(2, cols.BP, status_text(6, True))

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"✅ ROBOT 6 TAMAMLANDI!")
        logger.info(f"  Toplam sinyal: {total_signals}")
        logger.info(f"  Kapalı pozisyon: {closed_positions}")
        logger.info(f"  Win Rate: {win_rate:.1f}%")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ ROBOT 6 FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()
