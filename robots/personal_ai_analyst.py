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
from utils.common import (
    get_latest_market_data, get_last_6_batches, status_text, analyze_temporal_trend,
    is_ready_for_analysis, BATCH_STATUS_READY
)  # DRY: All common functions from single source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-8-PersonalAIAnalyst")

SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")


# analyze_temporal_trend removed - now imported from utils.common


def run():
    """Main execution function for Robot 8"""
    logger.info("=" * 80)
    logger.info("ROBOT 8: PERSONAL AI ANALYST (TEMPORAL TREND ANALİZİ) - BAŞLAT")
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

        # Robot 8: ALWAYS uses Gemini 2.5 Pro with user's custom prompt
        ai_model = "gemini"  # FIXED: Always Gemini
        custom_prompt = os.getenv("PERSONAL_AI_CUSTOM_PROMPT", None)

        analyst = create_personal_analyst(
            ai_model=ai_model,
            custom_prompt=custom_prompt
        )

        logger.info(f"\n🎯 {len(markets_data)} piyasa için TEMPORAL TREND analizi başlıyor...")
        logger.info(f"  AI Model: GEMINI 2.5 PRO (Jirad Fusion)")
        if custom_prompt:
            logger.info(f"  Custom Prompt: {custom_prompt[:100]}...")
        else:
            logger.info(f"  Using default Jirad Fusion Multi-Engine prompt")

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

            # 2. Robot 8 status kontrolü - Zaten işlenmişse atla (BR sütunu)
            try:
                current_status = ws.cell(row_index, cols.BR).value or ""
                if "Robot 8" in current_status and "✅" in current_status:
                    logger.info(f"⏭️  {market} zaten işlenmiş (Robot 8 ✅), atlanıyor...")
                    continue
            except:
                pass  # Status okunamazsa devam et

            # Analyze temporal trend (last 30 minutes)
            temporal_summary = "İlk analiz - henüz geçmiş veri yok"
            if market in temporal_data and temporal_data[market]:
                temporal_summary = analyze_temporal_trend(temporal_data[market])
                logger.info(f"  📈 {temporal_summary}")

            # Add temporal summary to indicators (Personal AI will see this)
            indicators_with_trend = indicators.copy()
            indicators_with_trend['temporal_summary'] = temporal_summary

            logger.info(f"\n{'='*60}")
            logger.info(f"📊 {market} @ ${price:,.2f}")
            logger.info(f"{'='*60}")

            # Get personal AI analysis with temporal context
            analysis = analyst.analyze(market, price, indicators_with_trend)

            if not analysis:
                logger.warning(f"  Kisisel AI analizi basarisiz: {market}")
                continue

            # Write to Google Sheets (AG-AH columns: Asistan AI Sinyal + Analiz)
            try:
                # AG: Signal + Confidence (Asistan AI Sinyal)
                ws.update_cell(row_index, cols.AG, f"{analysis['signal']} ({analysis['confidence']}%)")

                # AH: Detailed reasoning (Asistan AI Analizi)
                ws.update_cell(row_index, cols.AH, analysis['reasoning'][:500])  # Truncate to 500 chars

                # Update status (Robot 8: BR sütunu)
                ws.update_cell(row_index, cols.BR, status_text(8, True))

                processed += 1
                logger.info(f"  {analysis['signal']} ({analysis['confidence']}%)")
                logger.info(f"  {analysis['reasoning'][:100]}...")
                logger.info(f"  Satir {row_index} guncellendi")

                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                logger.error(f"  Sheets yazma hatasi {market}: {e}")
                continue

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 8 TAMAMLANDI")
        logger.info(f"  İşlenen piyasa: {processed}/{len(markets_data)}")
        if skipped_not_ready > 0:
            logger.info(f"  ⏳ Beklemede (henüz hazır değil): {skipped_not_ready}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"ROBOT 8 BASARISIZ: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()
