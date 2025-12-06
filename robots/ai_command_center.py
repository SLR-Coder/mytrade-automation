# robots/ai_command_center.py
# -*- coding: utf-8 -*-
"""
Robot 7: AI Command Center
Robot 3 ve Robot 8'den gelen tüm AI analizlerini okur, meta-analiz yapar ve nihai kararı verir
TP/SL hesaplama ve risk yönetimi dahil
"""

import os
import time
import logging
import re
from typing import Dict, List, Optional, Tuple

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.assistant_ai import create_assistant, BALANCED_PROFILE
from utils.meta_analyzer import create_command_center
from utils.supabase_client import get_pending_batches_for_robot, update_batch_analysis, get_market_history
from utils.monitoring import update_robot_status as update_monitoring

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-7-AICommandCenter")

# TP/SL Multipliers based on risk level
RISK_MULTIPLIERS = {
    "LOW": {"tp1": 1.5, "tp2": 2.5, "sl": 0.8},      # Daha agresif TP, dar SL
    "MEDIUM": {"tp1": 1.2, "tp2": 2.0, "sl": 1.0},   # Dengeli
    "HIGH": {"tp1": 1.0, "tp2": 1.5, "sl": 1.2},     # Muhafazakar TP, geniş SL
}

# Default volatility if ATR/BB not available (percentage)
DEFAULT_VOLATILITY_PCT = 0.02  # 2%


def calculate_volatility(signal: Dict) -> float:
    """
    Calculate volatility from indicators (ATR or Bollinger Bands)

    Priority: ATR > BB width > Default

    Returns:
        Volatility as a ratio (e.g., 0.02 = 2%)
    """
    price = float(signal.get("price", 0) or 0)
    if price <= 0:
        return DEFAULT_VOLATILITY_PCT

    # Try ATR first (best volatility measure)
    atr = signal.get("atr")
    if atr:
        try:
            atr_val = float(atr)
            if atr_val > 0:
                volatility = atr_val / price
                logger.debug(f"Using ATR volatility: {volatility:.4f}")
                return volatility
        except (ValueError, TypeError):
            pass

    # Try Bollinger Bands width
    bb_upper = signal.get("bb_upper")
    bb_lower = signal.get("bb_lower")
    if bb_upper and bb_lower:
        try:
            upper = float(bb_upper)
            lower = float(bb_lower)
            if upper > lower > 0:
                bb_width = (upper - lower) / price
                volatility = bb_width / 2  # Half of BB width
                logger.debug(f"Using BB volatility: {volatility:.4f}")
                return volatility
        except (ValueError, TypeError):
            pass

    # Default volatility
    logger.debug(f"Using default volatility: {DEFAULT_VOLATILITY_PCT}")
    return DEFAULT_VOLATILITY_PCT


def calculate_tp_sl(
    price: float,
    signal_direction: str,
    volatility: float,
    risk_level: str = "MEDIUM"
) -> Dict[str, float]:
    """
    Calculate Take Profit and Stop Loss levels

    Args:
        price: Current market price
        signal_direction: "BUY", "SELL", or "HOLD"
        volatility: Volatility ratio (e.g., 0.02 = 2%)
        risk_level: "LOW", "MEDIUM", or "HIGH"

    Returns:
        Dict with entry_price, tp1, tp2, sl, risk_reward
    """
    if signal_direction == "HOLD" or price <= 0:
        return {
            "entry_price": price,
            "tp1": None,
            "tp2": None,
            "sl": None,
            "risk_reward": None
        }

    # Get multipliers based on risk level
    multipliers = RISK_MULTIPLIERS.get(risk_level, RISK_MULTIPLIERS["MEDIUM"])

    # Calculate distances
    tp1_distance = price * volatility * multipliers["tp1"]
    tp2_distance = price * volatility * multipliers["tp2"]
    sl_distance = price * volatility * multipliers["sl"]

    if signal_direction == "BUY":
        tp1 = price + tp1_distance
        tp2 = price + tp2_distance
        sl = price - sl_distance
    else:  # SELL
        tp1 = price - tp1_distance
        tp2 = price - tp2_distance
        sl = price + sl_distance

    # Calculate Risk/Reward ratio (based on TP1)
    risk = abs(price - sl)
    reward = abs(tp1 - price)
    risk_reward = reward / risk if risk > 0 else 0

    logger.info(f"  📐 TP/SL hesaplandı: Entry=${price:,.2f}, TP1=${tp1:,.2f}, TP2=${tp2:,.2f}, SL=${sl:,.2f}, R:R={risk_reward:.2f}")

    return {
        "entry_price": round(price, 8),
        "tp1": round(tp1, 8),
        "tp2": round(tp2, 8),
        "sl": round(sl, 8),
        "risk_reward": round(risk_reward, 2)
    }

