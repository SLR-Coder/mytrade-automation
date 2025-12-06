# robots/telegram_publisher.py
# -*- coding: utf-8 -*-
"""
Robot 5: Telegram Publisher
Publishes AI trading signals to Telegram channel
Supabase'den okur, Telegram'a gönderir
"""

import os
import time
import datetime
import pytz
import logging
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from telegram import Bot
from telegram.constants import ParseMode

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.supabase_client import get_signals_to_publish, update_robot_status
from utils.monitoring import update_robot_status as update_monitoring
from utils.telegram_formatter import get_performance_badge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-5-TelegramPublisher")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", "65"))
MAX_SIGNALS = int(os.getenv("MAX_SIGNALS", "5"))
CHART_DIR = os.getenv("CHART_DIR", "/tmp/charts")
SEND_CHARTS = os.getenv("SEND_CHARTS", "true").lower() == "true"


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


# parse_float removed - now imported from utils.common


def calculate_recent_performance(ws, cols, days: int = 30) -> Dict:
    """
    Calculate performance metrics from recent closed trades

    Args:
        ws: Google Sheets worksheet
        cols: Column mapping
        days: Number of days to look back (default: 30)

    Returns:
        Dictionary with win_rate and total_signals
    """
    try:
        all_rows = ws.get_all_values()

        if len(all_rows) < 2:
            return {"win_rate": 0.0, "total_signals": 0}

        # Skip header
        data_rows = all_rows[1:]

        # Calculate date threshold
        date_threshold = datetime.datetime.now(pytz.timezone('UTC')) - datetime.timedelta(days=days)

        closed_trades = []

        for row in data_rows:
            # Skip if row is too short
            if len(row) <= max(cols.AS, cols.BH) - 1:
                continue

            # Get timestamp (A column)
            timestamp_str = row[cols.A - 1] if len(row) > cols.A - 1 else ""

            if not timestamp_str or "📊" in timestamp_str:
                continue  # Skip separator rows

            # Parse timestamp
            try:
                row_date = datetime.datetime.strptime(timestamp_str[:19], "%Y-%m-%d %H:%M:%S")
                row_date = row_date.replace(tzinfo=pytz.timezone('UTC'))

                # Skip if older than threshold
                if row_date < date_threshold:
                    continue
            except:
                continue

            # Get position status (BH column)
            position_status = row[cols.BH - 1] if len(row) > cols.BH - 1 else ""

            # Only include closed positions
            if position_status != "CLOSED":
                continue

            # Get signal
            final_signal_str = row[cols.AS - 1] if len(row) > cols.AS - 1 else ""

            if not final_signal_str or "HOLD" in final_signal_str.upper():
                continue

            # Get hit status (TP1, TP2, SL) - columns BE-BG
            tp1_hit = row[cols.BE - 1] if len(row) > cols.BE - 1 else ""
            tp2_hit = row[cols.BF - 1] if len(row) > cols.BF - 1 else ""
            sl_hit = row[cols.BG - 1] if len(row) > cols.BG - 1 else ""

            # Determine if winning trade (TP hit) or losing trade (SL hit)
            is_winner = (tp1_hit == "YES" or tp2_hit == "YES")

            closed_trades.append({
                "is_winner": is_winner
            })

        # Calculate win rate
        total_signals = len(closed_trades)
        winning_signals = sum(1 for t in closed_trades if t["is_winner"])

        win_rate = (winning_signals / total_signals * 100) if total_signals > 0 else 0.0

        logger.info(f"✓ Performance: {win_rate:.1f}% win rate ({winning_signals}/{total_signals} signals in last {days} days)")

        return {
            "win_rate": win_rate,
            "total_signals": total_signals
        }

    except Exception as e:
        logger.warning(f"Failed to calculate performance: {e}")
        return {"win_rate": 0.0, "total_signals": 0}


