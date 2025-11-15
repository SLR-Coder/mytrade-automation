# robots/ai_signal_generator.py
# -*- coding: utf-8 -*-
"""
Robot 3: AI Signal Generator - 4 AI Detaylı Analiz
DeepSeek, Claude, GPT-4, Grok - Her biri sinyal + detaylı analiz üretir
"""

import os
import time
import asyncio
import logging
from typing import Dict, List, Optional

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.deepseek_wrapper import get_deepseek_signal
from utils.claude_wrapper import get_claude_signal
from utils.openai_wrapper import get_openai_signal
from utils.grok_wrapper import get_grok_signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-3-AISignalGenerator")

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
    logger.info("📊 Son piyasa verileri okunuyor...")

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
            logger.warning(f"Indicator parse hatası {market}: {e}")

        markets_data.append({
            "market": market,
            "price": price,
            "indicators": indicators,
            "row_index": all_rows.index(row) + 1
        })

    logger.info(f"✓ {len(markets_data)} piyasa verisi okundu")
    return markets_data


async def collect_ai_signals(market: str, price: float, indicators: Dict) -> Dict:
    """
    4 AI'dan paralel sinyal topla

    Returns:
        {
            "deepseek": {"signal": "BUY", "confidence": 75, "reasoning": "..."},
            "claude": {...},
            "gpt4": {...},
            "grok": {...}
        }
    """
    logger.info(f"🤖 {market} için 4 AI'dan paralel sinyal topluyorum...")

    loop = asyncio.get_event_loop()

    tasks = [
        loop.run_in_executor(None, get_deepseek_signal, market, price, indicators),
        loop.run_in_executor(None, get_claude_signal, market, price, indicators),
        loop.run_in_executor(None, get_openai_signal, market, price, indicators),
        loop.run_in_executor(None, get_grok_signal, market, price, indicators),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    ai_signals = {}
    ai_names = ["deepseek", "claude", "gpt4", "grok"]

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"  ⚠️ {ai_names[i].upper()} başarısız: {result}")
            ai_signals[ai_names[i]] = None
        elif result is not None:
            ai_signals[ai_names[i]] = result
            logger.info(f"  ✅ {ai_names[i].upper()}: {result['signal']} ({result['confidence']}%)")
        else:
            ai_signals[ai_names[i]] = None

    return ai_signals


def calculate_risk_reward(price: float, signal: str, indicators: Dict):
    """Calculate risk/reward levels"""
    if signal == "HOLD":
        return None, None, None, None, None

    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")

    if bb_upper and bb_lower:
        volatility = (bb_upper - bb_lower) / price
    else:
        volatility = 0.02

    if signal == "BUY":
        entry = price
        tp1 = price * (1 + volatility * 1.5)
        tp2 = price * (1 + volatility * 3.0)
        sl = price * (1 - volatility * 1.0)
    elif signal == "SELL":
        entry = price
        tp1 = price * (1 - volatility * 1.5)
        tp2 = price * (1 - volatility * 3.0)
        sl = price * (1 + volatility * 1.0)
    else:
        return None, None, None, None, None

    risk_reward = abs(tp1 - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
    return entry, sl, tp1, tp2, risk_reward


async def run():
    """Main execution function for Robot 3"""
    logger.info("=" * 80)
    logger.info("🤖 ROBOT 3: AI SIGNAL GENERATOR (4 AI DETAYLI ANALİZ) - BAŞLAT")
    logger.info("=" * 80)

    try:
        sheet_id = get_secret("GOOGLE_SHEET_ID")
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        markets_data = get_latest_market_data(ws, cols)
        if not markets_data:
            logger.warning("⚠️ Analiz edilecek piyasa yok")
            return

        logger.info(f"\n🎯 {len(markets_data)} piyasa için AI analizi başlıyor...\n")

        processed = 0
        for market_data in markets_data:
            market = market_data["market"]
            price = market_data["price"]
            indicators = market_data["indicators"]
            row_index = market_data["row_index"]

            logger.info(f"\n{'='*60}")
            logger.info(f"📊 {market} @ ${price:,.2f}")
            logger.info(f"{'='*60}")

            # Collect AI signals (parallel)
            ai_signals = await collect_ai_signals(market, price, indicators)

            # Write to Google Sheets
            try:
                # DeepSeek (V-W)
                if ai_signals.get("deepseek"):
                    ds = ai_signals["deepseek"]
                    ws.update_cell(row_index, cols.V, f"{ds['signal']} ({ds['confidence']}%)")
                    ws.update_cell(row_index, cols.W, ds['reasoning'][:500])

                # Claude (X-Y)
                if ai_signals.get("claude"):
                    cl = ai_signals["claude"]
                    ws.update_cell(row_index, cols.X, f"{cl['signal']} ({cl['confidence']}%)")
                    ws.update_cell(row_index, cols.Y, cl['reasoning'][:500])

                # GPT-4 (Z-AA)
                if ai_signals.get("gpt4"):
                    gpt = ai_signals["gpt4"]
                    ws.update_cell(row_index, cols.Z, f"{gpt['signal']} ({gpt['confidence']}%)")
                    ws.update_cell(row_index, cols.AA, gpt['reasoning'][:500])

                # Grok (AB-AC)
                if ai_signals.get("grok"):
                    grk = ai_signals["grok"]
                    ws.update_cell(row_index, cols.AB, f"{grk['signal']} ({grk['confidence']}%)")
                    ws.update_cell(row_index, cols.AC, grk['reasoning'][:500])

                # Calculate majority signal for risk calculation
                signals_list = [s for s in ai_signals.values() if s]
                if signals_list:
                    buy_count = sum(1 for s in signals_list if s['signal'] == 'BUY')
                    sell_count = sum(1 for s in signals_list if s['signal'] == 'SELL')

                    if buy_count > sell_count:
                        majority = "BUY"
                    elif sell_count > buy_count:
                        majority = "SELL"
                    else:
                        majority = "HOLD"

                    # Risk management (AJ-AN)
                    entry, sl, tp1, tp2, rr = calculate_risk_reward(price, majority, indicators)
                    if entry:
                        ws.update_cell(row_index, cols.AJ, f"${entry:,.2f}")
                        ws.update_cell(row_index, cols.AK, f"${sl:,.2f}")
                        ws.update_cell(row_index, cols.AL, f"${tp1:,.2f}")
                        ws.update_cell(row_index, cols.AM, f"${tp2:,.2f}")
                        ws.update_cell(row_index, cols.AN, f"{rr:.2f}")

                # Status
                ws.update_cell(row_index, cols.AO, status_text(3, True))

                processed += 1
                logger.info(f"  ✓ Satır {row_index} güncellendi")
                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                logger.error(f"  ❌ Sheets yazma hatası {market}: {e}")
                continue

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 3 TAMAMLANDI")
        logger.info(f"  İşlenen piyasa: {processed}/{len(markets_data)}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ ROBOT 3 BAŞARISIZ: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(run())
