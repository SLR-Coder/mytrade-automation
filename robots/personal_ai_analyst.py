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
from utils.common import get_latest_market_data, get_last_6_batches, status_text as common_status_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-8-PersonalAIAnalyst")

SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")


def analyze_temporal_trend(batches: List[Dict]) -> str:
    """
    Analyze temporal trend from 6 batches of data (same as Robot 3)

    Args:
        batches: List of batch data (oldest to newest)

    Returns:
        Human-readable trend summary string
    """
    if not batches or len(batches) < 2:
        return "İlk veri - trend analizi yok"

    prices = [b['price'] for b in batches if b.get('price', 0) > 0]
    if len(prices) < 2:
        return "Yetersiz fiyat verisi"

    # Calculate price movement
    start_price = prices[0]
    end_price = prices[-1]
    price_change_pct = ((end_price - start_price) / start_price) * 100

    # Calculate momentum (last 3 vs first 3)
    if len(prices) >= 6:
        first_half_avg = sum(prices[:3]) / 3
        second_half_avg = sum(prices[3:]) / 3
        momentum = "GÜÇLÜ YUKARI" if second_half_avg > first_half_avg * 1.01 else \
                   "GÜÇLÜ AŞAĞI" if second_half_avg < first_half_avg * 0.99 else "NÖTR"
    else:
        momentum = "YUKARI" if end_price > start_price else "AŞAĞI" if end_price < start_price else "NÖTR"

    # Count upward movements
    up_count = sum(1 for i in range(1, len(prices)) if prices[i] > prices[i-1])
    consistency = f"{up_count}/{len(prices)-1}"

    summary = f"Son 30 dk: Fiyat {price_change_pct:+.2f}%, Momentum: {momentum}, Tutarlılık: {consistency} yukarı"
    return summary


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
        for market_data in markets_data:
            market = market_data["market"]
            price = market_data["price"]
            indicators = market_data["indicators"]
            row_index = market_data["row_index"]

            # Status kontrolü - Robot 8 zaten işlenmişse atla (BB sütunu)
            try:
                current_status = ws.cell(row_index, cols.BB).value or ""
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

            # Write to Google Sheets (U-V columns: Asistan AI Sinyal + Analiz)
            try:
                # U: Signal + Confidence (Asistan AI Sinyal)
                ws.update_cell(row_index, cols.U, f"{analysis['signal']} ({analysis['confidence']}%)")

                # V: Detailed reasoning (Asistan AI Analizi)
                ws.update_cell(row_index, cols.V, analysis['reasoning'][:500])  # Truncate to 500 chars

                # Update status (Robot 8: BB sütunu)
                ws.update_cell(row_index, cols.BB, common_status_text(8, True))

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
