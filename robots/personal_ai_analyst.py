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
from utils.assistant_ai import create_personal_analyst
from utils.supabase_client import get_pending_for_robot, update_robot_status
from utils.monitoring import update_robot_status as update_monitoring

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-8-PersonalAIAnalyst")

def run():
    """Main execution function for Robot 8"""
    logger.info("=" * 80)
    logger.info("🤖 ROBOT 8: PERSONAL AI ANALYST - BAŞLAT")
    logger.info("=" * 80)

    processed = 0
    error_msg = ""

    try:
        # Get pending signals from Supabase
        pending_signals = get_pending_for_robot(8)

        if not pending_signals:
            logger.warning("⚠️ İşlenecek sinyal yok (Robot 8 için)")
            try:
                gc = get_gspread_client()
                sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
                update_monitoring(gc, sheet_id, 8, True, 0, "İşlenecek veri yok")
            except:
                pass
            return

        # Robot 8: ALWAYS uses Gemini with user's custom prompt
        ai_model = "gemini"
        custom_prompt = os.getenv("PERSONAL_AI_CUSTOM_PROMPT", None)

        analyst = create_personal_analyst(
            ai_model=ai_model,
            custom_prompt=custom_prompt
        )

        logger.info(f"🎯 {len(pending_signals)} sinyal için Personal AI analizi başlıyor...")
        logger.info(f"   AI Model: GEMINI 2.5 PRO")

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
            }

            logger.info(f"\n{'='*60}")
            logger.info(f"📊 {market} @ ${price:,.2f}")
            logger.info(f"{'='*60}")

            # Get personal AI analysis
            analysis = analyst.analyze(market, price, indicators)

            if not analysis:
                logger.warning(f"  ⚠️ Personal AI analizi başarısız: {market}")
                continue

            # Write to Supabase
            update_data = {
                "personal_signal": analysis["signal"],
                "personal_confidence": analysis["confidence"],
                "personal_analysis": analysis["reasoning"][:500]
            }

            success = update_robot_status(signal_id, 8, update_data)
            if success:
                processed += 1
                logger.info(f"  ✅ {analysis['signal']} ({analysis['confidence']}%)")
                logger.info(f"  {analysis['reasoning'][:100]}...")
            else:
                logger.error(f"  ❌ Signal {signal_id} güncellenemedi")

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 8 TAMAMLANDI")
        logger.info(f"   📊 İşlenen: {processed}/{len(pending_signals)}")
        logger.info(f"   💾 Supabase: ✅")
        logger.info("=" * 80)

    except Exception as e:
        error_msg = str(e)[:50]
        logger.error(f"❌ ROBOT 8 BAŞARISIZ: {e}", exc_info=True)
        raise

    finally:
        # Update monitoring dashboard
        try:
            gc = get_gspread_client()
            sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
            update_monitoring(
                gc=gc,
                sheet_id=sheet_id,
                robot_number=8,
                success=processed > 0 or not error_msg,
                count=processed,
                detail=f"{processed} Personal AI analizi" if processed else "İşlenecek veri yok",
                error=error_msg
            )
        except Exception as e:
            logger.warning(f"Monitoring update failed: {e}")


if __name__ == "__main__":
    run()
