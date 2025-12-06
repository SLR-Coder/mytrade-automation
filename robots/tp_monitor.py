# robots/tp_monitor.py
# -*- coding: utf-8 -*-
"""
Robot 9: Real-Time TP/SL Monitor
Açık pozisyonları izler ve TP1/TP2/SL seviyelerine ulaşıldığında Telegram bildirimi gönderir.
Supabase'den okur ve günceller.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from telegram import Bot
from telegram.constants import ParseMode

from config.constants import CRYPTO_SYMBOLS
from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.supabase_client import (
    get_pending_batches_for_robot,
    update_batch_analysis,
    get_supabase,
    get_turkey_time
)
from utils.monitoring import update_robot_status as update_monitoring
from utils.api_clients import (
    BinanceClient,
    TwelveDataClient
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-9-TPMonitor")


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


def get_open_positions_from_supabase() -> List[Dict]:
    """Get open positions from Supabase for monitoring"""
    try:
        supabase = get_supabase()

        # Get signals with:
        # - robot5_status = completed (Telegram published)
        # - final_signal = BUY or SELL
        # - position_status is null or OPEN or TP1_HIT (still open)
        result = supabase.table("signals").select("*").eq(
            "robot5_status", "completed"
        ).eq(
            "batch_sequence", 6  # Only sequence 6 to avoid duplicates
        ).in_(
            "final_signal", ["BUY", "SELL"]
        ).execute()

        if not result.data:
            return []

        # Filter for open positions
        open_positions = []
        for row in result.data:
            position_status = row.get("position_status", "")

            # Skip closed positions
            if position_status in ["CLOSED", "TP2_HIT", "SL_HIT"]:
                continue

            # Need valid TP/SL values
            entry = row.get("entry_price") or row.get("price")
            sl = row.get("sl")
            tp1 = row.get("tp1")
            tp2 = row.get("tp2")

            if not entry or not sl:
                continue

            open_positions.append({
                "batch_id": row["batch_id"],
                "market": row["market"],
                "signal": row["final_signal"],
                "entry": float(entry),
                "sl": float(sl),
                "tp1": float(tp1) if tp1 else None,
                "tp2": float(tp2) if tp2 else None,
                "position_status": position_status or "OPEN",
            })

        return open_positions

    except Exception as e:
        logger.error(f"Error getting open positions: {e}")
        return []


def update_position_in_supabase(batch_id: str, market: str, update_data: Dict) -> bool:
    """Update position status in Supabase (all 6 sequences)"""
    try:
        supabase = get_supabase()

        update_data["robot9_last_check"] = get_turkey_time().isoformat()

        supabase.table("signals").update(update_data).eq(
            "batch_id", batch_id
        ).eq("market", market).execute()

        return True
    except Exception as e:
        logger.error(f"Error updating position: {e}")
        return False


def run():
    """Main execution function for Robot 9 - SUPABASE MODE"""
    logger.info("=" * 80)
    logger.info("🎯 ROBOT 9: TP/SL MONITOR - SUPABASE MODE")
    logger.info("=" * 80)

    monitored = 0
    notifications_sent = 0
    error_msg = ""

    try:
        # Initialize Telegram
        telegram_token = get_secret("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = get_secret("TELEGRAM_CHAT_ID")
        bot = Bot(token=telegram_token)

        # Get open positions from Supabase
        open_positions = get_open_positions_from_supabase()

        logger.info(f"\n📊 {len(open_positions)} açık pozisyon bulundu\n")

        if not open_positions:
            logger.info("  ℹ️  Takip edilecek açık pozisyon yok")
            try:
                gc = get_gspread_client()
                sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
                update_monitoring(gc, sheet_id, 9, True, 0, "Açık pozisyon yok")
            except:
                pass
            return

        # Monitor each position
        for pos in open_positions:
            logger.info(f"🔍 Kontrol: {pos['market']} ({pos['signal']})")
            logger.info(f"  Giriş: ${pos['entry']:,.2f} | SL: ${pos['sl']:,.2f} | TP1: ${pos['tp1']:,.2f if pos['tp1'] else 0} | TP2: ${pos['tp2']:,.2f if pos['tp2'] else 0}")

            # Fetch current price
            current_price = get_current_price(pos['market'])

            if not current_price:
                logger.warning(f"  ⚠️  Fiyat alınamadı, atlanıyor...")
                continue

            logger.info(f"  Şu anki fiyat: ${current_price:,.2f}")
            monitored += 1

            # Check TP1
            if pos['tp1'] and pos['position_status'] not in ["TP1_HIT", "TP2_HIT"]:
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

                    # Update Supabase - all 6 sequences
                    update_position_in_supabase(pos['batch_id'], pos['market'], {
                        "position_status": "TP1_HIT",
                        "tp1_hit_at": get_turkey_time().isoformat()
                    })

                    notifications_sent += 1

            # Check TP2
            if pos['tp2'] and pos['position_status'] != "TP2_HIT":
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

                    # Update Supabase - mark as closed
                    update_position_in_supabase(pos['batch_id'], pos['market'], {
                        "position_status": "CLOSED",
                        "tp2_hit_at": get_turkey_time().isoformat()
                    })

                    notifications_sent += 1

            # Check SL
            if pos['sl'] and pos['position_status'] not in ["CLOSED", "SL_HIT"]:
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

                    # Update Supabase - mark as closed
                    update_position_in_supabase(pos['batch_id'], pos['market'], {
                        "position_status": "CLOSED",
                        "sl_hit_at": get_turkey_time().isoformat()
                    })

                    notifications_sent += 1

            logger.info("")

        logger.info("=" * 80)
        logger.info(f"✅ ROBOT 9 TAMAMLANDI")
        logger.info(f"  İzlenen pozisyon: {monitored}/{len(open_positions)}")
        logger.info(f"  Gönderilen bildirim: {notifications_sent}")
        logger.info(f"  💾 Supabase: ✅")
        logger.info("=" * 80)

    except Exception as e:
        error_msg = str(e)[:50]
        logger.error(f"❌ ROBOT 9 BAŞARISIZ: {e}", exc_info=True)
        raise

    finally:
        # Update monitoring dashboard
        try:
            gc = get_gspread_client()
            sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
            update_monitoring(
                gc=gc,
                sheet_id=sheet_id,
                robot_number=9,
                success=monitored > 0 or not error_msg,
                count=monitored,
                detail=f"{monitored} pozisyon, {notifications_sent} bildirim",
                error=error_msg
            )
        except Exception as e:
            logger.warning(f"Monitoring update failed: {e}")


if __name__ == "__main__":
    run()