def read_ai_signals_from_supabase(signal: Dict) -> List[Dict]:
    """
    Supabase satırından tüm AI sinyallerini oku (Robot 3 + Robot 8)
    """
    ai_signals = []

    # Robot 3 AI'ları
    if signal.get("deepseek_signal"):
        ai_signals.append({
            "signal": signal["deepseek_signal"],
            "confidence": signal.get("deepseek_confidence", 50),
            "reasoning": signal.get("deepseek_analysis", ""),
            "ai_model": "DeepSeek-V3"
        })

    if signal.get("claude_signal"):
        ai_signals.append({
            "signal": signal["claude_signal"],
            "confidence": signal.get("claude_confidence", 50),
            "reasoning": signal.get("claude_analysis", ""),
            "ai_model": "Claude-Sonnet-4"
        })

    if signal.get("gpt4_signal"):
        ai_signals.append({
            "signal": signal["gpt4_signal"],
            "confidence": signal.get("gpt4_confidence", 50),
            "reasoning": signal.get("gpt4_analysis", ""),
            "ai_model": "GPT-4o"
        })

    if signal.get("gemini_signal"):
        ai_signals.append({
            "signal": signal["gemini_signal"],
            "confidence": signal.get("gemini_confidence", 50),
            "reasoning": signal.get("gemini_analysis", ""),
            "ai_model": "Gemini-2.5-Pro"
        })

    if signal.get("grok_signal"):
        ai_signals.append({
            "signal": signal["grok_signal"],
            "confidence": signal.get("grok_confidence", 50),
            "reasoning": signal.get("grok_analysis", ""),
            "ai_model": "Grok-2"
        })

    # Robot 8: Personal AI
    if signal.get("personal_signal"):
        ai_signals.append({
            "signal": signal["personal_signal"],
            "confidence": signal.get("personal_confidence", 50),
            "reasoning": signal.get("personal_analysis", ""),
            "ai_model": "Personal-AI-Gemini"
        })

    return ai_signals


def run():
    """Main execution function for Robot 7 - BATCH MODE"""
    logger.info("=" * 80)
    logger.info("🎯 ROBOT 7: AI COMMAND CENTER - BATCH MODE")
    logger.info("=" * 80)

    processed = 0
    total_markets = 0
    error_msg = ""

    try:
        # Get pending BATCHES from Supabase (Robot 3 AND Robot 8 completed)
        pending_batches = get_pending_batches_for_robot(7)

        if not pending_batches:
            logger.info("⏳ Analiz bekleyen batch yok (Robot 7)")
            try:
                gc = get_gspread_client()
                sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
                update_monitoring(gc, sheet_id, 7, True, 0, "Bekleyen batch yok")
            except:
                pass
            return

        # Initialize assistant and command center
        assistant = create_assistant(BALANCED_PROFILE)
        command_center = create_command_center()

        logger.info(f"🎯 {len(pending_batches)} batch için meta-analiz başlıyor...")

        for batch_info in pending_batches:
            batch_id = batch_info["batch_id"]
            markets = batch_info["markets"]

            logger.info(f"\n{'='*60}")
            logger.info(f"📦 Batch: {batch_id} - {len(markets)} market")
            logger.info(f"{'='*60}")

            for market_info in markets:
                market = market_info["market"]
                signal = market_info["signal_data"]  # Full signal data from sequence 6
                price = float(signal["price"]) if signal.get("price") else 0

                total_markets += 1

                logger.info(f"\n📊 {market} @ ${price:,.2f}")

                # Read AI signals from the signal data
                ai_signals = read_ai_signals_from_supabase(signal)

                if len(ai_signals) == 0:
                    logger.warning(f"  ⚠️ AI sinyali bulunamadı")
                    continue

                logger.info(f"  📊 {len(ai_signals)} AI sinyali okundu")
                for sig in ai_signals:
                    logger.info(f"    • {sig['ai_model']}: {sig['signal']} ({sig['confidence']}%)")

                # Assistant AI evaluation
                logger.info(f"  👤 Asistan AI değerlendirmesi...")
                assistant_rec = assistant.evaluate_signals(market, ai_signals)

                # Command Center meta-analysis
                logger.info(f"  🎯 Komuta Merkezi meta-analizi...")
                final_decision = command_center.make_decision(market, price, ai_signals, assistant_rec)

                final_signal = final_decision["final_signal"]
                risk_level = final_decision.get("risk_level", "MEDIUM")

                logger.info(f"  🎯 NİHAİ: {final_signal} ({final_decision['final_confidence']}%)")
                logger.info(f"  ⚠️ Risk: {risk_level}")

                # Calculate TP/SL based on volatility and risk level
                volatility = calculate_volatility(signal)
                tp_sl = calculate_tp_sl(price, final_signal, volatility, risk_level)

                # Prepare update data
                update_data = {
                    "final_signal": final_signal,
                    "final_confidence": final_decision["final_confidence"],
                    "final_analysis": final_decision["reasoning"][:500],
                    "risk_level": risk_level,
                }

                # Add TP/SL values
                if tp_sl.get("entry_price"):
                    update_data["entry_price"] = tp_sl["entry_price"]
                if tp_sl.get("tp1"):
                    update_data["tp1"] = tp_sl["tp1"]
                if tp_sl.get("tp2"):
                    update_data["tp2"] = tp_sl["tp2"]
                if tp_sl.get("sl"):
                    update_data["sl"] = tp_sl["sl"]

                # Update ALL 6 sequences for this market in this batch
                success = update_batch_analysis(batch_id, market, 7, update_data)
                if success:
                    processed += 1
                    logger.info(f"  ✅ {market} güncellendi (6 satır)")
                else:
                    logger.error(f"  ❌ {market} güncellenemedi")

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 7 TAMAMLANDI")
        logger.info(f"   📦 Batch: {len(pending_batches)}")
        logger.info(f"   📊 İşlenen: {processed}/{total_markets} market")
        logger.info(f"   💾 Supabase: ✅")
        logger.info("=" * 80)

    except Exception as e:
        error_msg = str(e)[:50]
        logger.error(f"❌ ROBOT 7 BAŞARISIZ: {e}", exc_info=True)
        raise

    finally:
        # Update monitoring dashboard
        try:
            gc = get_gspread_client()
            sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
            update_monitoring(
                gc=gc,
                sheet_id=sheet_id,
                robot_number=7,
                success=processed > 0 or not error_msg,
                count=processed,
                detail=f"{processed} market analizi" if processed else "Bekleyen batch yok",
                error=error_msg
            )
        except Exception as e:
            logger.warning(f"Monitoring update failed: {e}")


if __name__ == "__main__":
    run()
