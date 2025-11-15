# robots/ai_command_center.py
# -*- coding: utf-8 -*-
"""
Robot 7: AI Command Center
Tüm AI'ları paralel çalıştırıp komuta merkezinde birleştirir
"""

import os
import time
import asyncio
import logging
from typing import Dict, List, Optional

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.qwen_wrapper import get_qwen_signal
from utils.deepseek_wrapper import get_deepseek_signal
from utils.claude_wrapper import get_claude_signal
from utils.openai_wrapper import get_openai_signal
from utils.gemini_wrapper import get_gemini_signal
from utils.grok_wrapper import get_grok_signal
from utils.assistant_ai import create_assistant, BALANCED_PROFILE
from utils.meta_analyzer import create_command_center

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-7-AICommandCenter")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")


def status_text(robot_no: int, ok: bool) -> str:
    """Generate status text for robot"""
    return f"Robot {robot_no} {'✅' if ok else '❌'}"


def get_latest_market_data(ws, cols) -> List[Dict]:
    """
    Read latest market data from Google Sheets

    Returns list of market data dicts with indicators
    """
    logger.info("📊 En son piyasa verilerini okuyorum...")

    # Get all rows
    all_rows = ws.get_all_values()

    if len(all_rows) <= 1:
        logger.warning("Sheet'te veri yok")
        return []

    # Find last separator
    separator_idx = None
    for i in range(len(all_rows) - 1, 0, -1):
        if len(all_rows[i]) > cols.AH - 1:
            if all_rows[i][cols.AH - 1] == "Ayırıcı":
                separator_idx = i
                break

    if separator_idx is None:
        logger.warning("Ayırıcı bulunamadı, tüm veriler kullanılıyor")
        data_rows = all_rows[1:]
    else:
        data_rows = all_rows[separator_idx + 1:]

    logger.info(f"✓ {len(data_rows)} piyasa bulundu")

    # Parse market data
    markets_data = []
    for row in data_rows:
        if len(row) < cols.B:
            continue

        market = row[cols.B - 1] if len(row) > cols.B - 1 else ""
        if not market or market == "":
            continue

        try:
            # Parse price
            price_str = row[cols.C - 1] if len(row) > cols.C - 1 and row[cols.C - 1] else "0"
            price_str = price_str.replace(",", ".")
            price = float(price_str)
        except:
            price = 0

        # Parse indicators
        indicators = {}
        try:
            def parse_float(value):
                if not value:
                    return None
                return float(str(value).replace(",", "."))

            if len(row) > cols.F - 1 and row[cols.F - 1]:
                indicators['rsi'] = parse_float(row[cols.F - 1])
            if len(row) > cols.G - 1 and row[cols.G - 1]:
                indicators['macd'] = parse_float(row[cols.G - 1])
            if len(row) > cols.H - 1 and row[cols.H - 1]:
                indicators['macd_signal'] = parse_float(row[cols.H - 1])
            if len(row) > cols.I - 1 and row[cols.I - 1]:
                indicators['macd_histogram'] = parse_float(row[cols.I - 1])
            if len(row) > cols.J - 1 and row[cols.J - 1]:
                indicators['bb_upper'] = parse_float(row[cols.J - 1])
            if len(row) > cols.K - 1 and row[cols.K - 1]:
                indicators['bb_middle'] = parse_float(row[cols.K - 1])
            if len(row) > cols.L - 1 and row[cols.L - 1]:
                indicators['bb_lower'] = parse_float(row[cols.L - 1])
            if len(row) > cols.M - 1 and row[cols.M - 1]:
                indicators['ema_9'] = parse_float(row[cols.M - 1])
            if len(row) > cols.N - 1 and row[cols.N - 1]:
                indicators['ema_21'] = parse_float(row[cols.N - 1])
            if len(row) > cols.O - 1 and row[cols.O - 1]:
                indicators['ema_50'] = parse_float(row[cols.O - 1])
            if len(row) > cols.P - 1 and row[cols.P - 1]:
                indicators['ema_200'] = parse_float(row[cols.P - 1])

            # Support/Resistance
            support_levels = []
            resistance_levels = []
            if len(row) > cols.Q - 1 and row[cols.Q - 1]:
                val = parse_float(row[cols.Q - 1])
                if val:
                    support_levels.append(val)
            if len(row) > cols.R - 1 and row[cols.R - 1]:
                val = parse_float(row[cols.R - 1])
                if val:
                    resistance_levels.append(val)

            indicators['support_levels'] = support_levels
            indicators['resistance_levels'] = resistance_levels

            # Trend
            if len(row) > cols.S - 1 and row[cols.S - 1]:
                indicators['trend'] = row[cols.S - 1]

        except Exception as e:
            logger.warning(f"Indicator parse hatası {market}: {e}")

        markets_data.append({
            "market": market,
            "price": price,
            "indicators": indicators,
            "row_index": all_rows.index(row) + 1
        })

    return markets_data


