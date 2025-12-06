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
from utils.schema import resolve_columns
from utils.common import (
    status_text, is_ready_for_analysis, BATCH_STATUS_READY,
    get_rows_ready_for_command_center  # ROBUST: Zamanlama bağımsız satır bulma
)  # DRY: Import from common
from utils.assistant_ai import create_assistant, BALANCED_PROFILE
from utils.meta_analyzer import create_command_center

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-7-AICommandCenter")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")


def parse_ai_column(value: str, ai_name: str) -> Optional[Dict]:
    """
    AI sütunundan sinyal ve confidence parse et

    Format: "BUY (75%)" veya "SELL (60%)" veya "HOLD (50%)"

    Returns:
        {"signal": "BUY", "confidence": 75, "ai_model": "DeepSeek"} veya None
    """
    if not value or value.strip() == "":
        return None

    try:
        # Match pattern: "SIGNAL (CONFIDENCE%)"
        match = re.match(r'(BUY|SELL|HOLD)\s*\((\d+)%?\)', value.strip(), re.IGNORECASE)
        if match:
            signal = match.group(1).upper()
            confidence = int(match.group(2))

            return {
                "signal": signal,
                "confidence": confidence,
                "ai_model": ai_name
            }
        else:
            logger.warning(f"AI column parse failed for {ai_name}: '{value}'")
            return None

    except Exception as e:
        logger.warning(f"AI parse error for {ai_name}: {e}")
        return None


def read_ai_signals(row: List[str], cols) -> List[Dict]:
    """
    Google Sheets satırından tüm AI sinyallerini oku (Robot 3 + Robot 8)

    Args:
        row: Google Sheets satırı
        cols: Column mapping

    Returns:
        AI sinyalleri listesi
    """
    ai_signals = []

    # Robot 8: Personal AI (AG-AH)
    if len(row) > cols.AG - 1 and row[cols.AG - 1]:
        signal_data = parse_ai_column(row[cols.AG - 1], "Personal-AI-Gemini")
        if signal_data:
            if len(row) > cols.AH - 1 and row[cols.AH - 1]:
                signal_data["reasoning"] = row[cols.AH - 1]
            ai_signals.append(signal_data)

    # Robot 3 AI'ları:
    # GPT-4 (AI-AJ)
    if len(row) > cols.AI - 1 and row[cols.AI - 1]:
        signal_data = parse_ai_column(row[cols.AI - 1], "GPT-4o")
        if signal_data:
            if len(row) > cols.AJ - 1 and row[cols.AJ - 1]:
                signal_data["reasoning"] = row[cols.AJ - 1]
            ai_signals.append(signal_data)

    # Claude (AK-AL)
    if len(row) > cols.AK - 1 and row[cols.AK - 1]:
        signal_data = parse_ai_column(row[cols.AK - 1], "Claude-Sonnet-4")
        if signal_data:
            if len(row) > cols.AL - 1 and row[cols.AL - 1]:
                signal_data["reasoning"] = row[cols.AL - 1]
            ai_signals.append(signal_data)

    # Gemini (AM-AN)
    if len(row) > cols.AM - 1 and row[cols.AM - 1]:
        signal_data = parse_ai_column(row[cols.AM - 1], "Gemini-2.0-Flash")
        if signal_data:
            if len(row) > cols.AN - 1 and row[cols.AN - 1]:
                signal_data["reasoning"] = row[cols.AN - 1]
            ai_signals.append(signal_data)

    # Grok (AO-AP)
    if len(row) > cols.AO - 1 and row[cols.AO - 1]:
        signal_data = parse_ai_column(row[cols.AO - 1], "Grok-2")
        if signal_data:
            if len(row) > cols.AP - 1 and row[cols.AP - 1]:
                signal_data["reasoning"] = row[cols.AP - 1]
            ai_signals.append(signal_data)

    # DeepSeek (AQ-AR)
    if len(row) > cols.AQ - 1 and row[cols.AQ - 1]:
        signal_data = parse_ai_column(row[cols.AQ - 1], "DeepSeek-V3")
        if signal_data:
            if len(row) > cols.AR - 1 and row[cols.AR - 1]:
                signal_data["reasoning"] = row[cols.AR - 1]
            ai_signals.append(signal_data)

    logger.info(f"  📊 {len(ai_signals)} AI sinyali okundu (Robot 3 + Robot 8)")
    return ai_signals


