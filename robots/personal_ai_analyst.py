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
from utils.supabase_client import (
    get_unanalyzed_batches, get_market_history, update_batch_analysis
)
from utils.monitoring import update_robot_status as update_monitoring

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-8-PersonalAIAnalyst")


def format_trend_data(history: list) -> Dict:
    """Format 6-sequence trend data for AI analysis"""
    if not history:
        return {}

    prices = [float(h["price"]) for h in history if h.get("price")]
    if len(prices) >= 2:
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100
        trend_direction = "UP" if price_change > 0.5 else "DOWN" if price_change < -0.5 else "SIDEWAYS"
    else:
        price_change = 0
        trend_direction = "UNKNOWN"

    latest = history[-1] if history else {}

    return {
        "price_history": prices,
        "price_change_30min": price_change,
        "trend_direction": trend_direction,
        "latest_price": latest.get("price"),
        "latest_rsi": latest.get("rsi"),
        "latest_macd": latest.get("macd"),
        "latest_bb_upper": latest.get("bb_upper"),
        "latest_bb_middle": latest.get("bb_middle"),
        "latest_bb_lower": latest.get("bb_lower"),
    }


def run():
    """Main execution function for Robot 8 - POLLING MODE"""
    logger.info("=" * 80)
    logger.info("🤖 ROBOT 8: PERSONAL AI ANALYST - POLLING MODE")
    logger.info("=" * 80)

    processed = 0
    error_msg = ""

    try:
        # Check for unanalyzed batches
        unanalyzed = get_unanalyzed_batches(8)

        if not unanalyzed:
            logger.info("⏳ Analiz bekleyen batch yok (Robot 8)")
            try:
                gc = get_gspread_client()
                sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
                update_monitoring(gc, sheet_id, 8, True, 0, "Bekleyen batch yok")
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

        logger.info(f"🎯 {len(unanalyzed)} batch için Personal AI analizi başlıyor...")
        logger.info(f"   AI Model: GEMINI 2.5 PRO")

        for batch_info in unanalyzed:
            batch_id = batch_info["batch_id"]
            markets = batch_info["markets"]

            logger.info(f"\n{'='*60}")
            logger.info(f"📦 Batch: {batch_id} - {len(markets)} market")
            logger.info(f"{'='*60}")

            for market in markets:
                # Get 6-sequence trend data
                history = get_market_history(batch_id, market)

                if len(history) < 3:
                    logger.warning(f"  ⚠️ {market}: Yetersiz veri ({len(history)} sequence)")
                    continue

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
                    "trend_30min": trend_data["trend_direction"],
                    "price_change_30min": trend_data["price_change_30min"],
                    "price_history": trend_data["price_history"],
                }

                # Get personal AI analysis
                analysis = analyst.analyze(market, price, indicators)

                if not analysis:
                    logger.warning(f"  ⚠️ Personal AI analizi başarısız: {market}")
                    continue

                # Update all 6 sequences for this market
                update_data = {
                    "personal_signal": analysis["signal"],
                    "personal_confidence": analysis["confidence"],
                    "personal_analysis": analysis["reasoning"][:500]
                }

                success = update_batch_analysis(batch_id, market, 8, update_data)
                if success:
                    processed += 1
                    logger.info(f"  ✅ {analysis['signal']} ({analysis['confidence']}%)")
                else:
                    logger.error(f"  ❌ {market} güncellenemedi")

        # Calculate total markets
        total_markets = sum(len(b["markets"]) for b in unanalyzed)

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 8 TAMAMLANDI")
        logger.info(f"   📊 İşlenen: {processed}/{total_markets} market")
        logger.info(f"   📦 Batch: {len(unanalyzed)}")
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
                detail=f"{processed} market analizi" if processed else "Bekleyen batch yok",
                error=error_msg
            )
        except Exception as e:
            logger.warning(f"Monitoring update failed: {e}")


if __name__ == "__main__":
    run()