async def collect_ai_signals(market: str, price: float, indicators: Dict) -> List[Dict]:
    """
    Tüm AI'lardan paralel olarak sinyal topla

    Args:
        market: Piyasa adı
        price: Mevcut fiyat
        indicators: Teknik göstergeler

    Returns:
        AI sinyalleri listesi
    """
    logger.info(f"\n🤖 {market} için 5 AI'dan paralel sinyal topluyorum...")

    # Paralel AI çağrıları
    loop = asyncio.get_event_loop()

    tasks = [
        loop.run_in_executor(None, get_qwen_signal, market, price, indicators),
        loop.run_in_executor(None, get_deepseek_signal, market, price, indicators),
        loop.run_in_executor(None, get_claude_signal, market, price, indicators),
        loop.run_in_executor(None, get_openai_signal, market, price, indicators),
        loop.run_in_executor(None, get_gemini_signal, market, price, indicators),
        loop.run_in_executor(None, get_grok_signal, market, price, indicators),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out errors
    ai_signals = []
    for i, result in enumerate(results):
        ai_names = ["Qwen", "DeepSeek", "Claude", "OpenAI", "Gemini", "Grok"]
        if isinstance(result, Exception):
            logger.warning(f"  ⚠️ {ai_names[i]} başarısız: {result}")
        elif result is not None:
            ai_signals.append(result)
            logger.info(f"  ✅ {ai_names[i]}: {result['signal']} (%{result['confidence']})")

    logger.info(f"  📊 Toplam {len(ai_signals)}/6 AI'dan sinyal alındı")
    return ai_signals


async def run():
    """Main execution function for Robot 7"""
    logger.info("=" * 80)
    logger.info("🎯 ROBOT 7: AI COMMAND CENTER - BAŞLAT")
    logger.info("=" * 80)

    try:
        # Get secrets
        sheet_id = get_secret("GOOGLE_SHEET_ID")

        # Get Google Sheets client
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        logger.info(f"✓ Google Sheets bağlantısı kuruldu: {SHEET_TAB}")

        # Get latest market data
        markets_data = get_latest_market_data(ws, cols)

        if not markets_data:
            logger.warning("⚠️ Analiz edilecek piyasa verisi yok")
            return

        # Initialize assistant and command center
        assistant = create_assistant(BALANCED_PROFILE)  # Kullanıcı profili
        command_center = create_command_center()

        logger.info(f"\n🎯 {len(markets_data)} piyasa için AI Command Center analizi başlıyor...\n")

        # Process each market
        processed = 0
        for market_data in markets_data:
            market = market_data["market"]
            price = market_data["price"]
            indicators = market_data["indicators"]
            row_index = market_data["row_index"]

            logger.info(f"\n{'='*60}")
            logger.info(f"📊 {market} @ ${price:,.2f}")
            logger.info(f"{'='*60}")

            # Step 1: Collect AI signals (parallel)
            ai_signals = await collect_ai_signals(market, price, indicators)

            if len(ai_signals) == 0:
                logger.warning(f"  ⚠️ Hiçbir AI'dan sinyal alınamadı: {market}")
                continue

            # Step 2: Assistant AI evaluation
            logger.info(f"\n👤 Asistan AI değerlendiriliyor...")
            assistant_rec = assistant.evaluate_signals(market, ai_signals)
            logger.info(f"  {'✅' if assistant_rec['approved'] else '❌'} {assistant_rec['recommendation']}: {assistant_rec['reasoning']}")

            # Step 3: Command Center decision
            logger.info(f"\n🎯 Komuta Merkezi nihai kararı veriyor...")
            final_decision = command_center.make_decision(market, price, ai_signals, assistant_rec)
            logger.info(f"  🎯 NİHAİ KARAR: {final_decision['final_signal']} (%{final_decision['final_confidence']})")
            logger.info(f"  📝 Gerekçe: {final_decision['reasoning'][:150]}...")

            # Step 4: Write to Google Sheets
            try:
                logger.info(f"\n💾 Google Sheets'e yazılıyor...")

                # Write individual AI signals
                for sig in ai_signals:
                    if sig['ai_model'] == "Qwen2.5-Max":
                        ws.update_cell(row_index, cols.AJ, f"{sig['signal']} ({sig['confidence']}%)")
                    elif sig['ai_model'] == "DeepSeek-V3":
                        ws.update_cell(row_index, cols.AK, f"{sig['signal']} ({sig['confidence']}%)")
                    elif sig['ai_model'] == "Claude-Opus-4":
                        # Claude zaten W kolonunda, güncelleme
                        pass
                    elif sig['ai_model'] == "GPT-4":
                        # GPT-4 zaten V kolonunda, güncelleme
                        pass
                    elif sig['ai_model'] == "Gemini-2.0-Flash-Exp":
                        # Gemini zaten X kolonunda, güncelleme
                        pass
                    elif sig['ai_model'] == "Grok-3":
                        ws.update_cell(row_index, cols.AL, f"{sig['signal']} ({sig['confidence']}%)")

                # Write Assistant AI recommendation
                ws.update_cell(row_index, cols.AM, f"{assistant_rec['recommendation']} ({assistant_rec['avg_confidence']:.0f}%)")

                # Write Command Center decision
                ws.update_cell(row_index, cols.AN, final_decision['final_signal'])
                ws.update_cell(row_index, cols.AO, final_decision['reasoning'][:500])  # Truncate
                ws.update_cell(row_index, cols.AP, f"{final_decision['consensus_score']}%")

                # Update Robot 7 status
                ws.update_cell(row_index, cols.AH, status_text(7, True))

                processed += 1
                logger.info(f"  ✓ Satır {row_index} güncellendi")

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                logger.error(f"  ❌ Sheets yazma hatası {market}: {e}")
                continue

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 7 TAMAMLANDI")
        logger.info(f"  İşlenen piyasa: {processed}/{len(markets_data)}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ ROBOT 7 BAŞARISIZ: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(run())
