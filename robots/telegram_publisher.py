# robots/telegram_publisher.py
# -*- coding: utf-8 -*-
"""
Robot 5: Telegram Publisher
Publishes AI trading signals to Telegram channel
"""

import os
import time
import datetime
import pytz
import logging
from typing import Dict, List, Optional
from pathlib import Path
from telegram import Bot
from telegram.constants import ParseMode

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-5-TelegramPublisher")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", "65"))
MAX_SIGNALS = int(os.getenv("MAX_SIGNALS", "5"))
CHART_DIR = os.getenv("CHART_DIR", "/tmp/charts")
SEND_CHARTS = os.getenv("SEND_CHARTS", "true").lower() == "true"


def status_text(robot_no: int, ok: bool) -> str:
    """Generate status text for robot"""
    return f"Robot {robot_no} {'✅' if ok else '❌'}"


def get_signal_emoji(signal: str) -> str:
    """Get emoji for trading signal"""
    emoji_map = {
        "BUY": "🚀",
        "SELL": "🔻",
        "HOLD": "⏸"
    }
    return emoji_map.get(signal.upper(), "❓")


def get_trend_emoji(trend: str) -> str:
    """Get emoji for trend"""
    if not trend:
        return "➡️"
    trend_lower = trend.lower()
    if "up" in trend_lower or "bull" in trend_lower:
        return "📈"
    elif "down" in trend_lower or "bear" in trend_lower:
        return "📉"
    else:
        return "➡️"


def read_latest_signals(ws, cols) -> List[Dict]:
    """
    Read latest AI signals from Google Sheets

    Returns list of signal dicts with market data
    """
    logger.info("Reading latest AI signals from Google Sheets...")

    all_rows = ws.get_all_values()

    if len(all_rows) <= 1:
        logger.warning("No data in sheet")
        return []

    separator_idx = None
    for i in range(len(all_rows) - 1, 0, -1):
        if len(all_rows[i]) > cols.AH - 1:
            if all_rows[i][cols.AH - 1] == "Separator":
                separator_idx = i
                break

    if separator_idx is None:
        logger.warning("No separator found")
        data_rows = all_rows[1:]
    else:
        data_rows = all_rows[separator_idx + 1:]

    logger.info(f"Found {len(data_rows)} rows in latest batch")

    signals = []
    for row in data_rows:
        if len(row) < cols.B:
            continue

        market = row[cols.B - 1] if len(row) > cols.B - 1 else ""
        if not market or market == "":
            continue

        ensemble_signal = row[cols.Y - 1] if len(row) > cols.Y - 1 else ""
        if not ensemble_signal or ensemble_signal == "":
            continue

        try:
            price = float(row[cols.C - 1]) if len(row) > cols.C - 1 and row[cols.C - 1] else 0
            change_pct = float(row[cols.D - 1]) if len(row) > cols.D - 1 and row[cols.D - 1] else 0

            ensemble_confidence = int(float(row[cols.Z - 1])) if len(row) > cols.Z - 1 and row[cols.Z - 1] else 0
            ensemble_reasoning = row[cols.AA - 1] if len(row) > cols.AA - 1 else ""

            gpt4_signal = row[cols.V - 1] if len(row) > cols.V - 1 else ""
            claude_signal = row[cols.W - 1] if len(row) > cols.W - 1 else ""
            gemini_signal = row[cols.X - 1] if len(row) > cols.X - 1 else ""

            rsi = row[cols.F - 1] if len(row) > cols.F - 1 else ""
            trend = row[cols.S - 1] if len(row) > cols.S - 1 else ""

            signals.append({
                "market": market,
                "price": price,
                "change_pct": change_pct,
                "ensemble_signal": ensemble_signal.upper(),
                "ensemble_confidence": ensemble_confidence,
                "ensemble_reasoning": ensemble_reasoning,
                "gpt4_signal": gpt4_signal,
                "claude_signal": claude_signal,
                "gemini_signal": gemini_signal,
                "rsi": rsi,
                "trend": trend
            })

        except Exception as e:
            logger.warning(f"Error parsing signal for {market}: {e}")
            continue

    logger.info(f"✓ Parsed {len(signals)} signals")
    return signals


def filter_signals(signals: List[Dict], min_confidence: int) -> List[Dict]:
    """
    Filter signals by confidence and prioritize actionable signals

    Args:
        signals: List of signal dicts
        min_confidence: Minimum confidence threshold

    Returns:
        Filtered and sorted list
    """
    filtered = [s for s in signals if s['ensemble_confidence'] >= min_confidence]

    priority_order = {"BUY": 0, "SELL": 1, "HOLD": 2}

    sorted_signals = sorted(
        filtered,
        key=lambda x: (
            priority_order.get(x['ensemble_signal'], 99),
            -x['ensemble_confidence']
        )
    )

    logger.info(f"Filtered {len(filtered)}/{len(signals)} signals (min confidence: {min_confidence}%)")
    return sorted_signals


