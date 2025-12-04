# robots/tp_monitor.py
# -*- coding: utf-8 -*-
"""
Robot 9: Real-Time TP/SL Monitor
Açık pozisyonları izler ve TP1/TP2/SL seviyelerine ulaşıldığında Telegram bildirimi gönderir.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from telegram import Bot
from telegram.constants import ParseMode

from config.constants import (
    SHEETS_RATE_LIMIT_SLEEP,
    DEFAULT_SHEET_TAB,
    CRYPTO_SYMBOLS
)
from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.common import parse_float, status_text
from utils.api_clients import (
    BinanceClient,
    TwelveDataClient,
    PolygonClient,
    AlphaVantageClient
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-9-TPMonitor")

SHEET_TAB = os.getenv("SHEET_TAB", DEFAULT_SHEET_TAB)


def get_current_price(market: str) -> Optional[float]:
    """
    Fetch current market price from data providers.

    Args:
        market: Market symbol (e.g., "BTC/USDT", "EUR/USD")

    Returns:
        Current price or None if failed
    """
    try:
        # Determine market type using constants
        if "/" in market and any(crypto in market.upper() for crypto in CRYPTO_SYMBOLS):
            # Crypto market - use Binance
            # Convert "BTC/USDT" to "BTCUSDT"
            symbol = market.replace("/", "")
            binance = BinanceClient()
            result = binance.get_price(symbol)
            if result and "price" in result:
                return float(result["price"])
        else:
            # Forex/Commodity - use TwelveData
            twelve = TwelveDataClient()
            quote = twelve.get_quote(market)
            if quote and "close" in quote:
                return float(quote["close"])

        logger.warning(f"  ⚠️  Fiyat alınamadı {market}")
        return None
    except Exception as e:
        logger.error(f"  ❌ Fiyat hatası {market}: {e}")
        return None


def calculate_profit_pips(entry: float, current: float, signal: str, market: str) -> tuple:
    """
    Calculate profit in pips and percentage.

    Args:
        entry: Entry price
        current: Current price
        signal: BUY or SELL
        market: Market symbol

    Returns:
        (pips, percentage) tuple
    """
    # Calculate percentage
    if signal == "BUY":
        pct = ((current - entry) / entry) * 100
    else:  # SELL
        pct = ((entry - current) / entry) * 100

    # Calculate pips (forex uses pips, crypto uses percentage)
    if "USD" in market and "/" not in market:
        # Forex pair
        # For JPY pairs, 1 pip = 0.01, for others 1 pip = 0.0001
        if "JPY" in market:
            pips = abs(current - entry) * 100
        else:
            pips = abs(current - entry) * 10000

        if signal == "SELL":
            pips = pips if entry > current else -pips
        else:  # BUY
            pips = pips if current > entry else -pips
    else:
        # Crypto - use percentage as "pips"
        pips = pct

    return pips, pct


def send_tp_notification(bot: Bot, chat_id: str, market: str, signal: str,
                         tp_level: str, entry: float, tp_price: float,
                         current_price: float, pips: float, pct: float):
    """
    Send TP hit notification to Telegram.

    Format: "XAU Take-Profit 💸 Target: 1✅ Profit: +20 pips 🤑"
    """
    try:
        position = "LONG" if signal == "BUY" else "SHORT"
        emoji = "💸" if pips > 0 else "⚠️"
        profit_emoji = "🤑" if pips > 0 else "😐"

        # Determine if pips or percentage should be shown
        if "/" in market:  # Crypto - show percentage
            profit_text = f"{pct:+.2f}%"
        else:  # Forex - show pips
            profit_text = f"{pips:+.1f} pips"

        message = f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>🎯 HEDEF VURULDU! {emoji}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Market:</b> {market}
<b>Pozisyon:</b> {position}
<b>Hedef:</b> {tp_level} ✅

<b>📊 FİYAT BİLGİSİ:</b>
├─ Giriş: ${entry:,.2f}
├─ Hedef: ${tp_price:,.2f}
└─ Şu Anki: ${current_price:,.2f}

<b>💰 KÂR:</b> {profit_text} {profit_emoji}

<i>Tebrikler! Hedef başarıyla vuruldu! 🎉</i>
"""

        bot.send_message(
            chat_id=chat_id,
            text=message.strip(),
            parse_mode=ParseMode.HTML
        )
        logger.info(f"  ✅ {tp_level} bildirimi gönderildi: {market} ({profit_text})")

    except Exception as e:
        logger.error(f"  ❌ Telegram bildirimi gönderilemedi: {e}")