def run():
    """Main execution function for Robot 7"""
    logger.info("=" * 80)
    logger.info("🎯 ROBOT 7: AI COMMAND CENTER (META-ANALİZ) - BAŞLAT")
    logger.info("=" * 80)

    try:
        # Get secrets
        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")

        # Get Google Sheets client
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        logger.info(f"✓ Google Sheets bağlantısı kuruldu: {SHEET_TAB}")

        # ROBUST APPROACH: Find ALL rows where Robot 3 AND Robot 8 are complete
        # This is TIMING-INDEPENDENT - works even if timing is off!
        ready_rows = get_rows_ready_for_command_center(ws, cols)
        if not ready_rows:
            logger.warning("⚠️ Robot 7 için hazır satır yok (Robot 3 + Robot 8 tamamlanmamış)")
            return

        # Initialize assistant and command center
        assistant = create_assistant(BALANCED_PROFILE)
        command_center = create_command_center()

        logger.info(f"\n🎯 Robot 3 ve Robot 8'den AI sinyalleri okunuyor...\n")

        # Process each market
        processed = 0

        for market_data in ready_rows:
            market = market_data["market"]
            price = market_data["price"]
            row_index = market_data["row_index"]
            row = market_data["row_data"]

            # NOTE: All prerequisite checks are done in get_rows_ready_for_command_center()
            # No need to check Robot 1/3/8 status again here!

            logger.info(f"\n{'='*60}")
            logger.info(f"📊 {market} @ ${price:,.2f} (Satır {row_index})")
            logger.info(f"{'='*60}")

            # Step 1: Read AI signals from columns (Robot 3 + Robot 8)
            ai_signals = read_ai_signals(row, cols)

            if len(ai_signals) == 0:
                logger.warning(f"  ⚠️ Bu piyasa için AI sinyali bulunamadı (Robot 3 ve 8 henüz çalışmamış olabilir)")
                continue

            logger.info(f"\n  Okunan AI'lar:")
            for sig in ai_signals:
                reasoning_preview = sig.get('reasoning', 'Yok')[:50]
                logger.info(f"    • {sig['ai_model']}: {sig['signal']} ({sig['confidence']}%) - {reasoning_preview}...")

            # Step 2: Assistant AI evaluation
            logger.info(f"\n👤 Asistan AI değerlendirmesi...")
            assistant_rec = assistant.evaluate_signals(market, ai_signals)
            logger.info(f"  {'✅' if assistant_rec['approved'] else '❌'} {assistant_rec['recommendation']}")
            logger.info(f"  📝 {assistant_rec['reasoning']}")

            # Step 3: Command Center meta-analysis
            logger.info(f"\n🎯 Komuta Merkezi meta-analizi yapıyor...")
            final_decision = command_center.make_decision(market, price, ai_signals, assistant_rec)
            logger.info(f"  🎯 NİHAİ KARAR: {final_decision['final_signal']} (%{final_decision['final_confidence']})")
            logger.info(f"  📊 Consensus: %{final_decision['consensus_score']}")
            logger.info(f"  ⚠️  Risk: {final_decision.get('risk_level', 'MEDIUM')}")
            logger.info(f"  🎬 Aksiyon: {final_decision.get('suggested_action', 'SET ALERT')}")
            logger.info(f"  📝 Gerekçe: {final_decision['reasoning'][:150]}...")

            # Step 4: Write to Google Sheets (AS-AX columns: Robot 7 Komuta Merkezi)
            try:
                logger.info(f"\n💾 Komuta Merkezi kararı yazılıyor (AS-AX)...")

                # AS: KM Nihai Sinyal (BUY/SELL/HOLD)
                ws.update_cell(row_index, cols.AS, final_decision['final_signal'])

                # AT: KM Güven %
                ws.update_cell(row_index, cols.AT, f"%{final_decision['final_confidence']}")

                # AU: KM Meta-Analiz (Detaylı açıklama)
                ws.update_cell(row_index, cols.AU, final_decision['reasoning'][:500])  # Truncate

                # AV: KM Consensus %
                ws.update_cell(row_index, cols.AV, f"%{final_decision['consensus_score']}")

                # AW: KM Risk Level (LOW/MEDIUM/HIGH)
                ws.update_cell(row_index, cols.AW, final_decision.get('risk_level', 'MEDIUM'))

                # AX: KM Önerilen Aksiyon (ENTER NOW/WAIT/AVOID/etc.)
                ws.update_cell(row_index, cols.AX, final_decision.get('suggested_action', 'SET ALERT'))

                # Update Robot 7 status (BQ sütunu)
                ws.update_cell(row_index, cols.BQ, status_text(7, True))

                processed += 1
                logger.info(f"  ✅ Satır {row_index} güncellendi")

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                logger.error(f"  ❌ Sheets yazma hatası: {e}")
                continue

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 7 TAMAMLANDI")
        logger.info(f"  İşlenen piyasa: {processed}/{len(data_rows)}")
        if skipped_not_ready > 0:
            logger.info(f"  ⏳ Beklemede (toplam): {skipped_not_ready}")
            if skipped_robot1 > 0:
                logger.info(f"     └─ Robot 1 (veri) bekliyor: {skipped_robot1}")
            if skipped_robot3 > 0:
                logger.info(f"     └─ Robot 3 (AI sinyal) bekliyor: {skipped_robot3}")
            if skipped_robot8 > 0:
                logger.info(f"     └─ Robot 8 (Personal AI) bekliyor: {skipped_robot8}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ ROBOT 7 BAŞARISIZ: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()
