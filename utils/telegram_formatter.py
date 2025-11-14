# utils/telegram_formatter.py
# -*- coding: utf-8 -*-
"""
Telegram message formatting utilities
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("TelegramFormatter")


# ============================================================================
# YASAL SORUMLULUK UYARISI (Legal Disclaimer)
# ============================================================================

def get_disclaimer() -> str:
    """
    Yasal sorumluluk uyarısı - Her mesajda gösterilmeli

    Returns:
        HTML formatted disclaimer text
    """
    return (
        "\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <b>YASAL UYARI</b>\n\n"
        "Bu mesajlar <b>yalnızca bilgilendirme amaçlıdır</b> ve "
        "<b>yatırım tavsiyesi değildir</b>. "
        "Yapay zeka tarafından üretilen analizlerdir.\n\n"
        "• Yatırım kararlarınızı kendi araştırmanıza dayandırın\n"
        "• Geçmiş performans gelecek getiriyi garanti etmez\n"
        "• Yatırımlarınız değer kaybedebilir\n"
        "• Kaybetmeyi göze alamayacağınız parayı yatırmayın\n"
        "• Mutlaka Stop Loss kullanın\n\n"
        "<i>🤖 AI Models: GPT-4, Claude Opus 4, Gemini 2.5 Pro</i>"
    )


def get_performance_badge(win_rate: float = 0.0, total_signals: int = 0, period: str = "30 gün") -> str:
    """
    Performans göstergesi - Şeffaflık için

    Args:
        win_rate: Kazanma oranı (0-100)
        total_signals: Toplam sinyal sayısı
        period: Periyod açıklaması (örn: "30 gün", "7 gün")

    Returns:
        HTML formatted performance badge
    """
    if total_signals == 0:
        return "\n\n📊 <i>Performans verileri henüz yeterli değil.</i>"

    # Emoji seçimi
    if win_rate >= 70:
        emoji = "🟢"
        status = "Mükemmel"
    elif win_rate >= 60:
        emoji = "🟢"
        status = "İyi"
    elif win_rate >= 50:
        emoji = "🟡"
        status = "Orta"
    else:
        emoji = "🔴"
        status = "Zayıf"

    return (
        "\n\n"
        f"📊 <b>Geçmiş Performans ({period})</b>:\n"
        f"{emoji} Win Rate: <b>{win_rate:.1f}%</b> ({status})\n"
        f"📍 Toplam Sinyal: {total_signals}\n"
        f"<i>⚠️ Geçmiş performans gelecek getiriyi garanti etmez.</i>"
    )


# ============================================================================
# MESAJ FORMATLAMA FONKSİYONLARI
# ============================================================================

def format_trading_signal(
    market: str,
    signal: str,
    confidence: int,
    reasoning: str,
    price: float,
    indicators: Dict = None
) -> str:
    """
    Format trading signal for Telegram

    Args:
        market: Market symbol
        signal: Trading signal (BUY/SELL/HOLD)
        confidence: Confidence percentage
        reasoning: AI reasoning
        price: Current price
        indicators: Optional technical indicators

    Returns:
        Formatted message string
    """
    # Signal emoji
    signal_emoji = {
        "BUY": "🚀",
        "SELL": "🔻",
        "HOLD": "⏸"
    }.get(signal.upper(), "❓")

    # Build message
    message = f"{signal_emoji} <b>{market}</b>\n"
    message += f"Signal: <b>{signal}</b>\n"
    message += f"Price: ${price:,.2f}\n"
    message += f"Confidence: <b>{confidence}%</b>\n"

    # Add indicators if available
    if indicators:
        if "rsi" in indicators:
            rsi = indicators["rsi"]
            rsi_status = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
            message += f"RSI: {rsi:.1f} ({rsi_status})\n"

        if "trend" in indicators:
            trend_emoji = "📈" if "up" in indicators["trend"].lower() else "📉" if "down" in indicators["trend"].lower() else "➡️"
            message += f"Trend: {trend_emoji} {indicators['trend']}\n"

    # Add reasoning
    message += f"\n💡 {reasoning[:200]}"
    if len(reasoning) > 200:
        message += "..."

    # Add legal disclaimer (ZORUNLU - Yasal koruma için)
    message += get_disclaimer()

    return message

def format_performance_report(metrics: Dict) -> str:
    """
    Format performance metrics for Telegram

    Args:
        metrics: Performance metrics dict

    Returns:
        Formatted report string
    """
    message = "📊 <b>Performance Report</b>\n"
    message += "━━━━━━━━━━━━━━━━━\n\n"

    # Win rate
    win_rate = metrics.get("win_rate", 0)
    win_emoji = "✅" if win_rate >= 60 else "⚠️" if win_rate >= 40 else "❌"
    message += f"{win_emoji} Win Rate: <b>{win_rate:.1f}%</b>\n"

    # P&L
    if "avg_profit_percent" in metrics:
        message += f"📈 Avg Profit: {metrics['avg_profit_percent']:.2f}%\n"
    if "avg_loss_percent" in metrics:
        message += f"📉 Avg Loss: {metrics['avg_loss_percent']:.2f}%\n"

    # Signals
    if "total_signals" in metrics:
        message += f"\n📍 Total Signals: {metrics['total_signals']}\n"
        message += f"✅ Successful: {metrics.get('successful_signals', 0)}\n"
        message += f"❌ Failed: {metrics.get('failed_signals', 0)}\n"
        message += f"⏳ Pending: {metrics.get('pending_signals', 0)}\n"

    # Add disclaimer for transparency
    message += get_disclaimer()

    return message

def format_error_notification(robot_name: str, error: str, attempt: int = 1, max_retries: int = 3) -> str:
    """
    Format error notification for Telegram

    Args:
        robot_name: Name of the robot that failed
        error: Error message
        attempt: Current attempt number
        max_retries: Maximum retry attempts

    Returns:
        Formatted error message
    """
    message = f"🚨 <b>Error Alert</b>\n\n"
    message += f"Robot: {robot_name}\n"
    message += f"Attempt: {attempt}/{max_retries + 1}\n"
    message += f"Error: {error[:200]}\n"

    if attempt <= max_retries:
        message += f"\n⏳ Retrying..."
    else:
        message += f"\n❌ Max retries exceeded"

    return message