def send_sl_notification(bot: Bot, chat_id: str, market: str, signal: str,
                         entry: float, sl_price: float, current_price: float,
                         pips: float, pct: float):
    """
    Send SL hit notification to Telegram.
    """
    try:
        position = "LONG" if signal == "BUY" else "SHORT"

        # Determine if pips or percentage should be shown
        if "/" in market:  # Crypto - show percentage
            loss_text = f"{pct:.2f}%"
        else:  # Forex - show pips
            loss_text = f"{abs(pips):.1f} pips"

        message = f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>🚨 STOP LOSS VURULDU!</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Market:</b> {market}
<b>Pozisyon:</b> {position}

<b>📊 FİYAT BİLGİSİ:</b>
├─ Giriş: ${entry:,.2f}
├─ Stop Loss: ${sl_price:,.2f}
└─ Şu Anki: ${current_price:,.2f}

<b>📉 ZARAR:</b> -{loss_text} 😔

<i>Pozisyon kapatıldı. Bir sonraki fırsatı kolluyoruz! 💪</i>
"""

        bot.send_message(
            chat_id=chat_id,
            text=message.strip(),
            parse_mode=ParseMode.HTML
        )
        logger.info(f"  ✅ SL bildirimi gönderildi: {market} (-{loss_text})")

    except Exception as e:
        logger.error(f"  ❌ Telegram bildirimi gönderilemedi: {e}")


def run():
    """Main execution function for Robot 9"""
    logger.info("=" * 80)
    logger.info("🎯 ROBOT 9: TP/SL MONITOR - BAŞLAT")
    logger.info("=" * 80)

    try:
        # Initialize services
        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
        telegram_token = get_secret("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = get_secret("TELEGRAM_CHAT_ID")

        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        bot = Bot(token=telegram_token)

        # Read all rows
        all_rows = ws.get_all_values()

        if len(all_rows) < 2:
            logger.info("  ℹ️  Veri yok")
            return

        # Skip header row
        data_rows = all_rows[1:]

        # Track open positions
        open_positions = []

        for i, row in enumerate(data_rows, start=2):  # Row 2 is first data row
            row_index = i

            # Check if this row has a trading signal
            if len(row) <= cols.AG - 1:
                continue

            final_signal = row[cols.AG - 1] if len(row) > cols.AG - 1 else ""

            # Only monitor BUY/SELL signals (not HOLD)
            if final_signal not in ["BUY", "SELL"]:
                continue

            # Get market and prices
            market = row[cols.B - 1] if len(row) > cols.B - 1 else ""

            # Skip separator rows
            if not market or "📊" in market or "RAPORU" in market:
                continue

            # Get Entry/TP/SL prices (Robot 3 columns: AM-AQ)
            entry_str = row[cols.AM - 1] if len(row) > cols.AM - 1 else ""
            sl_str = row[cols.AN - 1] if len(row) > cols.AN - 1 else ""
            tp1_str = row[cols.AO - 1] if len(row) > cols.AO - 1 else ""
            tp2_str = row[cols.AP - 1] if len(row) > cols.AP - 1 else ""

            # Parse prices
            entry_price = parse_float(entry_str.replace("$", "").replace(",", "")) if entry_str else None
            sl_price = parse_float(sl_str.replace("$", "").replace(",", "")) if sl_str else None
            tp1_price = parse_float(tp1_str.replace("$", "").replace(",", "")) if tp1_str else None
            tp2_price = parse_float(tp2_str.replace("$", "").replace(",", "")) if tp2_str else None

            # Skip if no valid prices
            if not entry_price or not sl_price:
                continue

            # Check hit status (new columns: BC, BD, BE, BF)
            tp1_hit = row[cols.BC - 1] if len(row) > cols.BC - 1 else ""
            tp2_hit = row[cols.BD - 1] if len(row) > cols.BD - 1 else ""
            sl_hit = row[cols.BE - 1] if len(row) > cols.BE - 1 else ""
            position_status = row[cols.BF - 1] if len(row) > cols.BF - 1 else ""

            # Skip closed positions
            if position_status == "CLOSED":
                continue

            open_positions.append({
                "row_index": row_index,
                "market": market,
                "signal": final_signal,
                "entry": entry_price,
                "sl": sl_price,
                "tp1": tp1_price,
                "tp2": tp2_price,
                "tp1_hit": tp1_hit == "YES",
                "tp2_hit": tp2_hit == "YES",
                "sl_hit": sl_hit == "YES",
                "position_status": position_status
            })

        logger.info(f"\n📊 {len(open_positions)} açık pozisyon bulundu\n")

        if not open_positions:
            logger.info("  ℹ️  Takip edilecek açık pozisyon yok")
            # Update Robot 9 status
            ws.update_cell(2, cols.BG, status_text(9, True))
            return

        # Monitor each position
        monitored = 0
        notifications_sent = 0

        for pos in open_positions:
            logger.info(f"🔍 Kontrol: {pos['market']} ({pos['signal']})")
            logger.info(f"  Giriş: ${pos['entry']:,.2f} | SL: ${pos['sl']:,.2f} | TP1: ${pos['tp1']:,.2f} | TP2: ${pos['tp2']:,.2f}")

            # Fetch current price
            current_price = get_current_price(pos['market'])

            if not current_price:
                logger.warning(f"  ⚠️  Fiyat alınamadı, atlanıyor...")
                continue

            logger.info(f"  Şu anki fiyat: ${current_price:,.2f}")

            # Check TP1
            if pos['tp1'] and not pos['tp1_hit']:
                tp1_hit = False
                if pos['signal'] == "BUY" and current_price >= pos['tp1']:
                    tp1_hit = True
                elif pos['signal'] == "SELL" and current_price <= pos['tp1']:
                    tp1_hit = True

                if tp1_hit:
                    pips, pct = calculate_profit_pips(pos['entry'], current_price, pos['signal'], pos['market'])
                    logger.info(f"  🎯 TP1 VURULDU! Kâr: {pips:+.1f} pips ({pct:+.2f}%)")

                    # Send notification
                    send_tp_notification(bot, telegram_chat_id, pos['market'], pos['signal'],
                                        "TP1", pos['entry'], pos['tp1'], current_price, pips, pct)

                    # Update sheet
                    ws.update_cell(pos['row_index'], cols.BC, "YES")
                    time.sleep(SHEETS_RATE_LIMIT_SLEEP)

                    notifications_sent += 1

            # Check TP2
            if pos['tp2'] and not pos['tp2_hit']:
                tp2_hit = False
                if pos['signal'] == "BUY" and current_price >= pos['tp2']:
                    tp2_hit = True
                elif pos['signal'] == "SELL" and current_price <= pos['tp2']:
                    tp2_hit = True

                if tp2_hit:
                    pips, pct = calculate_profit_pips(pos['entry'], current_price, pos['signal'], pos['market'])
                    logger.info(f"  🎯 TP2 VURULDU! Kâr: {pips:+.1f} pips ({pct:+.2f}%)")

                    # Send notification
                    send_tp_notification(bot, telegram_chat_id, pos['market'], pos['signal'],
                                        "TP2", pos['entry'], pos['tp2'], current_price, pips, pct)

                    # Update sheet - mark position as closed
                    ws.update_cell(pos['row_index'], cols.BD, "YES")
                    ws.update_cell(pos['row_index'], cols.BF, "CLOSED")
                    time.sleep(SHEETS_RATE_LIMIT_SLEEP)

                    notifications_sent += 1

            # Check SL
            if pos['sl'] and not pos['sl_hit']:
                sl_hit = False
                if pos['signal'] == "BUY" and current_price <= pos['sl']:
                    sl_hit = True
                elif pos['signal'] == "SELL" and current_price >= pos['sl']:
                    sl_hit = True

                if sl_hit:
                    pips, pct = calculate_profit_pips(pos['entry'], current_price, pos['signal'], pos['market'])
                    logger.info(f"  🚨 SL VURULDU! Zarar: {abs(pips):.1f} pips ({abs(pct):.2f}%)")

                    # Send notification
                    send_sl_notification(bot, telegram_chat_id, pos['market'], pos['signal'],
                                        pos['entry'], pos['sl'], current_price, pips, pct)

                    # Update sheet - mark position as closed
                    ws.update_cell(pos['row_index'], cols.BE, "YES")
                    ws.update_cell(pos['row_index'], cols.BF, "CLOSED")
                    time.sleep(SHEETS_RATE_LIMIT_SLEEP)

                    notifications_sent += 1

            monitored += 1
            logger.info("")

        # Update Robot 9 status (BG column)
        ws.update_cell(2, cols.BG, status_text(9, True))

        logger.info("=" * 80)
        logger.info(f"✅ ROBOT 9 TAMAMLANDI")
        logger.info(f"  İzlenen pozisyon: {monitored}/{len(open_positions)}")
        logger.info(f"  Gönderilen bildirim: {notifications_sent}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ ROBOT 9 BAŞARISIZ: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()