def format_signal_message(signals: List[Dict], max_count: int = 5) -> str:
    """
    Format trading signals into Telegram message

    Args:
        signals: List of filtered signals
        max_count: Maximum number of signals to include

    Returns:
        Formatted message string
    """
    turkey_tz = pytz.timezone('Europe/Istanbul')
    timestamp = datetime.datetime.now(turkey_tz).strftime("%d.%m.%Y %H:%M")

    message = f"📊 <b>MyTrade AI Signals</b>\n"
    message += f"🕐 {timestamp} (Turkey)\n"
    message += f"━━━━━━━━━━━━━━━━━\n\n"

    buy_count = sum(1 for s in signals if s['ensemble_signal'] == 'BUY')
    sell_count = sum(1 for s in signals if s['ensemble_signal'] == 'SELL')
    hold_count = sum(1 for s in signals if s['ensemble_signal'] == 'HOLD')

    message += f"<b>Summary:</b>\n"
    message += f"🚀 BUY: {buy_count}  |  🔻 SELL: {sell_count}  |  ⏸ HOLD: {hold_count}\n\n"

    if not signals:
        message += "⚠️ No signals above confidence threshold.\n"
        return message

    message += f"<b>Top {min(max_count, len(signals))} Signals:</b>\n\n"

    for i, signal in enumerate(signals[:max_count], 1):
        emoji = get_signal_emoji(signal['ensemble_signal'])
        trend_emoji = get_trend_emoji(signal['trend'])

        message += f"{i}. <b>{signal['market']}</b>\n"
        message += f"   {emoji} <b>{signal['ensemble_signal']}</b> @ ${signal['price']:,.2f}\n"
        message += f"   💪 Confidence: <b>{signal['ensemble_confidence']}%</b>\n"

        if signal['rsi']:
            try:
                rsi_val = float(signal['rsi'])
                rsi_status = "Oversold" if rsi_val < 30 else "Overbought" if rsi_val > 70 else "Neutral"
                message += f"   📊 RSI: {rsi_val:.1f} ({rsi_status})\n"
            except:
                pass

        if signal['trend']:
            message += f"   {trend_emoji} Trend: {signal['trend']}\n"

        ai_votes = []
        if signal['gpt4_signal']:
            ai_votes.append(f"GPT-4: {signal['gpt4_signal']}")
        if signal['claude_signal']:
            ai_votes.append(f"Claude: {signal['claude_signal']}")
        if signal['gemini_signal']:
            ai_votes.append(f"Gemini: {signal['gemini_signal']}")

        if ai_votes:
            message += f"   🤖 AI: {' | '.join(ai_votes)}\n"

        if signal['ensemble_reasoning']:
            reasoning = signal['ensemble_reasoning'][:150]
            if len(signal['ensemble_reasoning']) > 150:
                reasoning += "..."
            message += f"   💡 {reasoning}\n"

        message += "\n"

    message += "━━━━━━━━━━━━━━━━━\n"
    message += "⚠️ <i>Not financial advice. DYOR.</i>\n"
    message += "🤖 <i>Powered by GPT-4, Claude & Gemini</i>"

    return message


def find_chart_for_market(market: str) -> Optional[str]:
    """
    Find chart file for a given market

    Args:
        market: Market symbol (e.g., "BTC/USDT")

    Returns:
        Path to chart file or None
    """
    safe_market = market.replace("/", "_")
    chart_path = os.path.join(CHART_DIR, f"{safe_market}_chart.png")

    if os.path.exists(chart_path):
        return chart_path
    else:
        return None


def send_to_telegram(bot_token: str, chat_id: str, message: str, signals: List[Dict] = None) -> bool:
    """
    Send message and charts to Telegram

    Args:
        bot_token: Telegram bot token
        chat_id: Chat ID or channel username
        message: Message to send
        signals: Optional list of signals (for charts)

    Returns:
        Success boolean
    """
    try:
        bot = Bot(token=bot_token)

        bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

        logger.info(f"✓ Message sent to Telegram chat: {chat_id}")

        if SEND_CHARTS and signals:
            charts_sent = 0
            for signal in signals[:MAX_SIGNALS]:
                chart_path = find_chart_for_market(signal['market'])

                if chart_path:
                    try:
                        with open(chart_path, 'rb') as chart_file:
                            caption = f"{signal['market']} - {signal['ensemble_signal']} ({signal['ensemble_confidence']}%)"
                            bot.send_photo(
                                chat_id=chat_id,
                                photo=chart_file,
                                caption=caption
                            )
                            charts_sent += 1
                            logger.info(f"✓ Chart sent for {signal['market']}")
                            time.sleep(1)
                    except Exception as e:
                        logger.warning(f"Failed to send chart for {signal['market']}: {e}")
                        continue

            if charts_sent > 0:
                logger.info(f"✓ Sent {charts_sent} charts to Telegram")

        return True

    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def run():
    """Main execution function for Robot 5"""
    logger.info("=" * 60)
    logger.info("ROBOT 5: TELEGRAM PUBLISHER - STARTING")
    logger.info("=" * 60)

    try:
        sheet_id = get_secret("GOOGLE_SHEET_ID")
        bot_token = get_secret("TELEGRAM_BOT_TOKEN")
        chat_id = get_secret("TELEGRAM_CHAT_ID")

        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        logger.info(f"Connected to Google Sheet: {SHEET_TAB}")

        signals = read_latest_signals(ws, cols)

        if not signals:
            logger.warning("⚠ No AI signals found in sheet")
            return

        filtered_signals = filter_signals(signals, MIN_CONFIDENCE)

        if not filtered_signals:
            logger.warning(f"⚠ No signals above {MIN_CONFIDENCE}% confidence")
            message = format_signal_message([], MAX_SIGNALS)
        else:
            message = format_signal_message(filtered_signals, MAX_SIGNALS)

        logger.info(f"Sending message to Telegram ({len(filtered_signals)} signals)...")
        success = send_to_telegram(bot_token, chat_id, message, filtered_signals if filtered_signals else None)

        if success:
            logger.info("✓ ROBOT 5 COMPLETED SUCCESSFULLY")
        else:
            logger.error("❌ Failed to send Telegram message")

    except Exception as e:
        logger.error(f"❌ ROBOT 5 FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()