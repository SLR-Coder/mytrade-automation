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

from config.constants import (
    MAX_REASONING_LENGTH, SHEETS_RATE_LIMIT_SLEEP, DEFAULT_VOLATILITY,
    RISK_VOLATILITY_MULTIPLIER_TP1, RISK_VOLATILITY_MULTIPLIER_TP2,
    RISK_VOLATILITY_MULTIPLIER_SL, DEFAULT_SHEET_TAB
)
from utils.common import (
    status_text, parse_float, get_latest_market_data,
    get_last_6_batches, analyze_temporal_trend,
    is_ready_for_analysis, BATCH_STATUS_READY
)  # DRY: All common functions from single source
from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.deepseek_wrapper import get_deepseek_signal
from utils.claude_wrapper import get_claude_signal
from utils.openai_wrapper import get_openai_signal
from utils.grok_wrapper import get_grok_signal
from utils.gemini_wrapper import get_gemini_signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-3-AISignalGenerator")

SHEET_TAB = os.getenv("SHEET_TAB", DEFAULT_SHEET_TAB)


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
    logger.info(f"🤖 {market} için 5 AI'dan paralel sinyal topluyorum...")

    loop = asyncio.get_event_loop()

    tasks = [
        loop.run_in_executor(None, get_deepseek_signal, market, price, indicators),
        loop.run_in_executor(None, get_claude_signal, market, price, indicators),
        loop.run_in_executor(None, get_openai_signal, market, price, indicators),
        loop.run_in_executor(None, get_gemini_signal, market, price, indicators),
        loop.run_in_executor(None, get_grok_signal, market, price, indicators),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    ai_signals = {}
    ai_names = ["deepseek", "claude", "gpt4", "gemini", "grok"]

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
    """
    Calculate risk/reward levels based on volatility

    Args:
        price: Current market price
        signal: Trading signal (BUY/SELL/HOLD)
        indicators: Technical indicators dictionary

    Returns:
        Tuple of (entry, sl, tp1, tp2, risk_reward) or (None, None, None, None, None) for HOLD
    """
    if signal == "HOLD":
        return None, None, None, None, None

    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")

    if bb_upper and bb_lower:
        volatility = (bb_upper - bb_lower) / price
    else:
        volatility = DEFAULT_VOLATILITY

    if signal == "BUY":
        entry = price
        tp1 = price * (1 + volatility * RISK_VOLATILITY_MULTIPLIER_TP1)
        tp2 = price * (1 + volatility * RISK_VOLATILITY_MULTIPLIER_TP2)
        sl = price * (1 - volatility * RISK_VOLATILITY_MULTIPLIER_SL)
    elif signal == "SELL":
        entry = price
        tp1 = price * (1 - volatility * RISK_VOLATILITY_MULTIPLIER_TP1)
        tp2 = price * (1 - volatility * RISK_VOLATILITY_MULTIPLIER_TP2)
        sl = price * (1 + volatility * RISK_VOLATILITY_MULTIPLIER_SL)
    else:
        return None, None, None, None, None

    risk_reward = abs(tp1 - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
    return entry, sl, tp1, tp2, risk_reward


# analyze_temporal_trend removed - now imported from utils.common


async def run():
    """Main execution function for Robot 3"""
    logger.info("=" * 80)
    logger.info("🤖 ROBOT 3: AI SIGNAL GENERATOR (TEMPORAL TREND ANALİZİ) - BAŞLAT")
    logger.info("=" * 80)

    try:
        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        # Read latest market data (for current prices and row indices)
        markets_data = get_latest_market_data(ws, cols)
        if not markets_data:
            logger.warning("⚠️ Analiz edilecek piyasa yok")
            return

        # Read temporal data (last 6 batches for trend analysis)
        temporal_data = get_last_6_batches(ws, cols)

        logger.info(f"\n🎯 {len(markets_data)} piyasa için TEMPORAL TREND analizi başlıyor...\n")

        processed = 0
        skipped_not_ready = 0

        for market_data in markets_data:
            market = market_data["market"]
            price = market_data["price"]
            indicators = market_data["indicators"]
            row_index = market_data["row_index"]

            # 1. Batch status kontrolü - Robot 1 "✅ Analiz Hazır" yazmış mı? (BK sütunu)
            try:
                robot1_status = ws.cell(row_index, cols.BK).value or ""
                if not is_ready_for_analysis(robot1_status):
                    skipped_not_ready += 1
                    continue  # Sessizce atla - henüz hazır değil
            except:
                pass  # Status okunamazsa devam et

            # 2. Robot 3 status kontrolü - Zaten işlenmişse atla (BM sütunu)
            try:
                current_status = ws.cell(row_index, cols.BM).value or ""
                if "Robot 3" in current_status and "✅" in current_status:
                    logger.info(f"⏭️  {market} zaten işlenmiş (Robot 3 ✅), atlanıyor...")
                    continue
            except:
                pass  # Status okunamazsa devam et

            # Analyze temporal trend (last 30 minutes)
            temporal_summary = "İlk analiz - henüz geçmiş veri yok"
            if market in temporal_data and temporal_data[market]:
                temporal_summary = analyze_temporal_trend(temporal_data[market])
                logger.info(f"  📈 {temporal_summary}")

            # Add temporal summary to indicators (AI'lar bunu görecek)
            indicators_with_trend = indicators.copy()
            indicators_with_trend['temporal_summary'] = temporal_summary

            logger.info(f"\n{'='*60}")
            logger.info(f"📊 {market} @ ${price:,.2f}")
            logger.info(f"{'='*60}")

            # Collect AI signals (parallel) - temporal_summary artık indicators içinde
            ai_signals = await collect_ai_signals(market, price, indicators_with_trend)

            # Write to Google Sheets - Her AI için 2 sütun: Sinyal + Analiz
            try:
                # GPT-4 (AI-AJ sütunları: sinyal + analiz)
                if ai_signals.get("gpt4"):
                    gpt = ai_signals["gpt4"]
                    ws.update_cell(row_index, cols.AI, f"{gpt['signal']} ({gpt['confidence']}%)")
                    ws.update_cell(row_index, cols.AJ, gpt['reasoning'][:MAX_REASONING_LENGTH])

                # Claude (AK-AL sütunları: sinyal + analiz)
                if ai_signals.get("claude"):
                    cl = ai_signals["claude"]
                    ws.update_cell(row_index, cols.AK, f"{cl['signal']} ({cl['confidence']}%)")
                    ws.update_cell(row_index, cols.AL, cl['reasoning'][:MAX_REASONING_LENGTH])

                # Gemini (AM-AN sütunları: sinyal + analiz)
                if ai_signals.get("gemini"):
                    gem = ai_signals["gemini"]
                    ws.update_cell(row_index, cols.AM, f"{gem['signal']} ({gem['confidence']}%)")
                    ws.update_cell(row_index, cols.AN, gem['reasoning'][:MAX_REASONING_LENGTH])

                # Grok (AO-AP sütunları: sinyal + analiz)
                if ai_signals.get("grok"):
                    grk = ai_signals["grok"]
                    ws.update_cell(row_index, cols.AO, f"{grk['signal']} ({grk['confidence']}%)")
                    ws.update_cell(row_index, cols.AP, grk['reasoning'][:MAX_REASONING_LENGTH])

                # DeepSeek (AQ-AR sütunları: sinyal + analiz)
                if ai_signals.get("deepseek"):
                    ds = ai_signals["deepseek"]
                    ws.update_cell(row_index, cols.AQ, f"{ds['signal']} ({ds['confidence']}%)")
                    ws.update_cell(row_index, cols.AR, ds['reasoning'][:MAX_REASONING_LENGTH])

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

                    # Risk management (AY-BC for Entry/SL/TP/RR)
                    entry, sl, tp1, tp2, rr = calculate_risk_reward(price, majority, indicators)
                    if entry:
                        ws.update_cell(row_index, cols.AY, f"${entry:,.2f}")  # Giriş Fiyatı
                        ws.update_cell(row_index, cols.AZ, f"${sl:,.2f}")     # Zarar Durdur
                        ws.update_cell(row_index, cols.BA, f"${tp1:,.2f}")    # Kar Al 1
                        ws.update_cell(row_index, cols.BB, f"${tp2:,.2f}")    # Kar Al 2
                        ws.update_cell(row_index, cols.BC, f"{rr:.2f}")       # Risk/Ödül

                # Status (Robot 3: BM sütunu)
                ws.update_cell(row_index, cols.BM, status_text(3, True))

                processed += 1
                logger.info(f"  ✓ Satır {row_index} güncellendi")
                time.sleep(SHEETS_RATE_LIMIT_SLEEP)  # Rate limiting

            except Exception as e:
                logger.error(f"  ❌ Sheets yazma hatası {market}: {e}")
                continue

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 3 TAMAMLANDI")
        logger.info(f"  İşlenen piyasa: {processed}/{len(markets_data)}")
        if skipped_not_ready > 0:
            logger.info(f"  ⏳ Beklemede (henüz hazır değil): {skipped_not_ready}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ ROBOT 3 BAŞARISIZ: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(run())
