# robots/sheets_to_db_sync.py
# -*- coding: utf-8 -*-
"""
Google Sheets to Database Sync
Reads final signals from Google Sheets (Robot 7 output) and syncs to database for Robot 6
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from core.database import get_db_session, init_database, close_database
from data.models.signals import SignalModel
from data.models.market_data import MarketDataModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SheetsToDBSync")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")


def parse_float(value: str) -> Optional[float]:
    """Parse float from string, handling Turkish decimal format"""
    if not value or value.strip() == "":
        return None
    try:
        # Replace Turkish decimal comma with dot
        value = str(value).replace(",", ".")
        return float(value)
    except:
        return None


def parse_confidence(value: str) -> Optional[int]:
    """Parse confidence percentage: '%75' or '75%' -> 75"""
    if not value or value.strip() == "":
        return None
    try:
        # Remove % sign and parse
        value = str(value).strip().replace("%", "")
        return int(float(value))
    except:
        return None


async def sync_signals():
    """
    Sync final signals from Google Sheets to database

    Reads Robot 7 Command Center output (AG-AL columns) and writes to SignalModel
    """
    logger.info("=" * 80)
    logger.info("📊 GOOGLE SHEETS → DATABASE SYNC - BAŞLAT")
    logger.info("=" * 80)

    try:
        # Get secrets
        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")

        # Get Google Sheets client
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        logger.info(f"✓ Google Sheets bağlantısı kuruldu: {SHEET_TAB}")

        # Get all rows
        all_rows = ws.get_all_values()

        if len(all_rows) <= 1:
            logger.warning("⚠️ Sheet'te veri yok")
            return

        # Find last separator
        separator_idx = None
        for i in range(len(all_rows) - 1, 0, -1):
            if len(all_rows[i]) > cols.B - 1:
                market_value = all_rows[i][cols.B - 1]
                if market_value and ("📊" in market_value or "RAPORU" in market_value):
                    separator_idx = i
                    logger.info(f"✓ Separator bulundu: Satır {i + 1}")
                    break

        if separator_idx is None:
            data_rows = all_rows[1:]
        else:
            data_rows = all_rows[separator_idx + 1:]

        logger.info(f"✓ {len(data_rows)} piyasa satırı bulundu")

        # Initialize database
        await init_database()

        synced_count = 0

        async with get_db_session() as session:
            for row in data_rows:
                # Skip empty rows
                if len(row) < cols.B or not row[cols.B - 1]:
                    continue

                market = row[cols.B - 1]

                # Check if Robot 7 has processed this row (AG column must have signal)
                if len(row) <= cols.AG - 1 or not row[cols.AG - 1]:
                    continue  # Robot 7 hasn't processed yet

                try:
                    # Extract data
                    timestamp_str = row[cols.A - 1] if len(row) > cols.A - 1 else ""

                    # Parse timestamp
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        timestamp = datetime.utcnow()

                    # Market data
                    price_usd = parse_float(row[cols.C - 1]) if len(row) > cols.C - 1 else None

                    # Robot 7 Command Center output (AG-AL)
                    final_signal = row[cols.AG - 1] if len(row) > cols.AG - 1 else ""  # BUY/SELL/HOLD
                    final_confidence = parse_confidence(row[cols.AH - 1]) if len(row) > cols.AH - 1 else None
                    reasoning = row[cols.AI - 1] if len(row) > cols.AI - 1 else ""
                    consensus = parse_confidence(row[cols.AJ - 1]) if len(row) > cols.AJ - 1 else None
                    risk_level = row[cols.AK - 1] if len(row) > cols.AK - 1 else "MEDIUM"
                    suggested_action = row[cols.AL - 1] if len(row) > cols.AL - 1 else "SET ALERT"

                    # Robot 3 individual AI signals (W-AF)
                    gpt4_signal = row[cols.W - 1] if len(row) > cols.W - 1 else ""
                    claude_signal = row[cols.Y - 1] if len(row) > cols.Y - 1 else ""
                    gemini_signal = row[cols.AA - 1] if len(row) > cols.AA - 1 else ""

                    # Extract confidence from "BUY (75%)" format
                    def extract_confidence(signal_str: str) -> Optional[int]:
                        import re
                        match = re.search(r'\((\d+)%?\)', signal_str)
                        if match:
                            return int(match.group(1))
                        return None

                    gpt4_conf = extract_confidence(gpt4_signal)
                    claude_conf = extract_confidence(claude_signal)
                    gemini_conf = extract_confidence(gemini_signal)

                    # Validate required fields
                    if not final_signal or final_signal not in ["BUY", "SELL", "HOLD"]:
                        continue

                    if not final_confidence or not price_usd:
                        continue

                    # Check if signal already exists (avoid duplicates)
                    from sqlalchemy import select
                    existing = await session.execute(
                        select(SignalModel).where(
                            SignalModel.market == market,
                            SignalModel.time == timestamp,
                            SignalModel.signal == final_signal
                        )
                    )

                    if existing.scalar_one_or_none():
                        logger.debug(f"⏭️  {market} @ {timestamp} already in DB, skipping...")
                        continue

                    # Create signal record
                    signal = SignalModel(
                        time=timestamp,
                        market=market,
                        timeframe="1h",
                        signal=final_signal,
                        confidence=final_confidence,
                        gpt4_signal=gpt4_signal.split("(")[0].strip() if gpt4_signal else None,
                        gpt4_confidence=gpt4_conf,
                        claude_signal=claude_signal.split("(")[0].strip() if claude_signal else None,
                        claude_confidence=claude_conf,
                        gemini_signal=gemini_signal.split("(")[0].strip() if gemini_signal else None,
                        gemini_confidence=gemini_conf,
                        reasoning=reasoning,
                        entry_price=price_usd,
                        stop_loss=None,  # Not in current schema, could be added
                        take_profit_1=None,  # Not in current schema
                        take_profit_2=None,  # Not in current schema
                        risk_reward_ratio=None,
                        position_size_percent=2.0,  # Default
                        news_sentiment=None,
                        signal_metadata={
                            "consensus": consensus,
                            "risk_level": risk_level,
                            "suggested_action": suggested_action,
                            "source": "Robot7-CommandCenter"
                        },
                        actual_outcome="pending"  # Will be updated by Robot 6
                    )

                    session.add(signal)

                    # Also sync market data for Robot 6 to use
                    market_data = MarketDataModel(
                        time=timestamp,
                        market=market,
                        timeframe="1h",
                        open=price_usd,
                        high=price_usd,
                        low=price_usd,
                        close=price_usd,
                        volume=0.0  # Not available in current data
                    )

                    session.add(market_data)

                    synced_count += 1
                    logger.info(f"  ✅ {market}: {final_signal} ({final_confidence}%) synced to DB")

                except Exception as e:
                    logger.error(f"  ❌ Error syncing {market}: {e}")
                    continue

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ SYNC TAMAMLANDI")
        logger.info(f"  Senkronize edilen sinyal: {synced_count}/{len(data_rows)}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ SYNC BAŞARISIZ: {e}", exc_info=True)
        raise
    finally:
        await close_database()


async def run():
    """Main execution function"""
    await sync_signals()


if __name__ == "__main__":
    asyncio.run(run())
