# robots/ai_command_center.py
# -*- coding: utf-8 -*-
"""
Robot 7: AI Command Center
Robot 3 ve Robot 8'den gelen tüm AI analizlerini okur, meta-analiz yapar ve nihai kararı verir
"""

import os
import time
import logging
import re
from typing import Dict, List, Optional

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.assistant_ai import create_assistant, BALANCED_PROFILE
from utils.meta_analyzer import create_command_center
from utils.supabase_client import get_pending_for_robot, update_robot_status
from utils.monitoring import update_robot_status as update_monitoring

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-7-AICommandCenter")

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
    """Main execution function for Robot 7"""
    logger.info("=" * 80)
    logger.info("🎯 ROBOT 7: AI COMMAND CENTER - BAŞLAT")
    logger.info("=" * 80)

    processed = 0
    error_msg = ""

    try:
        # Get pending signals from Supabase (Robot 3 AND Robot 8 completed)
        pending_signals = get_pending_for_robot(7)

        if not pending_signals:
            logger.warning("⚠️ Robot 7 için hazır sinyal yok (Robot 3 + Robot 8 tamamlanmamış)")
            try:
                gc = get_gspread_client()
                sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
                update_monitoring(gc, sheet_id, 7, True, 0, "İşlenecek veri yok")
            except:
                pass
            return

        # Initialize assistant and command center
        assistant = create_assistant(BALANCED_PROFILE)
        command_center = create_command_center()

        logger.info(f"🎯 {len(pending_signals)} sinyal için meta-analiz başlıyor...")

        for signal in pending_signals:
            signal_id = signal["id"]
            market = signal["market"]
            price = float(signal["price"]) if signal["price"] else 0

            logger.info(f"\n{'='*60}")
            logger.info(f"📊 {market} @ ${price:,.2f}")
            logger.info(f"{'='*60}")

            # Read AI signals from Supabase
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

            logger.info(f"  🎯 NİHAİ: {final_decision['final_signal']} ({final_decision['final_confidence']}%)")
            logger.info(f"  ⚠️ Risk: {final_decision.get('risk_level', 'MEDIUM')}")

            # Write to Supabase
            update_data = {
                "final_signal": final_decision["final_signal"],
                "final_confidence": final_decision["final_confidence"],
                "final_analysis": final_decision["reasoning"][:500],
                "risk_level": final_decision.get("risk_level", "MEDIUM"),
            }

            # Add TP/SL if available
            if final_decision.get("tp1"):
                update_data["tp1"] = final_decision["tp1"]
            if final_decision.get("tp2"):
                update_data["tp2"] = final_decision["tp2"]
            if final_decision.get("sl"):
                update_data["sl"] = final_decision["sl"]

            success = update_robot_status(signal_id, 7, update_data)
            if success:
                processed += 1
                logger.info(f"  ✅ Signal {signal_id} güncellendi")
            else:
                logger.error(f"  ❌ Signal {signal_id} güncellenemedi")

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 7 TAMAMLANDI")
        logger.info(f"   📊 İşlenen: {processed}/{len(pending_signals)}")
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
                detail=f"{processed} meta-analiz" if processed else "İşlenecek veri yok",
                error=error_msg
            )
        except Exception as e:
            logger.warning(f"Monitoring update failed: {e}")


if __name__ == "__main__":
    run()
