# robots/ai_signal_generator.py
# -*- coding: utf-8 -*-
"""
Robot 3: AI Signal Generator
Uses ensemble of 3 AI models (GPT-4, Claude, Gemini) for trading signals
NOTE: The actual implementation appears to be in Robot 4 in the source
"""

import os
import time
import datetime
import pytz
import logging
from typing import Dict, List, Optional, Tuple
from collections import Counter

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.openai_wrapper import get_openai_signal
from utils.claude_wrapper import get_claude_signal
from utils.gemini_wrapper import get_gemini_signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-3-AISignalGenerator")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", "60"))  # Minimum confidence to act


def status_text(robot_no: int, ok: bool) -> str:
    """Generate status text for robot"""
    return f"Robot {robot_no} {'✅' if ok else '❌'}"


def get_latest_market_data(ws, cols) -> List[Dict]:
    """
    Read latest market data from Google Sheets

    Returns list of market data dicts with indicators
    """
    logger.info("Reading latest market data from Google Sheets...")

    # Get all rows
    all_rows = ws.get_all_values()

    if len(all_rows) <= 1:
        logger.warning("No data in sheet")
        return []

    # Son ayırıcıyı bul (en son veri grubunu işaretler)
    separator_idx = None
    for i in range(len(all_rows) - 1, 0, -1):
        if len(all_rows[i]) > cols.AH - 1:
            if all_rows[i][cols.AH - 1] == "Ayırıcı":
                separator_idx = i
                break

    if separator_idx is None:
        logger.warning("Ayırıcı bulunamadı, tüm veriler kullanılıyor")
        data_rows = all_rows[1:]  # Başlığı atla
    else:
        # Son ayırıcıdan sonraki satırları al
        data_rows = all_rows[separator_idx + 1:]

    logger.info(f"Found {len(data_rows)} markets in latest batch")

    # Parse market data
    markets_data = []
    for row in data_rows:
        if len(row) < cols.B:
            continue

        market = row[cols.B - 1] if len(row) > cols.B - 1 else ""
        if not market or market == "":
            continue

        try:
            # Handle Turkish locale (comma as decimal separator)
            price_str = row[cols.C - 1] if len(row) > cols.C - 1 and row[cols.C - 1] else "0"
            price_str = price_str.replace(",", ".")
            price = float(price_str)
        except:
            price = 0

        # Parse indicators
        indicators = {}
        try:
            def parse_float(value):
                """Parse float handling Turkish locale"""
                if not value:
                    return None
                return float(str(value).replace(",", "."))

            if len(row) > cols.F - 1 and row[cols.F - 1]:
                indicators['rsi'] = parse_float(row[cols.F - 1])
            if len(row) > cols.G - 1 and row[cols.G - 1]:
                indicators['macd'] = parse_float(row[cols.G - 1])
            if len(row) > cols.H - 1 and row[cols.H - 1]:
                indicators['macd_signal'] = parse_float(row[cols.H - 1])
            if len(row) > cols.I - 1 and row[cols.I - 1]:
                indicators['macd_histogram'] = parse_float(row[cols.I - 1])
            if len(row) > cols.J - 1 and row[cols.J - 1]:
                indicators['bb_upper'] = parse_float(row[cols.J - 1])
            if len(row) > cols.K - 1 and row[cols.K - 1]:
                indicators['bb_middle'] = parse_float(row[cols.K - 1])
            if len(row) > cols.L - 1 and row[cols.L - 1]:
                indicators['bb_lower'] = parse_float(row[cols.L - 1])
            if len(row) > cols.M - 1 and row[cols.M - 1]:
                indicators['ema_9'] = parse_float(row[cols.M - 1])
            if len(row) > cols.N - 1 and row[cols.N - 1]:
                indicators['ema_21'] = parse_float(row[cols.N - 1])
            if len(row) > cols.O - 1 and row[cols.O - 1]:
                indicators['ema_50'] = parse_float(row[cols.O - 1])
            if len(row) > cols.P - 1 and row[cols.P - 1]:
                indicators['ema_200'] = parse_float(row[cols.P - 1])

            # Support/Resistance
            support_levels = []
            resistance_levels = []
            if len(row) > cols.Q - 1 and row[cols.Q - 1]:
                val = parse_float(row[cols.Q - 1])
                if val:
                    support_levels.append(val)
            if len(row) > cols.R - 1 and row[cols.R - 1]:
                val = parse_float(row[cols.R - 1])
                if val:
                    resistance_levels.append(val)

            indicators['support_levels'] = support_levels
            indicators['resistance_levels'] = resistance_levels

            # Trend
            if len(row) > cols.S - 1 and row[cols.S - 1]:
                indicators['trend'] = row[cols.S - 1]

        except Exception as e:
            logger.warning(f"Error parsing indicators for {market}: {e}")

        markets_data.append({
            "market": market,
            "price": price,
            "indicators": indicators,
            "row_index": all_rows.index(row) + 1  # 1-indexed for Sheets
        })

    logger.info(f"✓ Parsed {len(markets_data)} markets with indicators")
    return markets_data


