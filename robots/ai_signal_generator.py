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
from utils.supabase_client import get_pending_for_robot, update_robot_status
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


# analyze_temporal_trend removed - now imported from utils.common


async def run():
    """Main execution function for Robot 3"""
    logger.info("=" * 80)
    logger.info("🤖 ROBOT 3: AI SIGNAL GENERATOR - BAŞLAT")
    logger.info("=" * 80)

    processed = 0
    error_msg = ""

    try:
        # Get pending signals from Supabase
        pending_signals = get_pending_for_robot(3)

        if not pending_signals:
            logger.warning("⚠️ İşlenecek sinyal yok (Robot 3 için)")
            # Update monitoring
            try:
                gc = get_gspread_client()
                sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
                update_monitoring(gc, sheet_id, 3, True, 0, "İşlenecek veri yok")
            except:
                pass
            return

        logger.info(f"🎯 {len(pending_signals)} sinyal için AI analizi başlıyor...")

        for signal in pending_signals:
            signal_id = signal["id"]
            market = signal["market"]
            price = float(signal["price"]) if signal["price"] else 0

            # Build indicators dict from signal data
            indicators = {
                "rsi": signal.get("rsi"),
                "macd": signal.get("macd"),
                "macd_signal": signal.get("macd_signal"),
                "bb_upper": signal.get("bb_upper"),
                "bb_middle": signal.get("bb_middle"),
                "bb_lower": signal.get("bb_lower"),
                "ema_9": signal.get("ema_9"),
                "ema_21": signal.get("ema_21"),
                "support_1": signal.get("support_1"),
                "resistance_1": signal.get("resistance_1"),
                "atr": signal.get("atr"),
            }

            logger.info(f"\n{'='*60}")
            logger.info(f"📊 {market} @ ${price:,.2f}")
            logger.info(f"{'='*60}")

            # Collect AI signals (parallel)
            ai_signals = await collect_ai_signals(market, price, indicators)

            # Prepare data for Supabase update
            update_data = {}

            # DeepSeek
            if ai_signals.get("deepseek"):
                ds = ai_signals["deepseek"]
                update_data["deepseek_signal"] = ds["signal"]
                update_data["deepseek_confidence"] = ds["confidence"]
                update_data["deepseek_analysis"] = ds["reasoning"][:500]

            # Claude
            if ai_signals.get("claude"):
                cl = ai_signals["claude"]
                update_data["claude_signal"] = cl["signal"]
                update_data["claude_confidence"] = cl["confidence"]
                update_data["claude_analysis"] = cl["reasoning"][:500]

            # GPT-4
            if ai_signals.get("gpt4"):
                gpt = ai_signals["gpt4"]
                update_data["gpt4_signal"] = gpt["signal"]
                update_data["gpt4_confidence"] = gpt["confidence"]
                update_data["gpt4_analysis"] = gpt["reasoning"][:500]

            # Grok
            if ai_signals.get("grok"):
                grk = ai_signals["grok"]
                update_data["grok_signal"] = grk["signal"]
                update_data["grok_confidence"] = grk["confidence"]
                update_data["grok_analysis"] = grk["reasoning"][:500]

            # Write to Supabase
            if update_data:
                success = update_robot_status(signal_id, 3, update_data)
                if success:
                    processed += 1
                    logger.info(f"  ✅ Signal {signal_id} güncellendi")
                else:
                    logger.error(f"  ❌ Signal {signal_id} güncellenemedi")

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 3 TAMAMLANDI")
        logger.info(f"   📊 İşlenen: {processed}/{len(pending_signals)}")
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
                detail=f"{processed} AI analizi" if processed else "İşlenecek veri yok",
                error=error_msg
            )
        except Exception as e:
            logger.warning(f"Monitoring update failed: {e}")


if __name__ == "__main__":
    asyncio.run(run())
