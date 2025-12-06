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
    is_ready_for_analysis, BATCH_STATUS_READY,
    get_unprocessed_ready_rows,  # ROBUST: Zamanlama bağımsız satır bulma
    update_separator_status  # Separator satırına robot durumu yaz
)  # DRY: All common functions from single source
from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.deepseek_wrapper import get_deepseek_signal
from utils.claude_wrapper import get_claude_signal
from utils.openai_wrapper import get_openai_signal
from utils.grok_wrapper import get_grok_signal
from utils.gemini_wrapper import get_gemini_signal
from utils.supabase_client import (
    get_unanalyzed_batches, get_market_history, update_batch_analysis
)
from utils.monitoring import update_robot_status as update_monitoring

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


def format_trend_data(history: list) -> Dict:
    """Format 6-sequence trend data for AI analysis

    Args:
        history: List of 6 signal rows (sequences 1-6)

    Returns:
        Dict with trend summary and latest indicators
    """
    if not history:
        return {}

    # Get price trend
    prices = [float(h["price"]) for h in history if h.get("price")]
    if len(prices) >= 2:
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100
        trend_direction = "UP" if price_change > 0.5 else "DOWN" if price_change < -0.5 else "SIDEWAYS"
    else:
        price_change = 0
        trend_direction = "UNKNOWN"

    # Get RSI trend
    rsis = [float(h["rsi"]) for h in history if h.get("rsi")]
    rsi_trend = "INCREASING" if len(rsis) >= 2 and rsis[-1] > rsis[0] else "DECREASING" if len(rsis) >= 2 and rsis[-1] < rsis[0] else "STABLE"

    # Latest data (sequence 6)
    latest = history[-1] if history else {}

    return {
        "price_history": prices,
        "price_change_30min": price_change,
        "trend_direction": trend_direction,
        "rsi_trend": rsi_trend,
        "latest_price": latest.get("price"),
        "latest_rsi": latest.get("rsi"),
        "latest_macd": latest.get("macd"),
        "latest_bb_upper": latest.get("bb_upper"),
        "latest_bb_middle": latest.get("bb_middle"),
        "latest_bb_lower": latest.get("bb_lower"),
        "support": latest.get("support_1"),
        "resistance": latest.get("resistance_1"),
        "atr": latest.get("atr"),
        "sequence_count": len(history),
    }


async def run():
    """Main execution function for Robot 3 - POLLING MODE"""
    logger.info("=" * 80)
    logger.info("🤖 ROBOT 3: AI SIGNAL GENERATOR - POLLING MODE")
    logger.info("=" * 80)

    processed = 0
    error_msg = ""

    try:
        # Check for unanalyzed batches
        unanalyzed = get_unanalyzed_batches(3)

        if not unanalyzed:
            logger.info("⏳ Analiz bekleyen batch yok (Robot 3)")
            try:
                gc = get_gspread_client()
                sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
                update_monitoring(gc, sheet_id, 3, True, 0, "Bekleyen batch yok")
            except:
                pass
            return

        logger.info(f"🎯 {len(unanalyzed)} batch analiz edilecek")

        for batch_info in unanalyzed:
            batch_id = batch_info["batch_id"]
            markets = batch_info["markets"]

            logger.info(f"\n{'='*60}")
            logger.info(f"📦 Batch: {batch_id} - {len(markets)} market")
            logger.info(f"{'='*60}")

            for market in markets:
                # Get 6-sequence trend data for this market
                history = get_market_history(batch_id, market)

                if len(history) < 3:
                    logger.warning(f"  ⚠️ {market}: Yetersiz veri ({len(history)} sequence)")
                    continue

                # Format trend data
                trend_data = format_trend_data(history)
                price = float(trend_data.get("latest_price", 0) or 0)

                logger.info(f"\n📊 {market} @ ${price:,.2f}")
                logger.info(f"   30dk Trend: {trend_data['trend_direction']} ({trend_data['price_change_30min']:+.2f}%)")

                # Build indicators with trend context
                indicators = {
                    "rsi": trend_data.get("latest_rsi"),
                    "macd": trend_data.get("latest_macd"),
                    "bb_upper": trend_data.get("latest_bb_upper"),
                    "bb_middle": trend_data.get("latest_bb_middle"),
                    "bb_lower": trend_data.get("latest_bb_lower"),
                    "support_1": trend_data.get("support"),
                    "resistance_1": trend_data.get("resistance"),
                    "atr": trend_data.get("atr"),
                    # Trend context for AI
                    "trend_30min": trend_data["trend_direction"],
                    "price_change_30min": trend_data["price_change_30min"],
                    "rsi_trend": trend_data["rsi_trend"],
                    "price_history": trend_data["price_history"],
                }

                # Collect AI signals (parallel - 5 AIs)
                ai_signals = await collect_ai_signals(market, price, indicators)

                # Prepare update data
                update_data = {}

                if ai_signals.get("deepseek"):
                    ds = ai_signals["deepseek"]
                    update_data["deepseek_signal"] = ds["signal"]
                    update_data["deepseek_confidence"] = ds["confidence"]
                    update_data["deepseek_analysis"] = ds["reasoning"][:500]

                if ai_signals.get("claude"):
                    cl = ai_signals["claude"]
                    update_data["claude_signal"] = cl["signal"]
                    update_data["claude_confidence"] = cl["confidence"]
                    update_data["claude_analysis"] = cl["reasoning"][:500]

                if ai_signals.get("gpt4"):
                    gpt = ai_signals["gpt4"]
                    update_data["gpt4_signal"] = gpt["signal"]
                    update_data["gpt4_confidence"] = gpt["confidence"]
                    update_data["gpt4_analysis"] = gpt["reasoning"][:500]

                if ai_signals.get("gemini"):
                    gem = ai_signals["gemini"]
                    update_data["gemini_signal"] = gem["signal"]
                    update_data["gemini_confidence"] = gem["confidence"]
                    update_data["gemini_analysis"] = gem["reasoning"][:500]

                if ai_signals.get("grok"):
                    grk = ai_signals["grok"]
                    update_data["grok_signal"] = grk["signal"]
                    update_data["grok_confidence"] = grk["confidence"]
                    update_data["grok_analysis"] = grk["reasoning"][:500]

                # Update all 6 sequences for this market
                if update_data:
                    success = update_batch_analysis(batch_id, market, 3, update_data)
                    if success:
                        processed += 1
                        logger.info(f"  ✅ {market} analiz tamamlandı")
                    else:
                        logger.error(f"  ❌ {market} güncellenemedi")

        # Calculate total markets processed
        total_markets = sum(len(b["markets"]) for b in unanalyzed)

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 3 TAMAMLANDI")
        logger.info(f"   📊 İşlenen: {processed}/{total_markets} market")
        logger.info(f"   📦 Batch: {len(unanalyzed)}")
        logger.info(f"   💾 Supabase: ✅")
        logger.info("=" * 80)

    except Exception as e:
        error_msg = str(e)[:50]
        logger.error(f"❌ ROBOT 3 BAŞARISIZ: {e}", exc_info=True)
        raise

    finally:
        # Update monitoring dashboard
        try:
            gc = get_gspread_client()
            sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
            update_monitoring(
                gc=gc,
                sheet_id=sheet_id,
                robot_number=3,
                success=processed > 0 or not error_msg,
                count=processed,
                detail=f"{processed} market analizi" if processed else "Bekleyen batch yok",
                error=error_msg
            )
        except Exception as e:
            logger.warning(f"Monitoring update failed: {e}")


if __name__ == "__main__":
    asyncio.run(run())
