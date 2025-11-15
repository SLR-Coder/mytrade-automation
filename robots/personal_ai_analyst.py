# robots/personal_ai_analyst.py
# -*- coding: utf-8 -*-
"""
Robot 8: Personal AI Analyst
Kullanicinin kisisel AI analisti - ozel prompt ile detayli piyasa analizi
"""

import os
import time
import logging
from typing import Dict, List

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.assistant_ai import create_personal_analyst

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-8-PersonalAIAnalyst")

SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")


def status_text(robot_no: int, ok: bool) -> str:
    """Generate status text for robot"""
    return f"Robot {robot_no} {'✅' if ok else '❌'}"


def parse_float(value):
    """Parse float handling Turkish locale"""
    if not value:
        return None
    return float(str(value).replace(",", "."))


def get_latest_market_data(ws, cols) -> List[Dict]:
    """Read latest market data from Google Sheets"""
    logger.info("Son piyasa verileri okunuyor...")

    all_rows = ws.get_all_values()
    if len(all_rows) <= 1:
        return []

    # Find last separator
    separator_idx = None
    for i in range(len(all_rows) - 1, 0, -1):
        if len(all_rows[i]) > cols.AO - 1:
            if all_rows[i][cols.AO - 1] == "Ayırıcı":
                separator_idx = i
                break

    if separator_idx is None:
        data_rows = all_rows[1:]
    else:
        data_rows = all_rows[separator_idx + 1:]

    markets_data = []
    for row in data_rows:
        if len(row) < cols.B:
            continue

        market = row[cols.B - 1] if len(row) > cols.B - 1 else ""
        if not market:
            continue

        try:
            price_str = row[cols.C - 1] if len(row) > cols.C - 1 and row[cols.C - 1] else "0"
            price = parse_float(price_str) or 0
        except:
            price = 0

        # Parse indicators
        indicators = {}
        try:
            if len(row) > cols.F - 1: indicators['rsi'] = parse_float(row[cols.F - 1])
            if len(row) > cols.G - 1: indicators['macd'] = parse_float(row[cols.G - 1])
            if len(row) > cols.H - 1: indicators['macd_signal'] = parse_float(row[cols.H - 1])
            if len(row) > cols.I - 1: indicators['macd_histogram'] = parse_float(row[cols.I - 1])
            if len(row) > cols.J - 1: indicators['bb_upper'] = parse_float(row[cols.J - 1])
            if len(row) > cols.K - 1: indicators['bb_middle'] = parse_float(row[cols.K - 1])
            if len(row) > cols.L - 1: indicators['bb_lower'] = parse_float(row[cols.L - 1])
            if len(row) > cols.M - 1: indicators['ema_9'] = parse_float(row[cols.M - 1])
            if len(row) > cols.N - 1: indicators['ema_21'] = parse_float(row[cols.N - 1])
            if len(row) > cols.O - 1: indicators['ema_50'] = parse_float(row[cols.O - 1])
            if len(row) > cols.P - 1: indicators['ema_200'] = parse_float(row[cols.P - 1])
            if len(row) > cols.S - 1: indicators['trend'] = row[cols.S - 1]

            support_levels = []
            resistance_levels = []
            if len(row) > cols.Q - 1 and row[cols.Q - 1]:
                val = parse_float(row[cols.Q - 1])
                if val: support_levels.append(val)
            if len(row) > cols.R - 1 and row[cols.R - 1]:
                val = parse_float(row[cols.R - 1])
                if val: resistance_levels.append(val)

            indicators['support_levels'] = support_levels
            indicators['resistance_levels'] = resistance_levels
        except Exception as e:
            logger.warning(f"Indicator parse hatasi {market}: {e}")

        markets_data.append({
            "market": market,
            "price": price,
            "indicators": indicators,
            "row_index": all_rows.index(row) + 1
        })

    logger.info(f"{len(markets_data)} piyasa verisi okundu")
    return markets_data


def run():
    """Main execution function for Robot 8"""
    logger.info("=" * 80)
    logger.info("ROBOT 8: PERSONAL AI ANALYST (GEMINI 2.5 PRO) - BASLAT")
    logger.info("=" * 80)

    try:
        sheet_id = get_secret("GOOGLE_SHEET_ID")
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        markets_data = get_latest_market_data(ws, cols)
        if not markets_data:
            logger.warning("Analiz edilecek piyasa yok")
            return

        # Robot 8: ALWAYS uses Gemini 2.5 Pro with user's custom prompt
        # Fixed: ai_model = "gemini"
        # Custom prompt from environment variable
        ai_model = "gemini"  # FIXED: Always Gemini
        custom_prompt = os.getenv("PERSONAL_AI_CUSTOM_PROMPT", None)

        analyst = create_personal_analyst(
            ai_model=ai_model,
            custom_prompt=custom_prompt
        )

        logger.info(f"\n{len(markets_data)} piyasa icin kisisel AI analizi basliyor...")
        logger.info(f"  AI Model: GEMINI 2.5 PRO (Fixed)")
        if custom_prompt:
            logger.info(f"  Custom Prompt: {custom_prompt[:100]}...")
        else:
            logger.info(f"  Using default Jirad-style prompt")

        processed = 0
        for market_data in markets_data:
            market = market_data["market"]
            price = market_data["price"]
            indicators = market_data["indicators"]
            row_index = market_data["row_index"]

            logger.info(f"\n{'='*60}")
            logger.info(f"{market} @ ${price:,.2f}")
            logger.info(f"{'='*60}")

            # Get personal AI analysis
            analysis = analyst.analyze(market, price, indicators)

            if not analysis:
                logger.warning(f"  Kisisel AI analizi basarisiz: {market}")
                continue

            # Write to Google Sheets (AD-AE columns)
            try:
                # AD: Signal + Confidence
                ws.update_cell(row_index, cols.AD, f"{analysis['signal']} ({analysis['confidence']}%)")

                # AE: Detailed reasoning
                ws.update_cell(row_index, cols.AE, analysis['reasoning'][:500])  # Truncate to 500 chars

                # Update status
                ws.update_cell(row_index, cols.AO, status_text(8, True))

                processed += 1
                logger.info(f"  {analysis['signal']} ({analysis['confidence']}%)")
                logger.info(f"  {analysis['reasoning'][:100]}...")
                logger.info(f"  Satir {row_index} guncellendi")

                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                logger.error(f"  Sheets yazma hatasi {market}: {e}")
                continue

        logger.info("\n" + "=" * 80)
        logger.info(f"ROBOT 8 TAMAMLANDI")
        logger.info(f"  Islenen piyasa: {processed}/{len(markets_data)}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"ROBOT 8 BASARISIZ: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()
