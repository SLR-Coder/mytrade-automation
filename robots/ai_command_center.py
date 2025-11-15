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
from utils.assistant_ai import create_assistant, BALANCED_PROFILE
from utils.meta_analyzer import create_command_center

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-7-AICommandCenter")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")


def status_text(robot_no: int, ok: bool) -> str:
    """Generate status text for robot"""
    return f"Robot {robot_no} {'✅' if ok else '❌'}"


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

    # Robot 3: 4 AI (V-AC)
    # DeepSeek (V-W)
    if len(row) > cols.V - 1 and row[cols.V - 1]:
        signal_data = parse_ai_column(row[cols.V - 1], "DeepSeek-V3")
        if signal_data:
            # Add reasoning if available
            if len(row) > cols.W - 1 and row[cols.W - 1]:
                signal_data["reasoning"] = row[cols.W - 1]
            ai_signals.append(signal_data)

    # Claude (X-Y)
    if len(row) > cols.X - 1 and row[cols.X - 1]:
        signal_data = parse_ai_column(row[cols.X - 1], "Claude-Sonnet-4")
        if signal_data:
            if len(row) > cols.Y - 1 and row[cols.Y - 1]:
                signal_data["reasoning"] = row[cols.Y - 1]
            ai_signals.append(signal_data)

    # GPT-4 (Z-AA)
    if len(row) > cols.Z - 1 and row[cols.Z - 1]:
        signal_data = parse_ai_column(row[cols.Z - 1], "GPT-4")
        if signal_data:
            if len(row) > cols.AA - 1 and row[cols.AA - 1]:
                signal_data["reasoning"] = row[cols.AA - 1]
            ai_signals.append(signal_data)

    # Grok (AB-AC)
    if len(row) > cols.AB - 1 and row[cols.AB - 1]:
        signal_data = parse_ai_column(row[cols.AB - 1], "Grok-3")
        if signal_data:
            if len(row) > cols.AC - 1 and row[cols.AC - 1]:
                signal_data["reasoning"] = row[cols.AC - 1]
            ai_signals.append(signal_data)

    # Robot 8: Personal AI (AD-AE)
    if len(row) > cols.AD - 1 and row[cols.AD - 1]:
        signal_data = parse_ai_column(row[cols.AD - 1], "Personal-AI")
        if signal_data:
            if len(row) > cols.AE - 1 and row[cols.AE - 1]:
                signal_data["reasoning"] = row[cols.AE - 1]
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
        sheet_id = get_secret("GOOGLE_SHEET_ID")

        # Get Google Sheets client
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        logger.info(f"✓ Google Sheets bağlantısı kuruldu: {SHEET_TAB}")

        # Get all rows
        all_rows = ws.get_all_values()

        if len(all_rows) <= 1:
            logger.warning("⚠️ Sheet'te veri yok")
            return

        # Find last separator
        separator_idx = None
        for i in range(len(all_rows) - 1, 0, -1):
            if len(all_rows[i]) > cols.AO - 1:
                if all_rows[i][cols.AO - 1] == "Ayırıcı":
                    separator_idx = i
                    break

        if separator_idx is None:
            data_rows = all_rows[1:]
        else:
            data_rows = all_rows[separator_idx + 1:]

        logger.info(f"✓ {len(data_rows)} piyasa satırı bulundu")

        # Initialize assistant and command center
        assistant = create_assistant(BALANCED_PROFILE)
        command_center = create_command_center()

        logger.info(f"\n🎯 Robot 3 ve Robot 8'den AI sinyalleri okunuyor...\n")

        # Process each market
        processed = 0
        for row in data_rows:
            # Skip empty rows
            if len(row) < cols.B or not row[cols.B - 1]:
                continue

            market = row[cols.B - 1]
            row_index = all_rows.index(row) + 1

            try:
                # Parse price
                price_str = row[cols.C - 1] if len(row) > cols.C - 1 and row[cols.C - 1] else "0"
                price = float(price_str.replace(",", "."))
            except:
                price = 0

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
            logger.info(f"  📝 Gerekçe: {final_decision['reasoning'][:100]}...")

            # Step 4: Write to Google Sheets (AF-AI columns)
            try:
                logger.info(f"\n💾 Komuta Merkezi kararı yazılıyor (AF-AI)...")

                # AF: Final Signal
                ws.update_cell(row_index, cols.AF, final_decision['final_signal'])

                # AG: Confidence %
                ws.update_cell(row_index, cols.AG, f"%{final_decision['final_confidence']}")

                # AH: Meta-Analysis (reasoning)
                ws.update_cell(row_index, cols.AH, final_decision['reasoning'][:500])  # Truncate

                # AI: Consensus %
                ws.update_cell(row_index, cols.AI, f"%{final_decision['consensus_score']}")

                # Update Robot 7 status
                ws.update_cell(row_index, cols.AO, status_text(7, True))

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
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ ROBOT 7 BAŞARISIZ: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()