async def run():
    """Main execution function for Robot 3"""
    logger.info("=" * 60)
    logger.info("ROBOT 3: AI SIGNAL GENERATOR - STARTING")
    logger.info("=" * 60)

    try:
        # Get secrets
        sheet_id = get_secret("GOOGLE_SHEET_ID")

        # Get Google Sheets client
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        logger.info(f"Connected to Google Sheet: {SHEET_TAB}")

        # Get latest market data
        markets_data = get_latest_market_data(ws, cols)

        if not markets_data:
            logger.warning("⚠ No market data to analyze")
            return

        logger.info(f"\n🤖 Generating AI signals for {len(markets_data)} markets...")

        # Generate signals for each market
        signals_generated = 0
        for market_data in markets_data:
            market = market_data["market"]
            price = market_data["price"]
            indicators = market_data["indicators"]
            row_index = market_data["row_index"]

            logger.info(f"\n📊 Analyzing {market} @ ${price:,.2f}")

            # Get Claude signal (primary AI in TEST mode)
            ai_signal = get_claude_signal(market, price, indicators)
            ai_name = "Claude"

            if not ai_signal:
                logger.warning(f"  ⚠️ Claude sinyali alınamadı, Gemini deneniyor...")
                # Fallback to Gemini
                ai_signal = get_gemini_signal(market, price, indicators)
                ai_name = "Gemini"

                if not ai_signal:
                    logger.warning(f"  ⚠️ Hiçbir AI sinyali alınamadı: {market}")
                    continue

            # In TEST mode, use single AI signal as final signal (no ensemble)
            final_signal = ai_signal["signal"]
            final_confidence = ai_signal["confidence"]
            reasoning = ai_signal["reasoning"][:500]  # Truncate for Sheets

            logger.info(f"  🎯 {ai_name}: {ai_signal['signal']} ({ai_signal['confidence']}%)")
            logger.info(f"  ✅ Final: {final_signal} ({final_confidence}%)")

            # Calculate risk/reward levels
            tp1, tp2, sl = calculate_risk_reward(price, final_signal, indicators)

            # Sinyalleri Google Sheets'e yaz
            try:
                # Kolon V: GPT-4 Sinyali (TEST modunda yok)
                ws.update_cell(row_index, cols.V, "Yok (TEST)")

                # Kolon W: Claude Sinyali
                if ai_name == "Claude":
                    ws.update_cell(row_index, cols.W, f"{ai_signal['signal']} ({ai_signal['confidence']}%)")
                else:
                    ws.update_cell(row_index, cols.W, "Yok")

                # Kolon X: Gemini Sinyali
                if ai_name == "Gemini":
                    ws.update_cell(row_index, cols.X, f"{ai_signal['signal']} ({ai_signal['confidence']}%)")
                else:
                    ws.update_cell(row_index, cols.X, "Yok")

                # Kolon Y: Nihai Sinyal (Topluluk)
                ws.update_cell(row_index, cols.Y, final_signal)

                # Kolon Z: Güven
                ws.update_cell(row_index, cols.Z, f"{final_confidence}%")

                # Kolon AA: AI Gerekçesi
                ws.update_cell(row_index, cols.AA, reasoning)

                # Kolon AB: Kar Al 1
                ws.update_cell(row_index, cols.AB, f"${tp1:,.2f}" if tp1 else "")

                # Kolon AC: Kar Al 2
                ws.update_cell(row_index, cols.AC, f"${tp2:,.2f}" if tp2 else "")

                # Kolon AD: Zarar Durdur
                ws.update_cell(row_index, cols.AD, f"${sl:,.2f}" if sl else "")

                # Kolon AE: Robot 3 Durumu
                ws.update_cell(row_index, cols.AE, status_text(3, True))

                signals_generated += 1
                logger.info(f"  ✓ Signal written to row {row_index}")

                # Rate limiting (Google Sheets API)
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"  ❌ Failed to write signal for {market}: {e}")
                continue

        logger.info("=" * 60)
        logger.info(f"✓ ROBOT 3 COMPLETED")
        logger.info(f"  Signals generated: {signals_generated}/{len(markets_data)}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ ROBOT 3 FAILED: {e}", exc_info=True)
        raise


def calculate_risk_reward(price: float, signal: str, indicators: Dict) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Calculate Take Profit and Stop Loss levels

    Args:
        price: Current price
        signal: BUY/SELL/HOLD
        indicators: Technical indicators

    Returns:
        Tuple of (TP1, TP2, SL)
    """
    if signal == "HOLD":
        return None, None, None

    # Get ATR-based volatility (use Bollinger Bands as proxy)
    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")

    if bb_upper and bb_lower:
        volatility = (bb_upper - bb_lower) / price
    else:
        volatility = 0.02  # Default 2% volatility

    if signal == "BUY":
        # Take Profit levels (1.5x and 3x risk)
        tp1 = price * (1 + volatility * 1.5)
        tp2 = price * (1 + volatility * 3.0)
        # Stop Loss (below support or -1x volatility)
        sl = price * (1 - volatility * 1.0)

    elif signal == "SELL":
        # Take Profit levels (1.5x and 3x risk)
        tp1 = price * (1 - volatility * 1.5)
        tp2 = price * (1 - volatility * 3.0)
        # Stop Loss (above resistance or +1x volatility)
        sl = price * (1 + volatility * 1.0)

    else:
        return None, None, None

    return tp1, tp2, sl


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())