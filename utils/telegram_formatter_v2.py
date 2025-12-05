# utils/telegram_formatter_v2.py
# -*- coding: utf-8 -*-
"""
Clean Telegram Message Formatter V2
Simplified, professional trading signal format
"""

import datetime
import pytz
from typing import Dict, List, Optional


def format_signal(signal: Dict) -> str:
    """
    Format a single trading signal - CLEAN VERSION

    Args:
        signal: Signal dict with market, entry, tp, sl, etc.

    Returns:
        Clean formatted message
    """
    turkey_tz = pytz.timezone('Europe/Istanbul')
    timestamp = datetime.datetime.now(turkey_tz).strftime("%H:%M")

    # Signal direction
    direction = signal.get('ensemble_signal', 'HOLD').upper()
    if direction == "BUY":
        emoji = "🚀"
        direction_tr = "ALIŞ"
    elif direction == "SELL":
        emoji = "🔻"
        direction_tr = "SATIŞ"
    else:
        emoji = "⏸"
        direction_tr = "BEKLE"

    # Market name
    market = signal.get('market', 'UNKNOWN')

    # Build message
    msg = f"{emoji} <b>{market} - {direction_tr}</b>\n\n"

    # Entry/TP/SL
    entry = signal.get('entry_price')
    tp1 = signal.get('take_profit_1')
    tp2 = signal.get('take_profit_2')
    sl = signal.get('stop_loss')
    rr = signal.get('risk_reward')

    if entry:
        msg += f"💰 <b>Giriş:</b> ${entry:,.2f}\n"

    if tp1 or tp2:
        tp_parts = []
        if tp1:
            tp_parts.append(f"${tp1:,.2f}")
        if tp2:
            tp_parts.append(f"${tp2:,.2f}")
        msg += f"🎯 <b>Hedef:</b> {' → '.join(tp_parts)}\n"

    if sl:
        msg += f"🛑 <b>Stop:</b> ${sl:,.2f}\n"

    if rr:
        msg += f"⚖️ <b>R/R:</b> 1:{rr:.1f}\n"

    msg += "\n"

    # Confidence & Risk (compact)
    confidence = signal.get('ensemble_confidence', 0)
    risk = signal.get('risk_level', 'MEDIUM')

    risk_emoji = "🟢" if risk == "LOW" else "🟡" if risk == "MEDIUM" else "🔴"
    risk_tr = "Düşük" if risk == "LOW" else "Orta" if risk == "MEDIUM" else "Yüksek"

    msg += f"📊 Güven: %{confidence} | Risk: {risk_emoji} {risk_tr}\n"
    msg += f"⏰ {timestamp} TR"

    return msg


def format_signal_batch(signals: List[Dict]) -> str:
    """
    Format multiple signals as a summary

    Args:
        signals: List of signal dicts

    Returns:
        Summary message
    """
    turkey_tz = pytz.timezone('Europe/Istanbul')
    timestamp = datetime.datetime.now(turkey_tz).strftime("%d.%m.%Y %H:%M")

    buy_count = sum(1 for s in signals if s.get('ensemble_signal', '').upper() == 'BUY')
    sell_count = sum(1 for s in signals if s.get('ensemble_signal', '').upper() == 'SELL')

    msg = f"📊 <b>SİNYAL ÖZETİ</b>\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"🚀 Alış: {buy_count} | 🔻 Satış: {sell_count}\n"
    msg += f"📍 Toplam: {len(signals)} sinyal\n"
    msg += f"⏰ {timestamp}\n"
    msg += f"━━━━━━━━━━━━━━━━"

    return msg


def format_tp_hit(market: str, tp_level: str, entry: float, exit_price: float, profit_pct: float) -> str:
    """
    Format TP hit notification

    Args:
        market: Market symbol
        tp_level: "TP1" or "TP2"
        entry: Entry price
        exit_price: Exit price
        profit_pct: Profit percentage

    Returns:
        Formatted message
    """
    emoji = "✅" if profit_pct > 0 else "⚠️"

    msg = f"{emoji} <b>{market} - {tp_level} ULAŞILDI!</b>\n\n"
    msg += f"💵 Giriş: ${entry:,.2f}\n"
    msg += f"💰 Çıkış: ${exit_price:,.2f}\n"
    msg += f"📈 Kar: <b>+{profit_pct:.2f}%</b>"

    return msg


def format_sl_hit(market: str, entry: float, exit_price: float, loss_pct: float) -> str:
    """
    Format SL hit notification

    Args:
        market: Market symbol
        entry: Entry price
        exit_price: Exit price
        loss_pct: Loss percentage (positive number)

    Returns:
        Formatted message
    """
    msg = f"🛑 <b>{market} - STOP LOSS!</b>\n\n"
    msg += f"💵 Giriş: ${entry:,.2f}\n"
    msg += f"💰 Çıkış: ${exit_price:,.2f}\n"
    msg += f"📉 Zarar: <b>-{abs(loss_pct):.2f}%</b>"

    return msg


def format_daily_summary(
    total_signals: int,
    wins: int,
    losses: int,
    total_profit_pct: float
) -> str:
    """
    Format daily performance summary

    Args:
        total_signals: Total signals today
        wins: Winning trades
        losses: Losing trades
        total_profit_pct: Total profit/loss percentage

    Returns:
        Formatted message
    """
    turkey_tz = pytz.timezone('Europe/Istanbul')
    date_str = datetime.datetime.now(turkey_tz).strftime("%d.%m.%Y")

    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

    profit_emoji = "📈" if total_profit_pct > 0 else "📉" if total_profit_pct < 0 else "➡️"

    msg = f"📊 <b>GÜNLÜK ÖZET</b>\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"📅 {date_str}\n\n"
    msg += f"📍 Toplam Sinyal: {total_signals}\n"
    msg += f"✅ Kazanan: {wins}\n"
    msg += f"❌ Kaybeden: {losses}\n"
    msg += f"📊 Başarı: %{win_rate:.1f}\n\n"
    msg += f"{profit_emoji} <b>Günlük P/L: {total_profit_pct:+.2f}%</b>\n"
    msg += f"━━━━━━━━━━━━━━━━"

    return msg


def format_system_alert(robot_name: str, status: str, message: str = None) -> str:
    """
    Format system alert for ADMIN only

    Args:
        robot_name: Robot identifier
        status: "STARTED", "COMPLETED", "ERROR"
        message: Optional details

    Returns:
        Formatted message
    """
    turkey_tz = pytz.timezone('Europe/Istanbul')
    timestamp = datetime.datetime.now(turkey_tz).strftime("%H:%M:%S")

    status_emoji = {
        "STARTED": "🚀",
        "COMPLETED": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️"
    }.get(status, "ℹ️")

    msg = f"{status_emoji} <b>{robot_name}</b>\n"
    msg += f"Durum: {status}\n"

    if message:
        msg += f"Detay: {message}\n"

    msg += f"⏰ {timestamp}"

    return msg


def format_no_signals() -> str:
    """Format message when no signals are available"""
    turkey_tz = pytz.timezone('Europe/Istanbul')
    timestamp = datetime.datetime.now(turkey_tz).strftime("%H:%M")

    return f"ℹ️ <b>Aktif Sinyal Yok</b>\n\n" \
           f"Şu an güvenilir sinyal bulunamadı.\n" \
           f"Piyasa takipte...\n\n" \
           f"⏰ {timestamp} TR"