def read_latest_signals(ws, cols) -> List[Dict]:
    """
    Read AI signals from Google Sheets - ROBUST (timing-independent)

    Uses get_rows_with_signals() to find ALL unprocessed rows with signals,
    not just the latest batch. This works even if Robot 1 timing is off.

    Also checks BO column to avoid republishing signals!

    Returns list of signal dicts with market data and row indices
    """
    logger.info("Reading AI signals from Google Sheets (ROBUST mode)...")

    # ROBUST: Find ALL rows with signals that Robot 5 hasn't published yet
    # BO column = Robot 5 status column
    ready_rows = get_rows_with_signals(ws, cols, cols.BO, "Robot 5")

    if not ready_rows:
        logger.warning("⚠️ Yayınlanacak sinyal yok (Robot 5 için)")
        return []

    # Parse signal data from ready rows
    signals = []
    for market_data in ready_rows:
        row = market_data["row_data"]
        row_index = market_data["row_index"]
        market = market_data["market"]
        final_signal = market_data["final_signal"]

        # NOTE: BK, AS, and BO checks are done in get_rows_with_signals()
        # No need to check again here!

        try:
            price = parse_float(row[cols.C - 1]) if len(row) > cols.C - 1 else 0.0
            change_pct = parse_float(row[cols.E - 1]) if len(row) > cols.E - 1 else 0.0

            # Robot 7 Command Center output (AS-AX)
            final_confidence_str = row[cols.AT - 1] if len(row) > cols.AT - 1 else "0"
            final_confidence = int(float(final_confidence_str.replace('%', ''))) if final_confidence_str else 0

            final_reasoning = row[cols.AU - 1] if len(row) > cols.AU - 1 else ""
            consensus_str = row[cols.AV - 1] if len(row) > cols.AV - 1 else "0"
            consensus = int(float(consensus_str.replace('%', ''))) if consensus_str else 0
            risk_level = row[cols.AW - 1] if len(row) > cols.AW - 1 else "MEDIUM"
            suggested_action = row[cols.AX - 1] if len(row) > cols.AX - 1 else "SET ALERT"

            # Robot 3 AI signals (columns: AI-AR)
            gpt4_signal = row[cols.AI - 1] if len(row) > cols.AI - 1 else ""
            claude_signal = row[cols.AK - 1] if len(row) > cols.AK - 1 else ""
            gemini_signal = row[cols.AM - 1] if len(row) > cols.AM - 1 else ""
            grok_signal = row[cols.AO - 1] if len(row) > cols.AO - 1 else ""
            deepseek_signal = row[cols.AQ - 1] if len(row) > cols.AQ - 1 else ""

            # Robot 8 Personal AI signal (AG column)
            personal_signal = row[cols.AG - 1] if len(row) > cols.AG - 1 else ""

            # Indicators (corrected columns)
            rsi = row[cols.G - 1] if len(row) > cols.G - 1 else ""
            trend = row[cols.T - 1] if len(row) > cols.T - 1 else ""

            # Entry/TP/SL from Risk columns (AY-BC)
            entry_str = row[cols.AY - 1] if len(row) > cols.AY - 1 else ""
            sl_str = row[cols.AZ - 1] if len(row) > cols.AZ - 1 else ""
            tp1_str = row[cols.BA - 1] if len(row) > cols.BA - 1 else ""
            tp2_str = row[cols.BB - 1] if len(row) > cols.BB - 1 else ""
            rr_str = row[cols.BC - 1] if len(row) > cols.BC - 1 else ""

            # Parse Entry/TP/SL (format: "$95,000.00")
            def extract_price(price_str):
                if not price_str:
                    return None
                try:
                    # Remove $ and commas, then parse
                    clean = price_str.replace("$", "").replace(",", "")
                    return float(clean)
                except:
                    return None

            entry_price = extract_price(entry_str)
            stop_loss = extract_price(sl_str)
            take_profit_1 = extract_price(tp1_str)
            take_profit_2 = extract_price(tp2_str)

            try:
                risk_reward = float(rr_str) if rr_str else None
            except:
                risk_reward = None

            # Get chart URL from BT column (GCS URL from Robot 4)
            chart_url = row[cols.BT - 1] if len(row) > cols.BT - 1 else ""

            signals.append({
                "row_index": row_index,
                "market": market,
                "price": price,
                "change_pct": change_pct,
                "ensemble_signal": final_signal.upper(),
                "ensemble_confidence": final_confidence,
                "ensemble_reasoning": final_reasoning,
                "consensus": consensus,
                "risk_level": risk_level,
                "suggested_action": suggested_action,
                "personal_signal": personal_signal,
                "gpt4_signal": gpt4_signal,
                "claude_signal": claude_signal,
                "gemini_signal": gemini_signal,
                "grok_signal": grok_signal,
                "deepseek_signal": deepseek_signal,
                "rsi": rsi,
                "trend": trend,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit_1": take_profit_1,
                "take_profit_2": take_profit_2,
                "risk_reward": risk_reward,
                "chart_url": chart_url
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


def format_overview_message(signals: List[Dict]) -> str:
    """
    Format overview message for Telegram

    Args:
        signals: List of filtered signals

    Returns:
        Overview message string
    """
    turkey_tz = pytz.timezone('Europe/Istanbul')
    timestamp = datetime.datetime.now(turkey_tz).strftime("%d.%m.%Y %H:%M")

    buy_count = sum(1 for s in signals if s['ensemble_signal'] == 'BUY')
    sell_count = sum(1 for s in signals if s['ensemble_signal'] == 'SELL')
    hold_count = sum(1 for s in signals if s['ensemble_signal'] == 'HOLD')

    message = f"🎯 <b>KURUMSAL TİCARET SİNYALLERİ</b>\n"
    message += f"📍 MyTrade Araştırma Masası\n"
    message += f"🕐 {timestamp} (İstanbul)\n"
    message += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
    message += f"<b>📈 PİYASA GÖRÜNÜMÜ</b>\n"
    message += f"Alış Eğilimi: {buy_count} | Satış Eğilimi: {sell_count} | Nötr: {hold_count}\n"
    message += f"Takip Edilen Varlıklar: {len(signals)}\n\n"
    message += f"<i>⬇️ Her sinyal detayları ile aşağıda paylaşılmaktadır...</i>"

    return message


# analyze_temporal_trend removed - now imported from utils.common


def format_single_signal(signal: Dict, index: int, temporal_trend: Dict = None, performance_data: Dict = None) -> str:
    """
    Format single signal message for Telegram

    Args:
        signal: Signal dict
        index: Signal number (1-indexed)
        temporal_trend: Optional temporal trend data
        performance_data: Optional performance metrics (win_rate, total_signals)

    Returns:
        Formatted message string
    """
    emoji = get_signal_emoji(signal['ensemble_signal'])
    trend_emoji = get_trend_emoji(signal['trend'])

    # Risk classification
    risk_level = signal.get('risk_level', 'MEDIUM')
    risk_emoji = "🟢" if risk_level == "LOW" else "🟡" if risk_level == "MEDIUM" else "🔴"

    # Recommendation mapping (Turkish)
    action = signal.get('suggested_action', 'SET ALERT')
    if action == "ENTER NOW":
        action_text = "AKTİF POZİSYON"
    elif action == "WAIT FOR PULLBACK":
        action_text = "GİRİŞ BEKLE"
    elif action == "SET ALERT":
        action_text = "TAKİP ET"
    else:  # AVOID
        action_text = "POZİSYON ALMA"

    # Signal direction (Turkish with English in parentheses)
    direction = signal['ensemble_signal']
    if direction == "BUY":
        position_text = "ALIŞ (LONG)"
    elif direction == "SELL":
        position_text = "SATIŞ (SHORT)"
    else:
        position_text = "NÖTR (NEUTRAL)"

    # Risk level Turkish mapping
    risk_tr = "DÜŞÜK (LOW)" if risk_level == "LOW" else "ORTA (MEDIUM)" if risk_level == "MEDIUM" else "YÜKSEK (HIGH)"

    message = f"━━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"{emoji} <b>#{index} • {signal['market']} - {position_text}</b>\n"
    message += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # Entry/TP/SL Section (Hybrid Format - Compact but Clear)
    if signal.get('entry_price'):
        message += f"<b>🛒 GİRİŞ:</b> ${signal['entry_price']:,.2f}\n"

        # Targets (TP1 and TP2)
        if signal.get('take_profit_1') or signal.get('take_profit_2'):
            message += f"<b>🎯 HEDEFLER:</b>\n"
            if signal.get('take_profit_1'):
                message += f"   TP1: ${signal['take_profit_1']:,.2f}\n"
            if signal.get('take_profit_2'):
                message += f"   TP2: ${signal['take_profit_2']:,.2f}\n"

        # Stop Loss
        if signal.get('stop_loss'):
            message += f"<b>🚨 STOP LOSS:</b> ${signal['stop_loss']:,.2f}\n"

        # Risk/Reward
        if signal.get('risk_reward'):
            message += f"<b>⚖️ Risk/Reward:</b> 1:{signal['risk_reward']:.2f}\n"

        message += "\n"
    else:
        # Fallback: Show current price
        message += f"<b>💵 Fiyat:</b> ${signal['price']:,.2f}"

        # Change percentage if available
        if signal.get('change_pct'):
            change = signal['change_pct']
            change_emoji = "📈" if change > 0 else "📉"
            message += f" ({change_emoji}{change:+.2f}%)"
        message += "\n\n"

    # Analysis Section (Compact Hybrid Format)
    message += f"<b>📊 ANALİZ:</b>\n"

    conviction = signal['ensemble_confidence']
    consensus = signal.get('consensus', conviction)

    message += f"├─ İnanç: %{conviction}\n"
    message += f"├─ Fikir Birliği: %{consensus}\n"
    message += f"├─ Risk: {risk_emoji} {risk_tr.split('(')[0].strip()}\n"
    message += f"└─ Öneri: {action_text}\n"

    # Temporal trend analysis (30 minutes)
    if temporal_trend and temporal_trend.get('available'):
        message += f"\n<b>📊 SON 30 DAKİKA TRENDİ:</b>\n"

        # Price change with color coding
        price_change = temporal_trend['price_change_pct']
        if price_change > 0:
            price_emoji = "📈"
            price_text = f"<b>+%{price_change:.2f}</b>"
        elif price_change < 0:
            price_emoji = "📉"
            price_text = f"<b>%{price_change:.2f}</b>"
        else:
            price_emoji = "➡️"
            price_text = "%0.00"

        message += f"├─ Fiyat Değişimi: {price_emoji} {price_text}\n"
        message += f"├─ Momentum: {temporal_trend['momentum']}\n"
        message += f"└─ Tutarlılık: {temporal_trend['consistency']} batch yukarı hareket\n"

    # Technical indicators (Compact Single Line)
    tech_indicators = []
    if signal['rsi']:
        try:
            rsi_val = float(signal['rsi'])
            if rsi_val < 30:
                rsi_emoji_val = "🔵"
            elif rsi_val > 70:
                rsi_emoji_val = "🔴"
            else:
                rsi_emoji_val = "⚪"
            tech_indicators.append(f"RSI: {rsi_emoji_val}{rsi_val:.1f}")
        except:
            pass

    if signal['trend']:
        tech_indicators.append(f"Trend: {trend_emoji}{signal['trend']}")

    if tech_indicators:
        message += f"\n<b>💡 Teknik:</b> {' | '.join(tech_indicators)}\n"

    # Professional analysis summary (Compact - Optional)
    if signal['ensemble_reasoning']:
        reasoning = signal['ensemble_reasoning']
        # Make it look more professional - remove AI mentions
        reasoning = reasoning.replace('AI', 'analist')
        reasoning = reasoning.replace('Personal AI', 'Baş analist')
        reasoning = reasoning.replace('GPT-4', 'Kantitatif ekip')
        reasoning = reasoning.replace('Claude', 'Temel analiz ekibi')
        reasoning = reasoning.replace('Gemini', 'Teknik ekip')
        reasoning = reasoning.replace('Grok', 'Momentum ekibi')
        reasoning = reasoning.replace('DeepSeek', 'Risk ekibi')

        if len(reasoning) > 200:
            reasoning = reasoning[:200] + "..."

        message += f"\n<b>📋 Özet:</b> <i>{reasoning}</i>"

    # Add performance badge (transparency feature)
    if performance_data and performance_data.get('total_signals', 0) > 0:
        performance_badge = get_performance_badge(
            win_rate=performance_data['win_rate'],
            total_signals=performance_data['total_signals'],
            period="30 gün"
        )
        message += performance_badge

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


async def send_message_with_retry(bot: Bot, chat_id: str, text: str, max_retries: int = 3, **kwargs) -> bool:
    """Send message with retry logic for transient errors"""
    for attempt in range(max_retries):
        try:
            await bot.send_message(chat_id=chat_id, text=text, **kwargs)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)  # Exponential backoff: 2, 4, 8 seconds
                logger.warning(f"Telegram error (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Failed after {max_retries} attempts: {e}")
                return False
    return False


async def send_signals_individually_async(bot_token: str, chat_id: str, signals: List[Dict], temporal_data: Dict = None, performance_data: Dict = None) -> bool:
    """
    Send overview + individual signal messages with charts

    Args:
        bot_token: Telegram bot token
        chat_id: Chat ID or channel username
        signals: List of signals to send
        temporal_data: Optional temporal trend data for each market
        performance_data: Optional performance metrics (win_rate, total_signals)

    Returns:
        Success boolean
    """
    try:
        bot = Bot(token=bot_token)

        # Send overview message
        overview = format_overview_message(signals)
        success = await send_message_with_retry(
            bot, chat_id, overview,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        if success:
            logger.info(f"✓ Overview message sent to Telegram")
        else:
            logger.error(f"❌ Failed to send overview message")
            return False

        await asyncio.sleep(2)

        # Send each signal + chart individually
        charts_sent = 0
        messages_sent = 0
        for i, signal in enumerate(signals[:MAX_SIGNALS], 1):
            # Calculate temporal trend for this market
            temporal_trend = None
            if temporal_data and signal['market'] in temporal_data:
                temporal_trend = analyze_temporal_trend(temporal_data[signal['market']])

            # Send signal message (with performance badge) - with retry
            message = format_single_signal(signal, i, temporal_trend, performance_data)
            success = await send_message_with_retry(
                bot, chat_id, message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            if success:
                messages_sent += 1
                logger.info(f"✓ Signal #{i} sent: {signal['market']}")
            else:
                logger.warning(f"⚠ Failed to send signal #{i}: {signal['market']}")

            await asyncio.sleep(1.5)  # Slightly longer delay between messages

            # Send chart if available (prefer GCS URL, fallback to local file)
            if SEND_CHARTS:
                chart_url = signal.get('chart_url', '')
                chart_path = find_chart_for_market(signal['market']) if not chart_url else None

                if chart_url or chart_path:
                    try:
                        for attempt in range(3):
                            try:
                                caption = f"📊 {signal['market']} Teknik Analiz"

                                if chart_url:
                                    # Send GCS URL directly (preferred)
                                    await bot.send_photo(
                                        chat_id=chat_id,
                                        photo=chart_url,
                                        caption=caption
                                    )
                                    charts_sent += 1
                                    logger.info(f"✓ Chart sent for {signal['market']} (GCS URL)")
                                else:
                                    # Fallback to local file
                                    with open(chart_path, 'rb') as chart_file:
                                        await bot.send_photo(
                                            chat_id=chat_id,
                                            photo=chart_file,
                                            caption=caption
                                        )
                                        charts_sent += 1
                                        logger.info(f"✓ Chart sent for {signal['market']} (local file)")
                                break
                            except Exception as e:
                                if attempt < 2:
                                    await asyncio.sleep(2 ** (attempt + 1))
                                else:
                                    logger.warning(f"Failed to send chart for {signal['market']}: {e}")
                        await asyncio.sleep(1.5)
                    except Exception as e:
                        logger.warning(f"Failed to send chart for {signal['market']}: {e}")

        logger.info(f"✓ Sent {messages_sent} signal messages and {charts_sent} charts")
        return messages_sent > 0  # Success if at least one message was sent

    except Exception as e:
        logger.error(f"Failed to send Telegram messages: {e}")
        return False


def send_signals_individually(bot_token: str, chat_id: str, signals: List[Dict], temporal_data: Dict = None, performance_data: Dict = None) -> bool:
    """
    Send signals individually to Telegram (sync wrapper)

    Args:
        bot_token: Telegram bot token
        chat_id: Chat ID or channel username
        signals: List of signals to send
        temporal_data: Optional temporal trend data
        performance_data: Optional performance metrics (win_rate, total_signals)

    Returns:
        Success boolean
    """
    return asyncio.run(send_signals_individually_async(bot_token, chat_id, signals, temporal_data, performance_data))


def run():
    """Main execution function for Robot 5"""
    logger.info("=" * 80)
    logger.info("📢 ROBOT 5: TELEGRAM PUBLISHER - BAŞLAT")
    logger.info("=" * 80)

    processed = 0
    error_msg = ""

    try:
        bot_token = get_secret("TELEGRAM_BOT_TOKEN")
        chat_id = get_secret("TELEGRAM_CHAT_ID")

        # Get signals ready to publish from Supabase
        pending_signals = get_signals_to_publish()

        if not pending_signals:
            logger.warning("⚠️ Yayınlanacak sinyal yok (Robot 5 için)")
            try:
                gc = get_gspread_client()
                sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
                update_monitoring(gc, sheet_id, 5, True, 0, "İşlenecek veri yok")
            except:
                pass
            return

        logger.info(f"🎯 {len(pending_signals)} sinyal Telegram'a gönderilecek...")

        # Convert Supabase rows to signal format for Telegram
        signals = []
        for signal_data in pending_signals:
            signal = {
                "id": signal_data["id"],
                "market": signal_data["market"],
                "price": float(signal_data["price"]) if signal_data.get("price") else 0,
                "change_pct": float(signal_data.get("change_24h", 0) or 0),
                "ensemble_signal": signal_data.get("final_signal", "HOLD"),
                "ensemble_confidence": int(signal_data.get("final_confidence", 0) or 0),
                "ensemble_reasoning": signal_data.get("final_analysis", ""),
                "risk_level": signal_data.get("risk_level", "MEDIUM"),
                "suggested_action": "SET ALERT",
                "rsi": signal_data.get("rsi"),
                "trend": signal_data.get("trend"),
                "entry_price": float(signal_data["price"]) if signal_data.get("price") else None,
                "stop_loss": float(signal_data.get("sl")) if signal_data.get("sl") else None,
                "take_profit_1": float(signal_data.get("tp1")) if signal_data.get("tp1") else None,
                "take_profit_2": float(signal_data.get("tp2")) if signal_data.get("tp2") else None,
                "risk_reward": None,
                "chart_url": signal_data.get("chart_url", ""),
                # AI signals for display
                "personal_signal": signal_data.get("personal_signal", ""),
                "gpt4_signal": signal_data.get("gpt4_signal", ""),
                "claude_signal": signal_data.get("claude_signal", ""),
                "gemini_signal": "",
                "grok_signal": signal_data.get("grok_signal", ""),
                "deepseek_signal": signal_data.get("deepseek_signal", ""),
            }
            signals.append(signal)

        # Filter by confidence
        filtered_signals = filter_signals(signals, MIN_CONFIDENCE)

        # Filter to signals with charts if SEND_CHARTS is enabled
        if SEND_CHARTS and filtered_signals:
            signals_with_charts = []
            for signal in filtered_signals:
                chart_url = signal.get('chart_url', '')
                chart_path = find_chart_for_market(signal['market']) if not chart_url else None
                if chart_url or chart_path:
                    signals_with_charts.append(signal)

            if signals_with_charts:
                logger.info(f"✅ {len(signals_with_charts)}/{len(filtered_signals)} sinyal grafik ile")
                filtered_signals = signals_with_charts
            else:
                logger.warning("⚠️ Grafikli sinyal yok, tümü gönderilecek")

        if not filtered_signals:
            logger.warning(f"⚠️ {MIN_CONFIDENCE}% üzeri güven yok")
            try:
                gc = get_gspread_client()
                sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
                update_monitoring(gc, sheet_id, 5, True, 0, f"Güven < {MIN_CONFIDENCE}%")
            except:
                pass
            return

        logger.info(f"📤 {len(filtered_signals)} sinyal Telegram'a gönderiliyor...")

        # Send to Telegram
        success = send_signals_individually(bot_token, chat_id, filtered_signals, None, None)

        if success:
            # Update Supabase status for published signals
            for signal in filtered_signals:
                signal_id = signal["id"]
                update_data = {"telegram_message_id": f"sent_{int(time.time())}"}
                if update_robot_status(signal_id, 5, update_data):
                    processed += 1
                    logger.info(f"  ✅ {signal['market']} yayınlandı")
                else:
                    logger.error(f"  ❌ {signal['market']} güncellenemedi")

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ ROBOT 5 TAMAMLANDI")
        logger.info(f"   📤 Yayınlanan: {processed}/{len(filtered_signals)}")
        logger.info(f"   💾 Supabase: ✅")
        logger.info("=" * 80)

    except Exception as e:
        error_msg = str(e)[:50]
        logger.error(f"❌ ROBOT 5 BAŞARISIZ: {e}", exc_info=True)
        raise

    finally:
        # Update monitoring dashboard
        try:
            gc = get_gspread_client()
            sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
            update_monitoring(
                gc=gc,
                sheet_id=sheet_id,
                robot_number=5,
                success=processed > 0 or not error_msg,
                count=processed,
                detail=f"{processed} Telegram" if processed else "İşlenecek veri yok",
                error=error_msg
            )
        except Exception as e:
            logger.warning(f"Monitoring update failed: {e}")


if __name__ == "__main__":
    run()