# robots/weekly_telegram_report.py
# -*- coding: utf-8 -*-
"""
Robot 6 Enhancement: Weekly Telegram Performance Report
Reads closed positions from Google Sheets and sends weekly summary to Telegram
"""

import os
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from urllib.parse import quote

from config.constants import DEFAULT_SHEET_TAB
from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.common import parse_float, status_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-6-WeeklyReport")

SHEET_TAB = os.getenv("SHEET_TAB", DEFAULT_SHEET_TAB)


def parse_signal_from_cell(cell_value: str) -> Optional[str]:
    """
    Parse signal from cell value (format: "BUY" or "SELL" or "BUY (confidence)")

    Args:
        cell_value: Cell value from AG column

    Returns:
        Signal type (BUY/SELL/HOLD) or None
    """
    if not cell_value:
        return None

    cell_value = cell_value.upper()

    if "BUY" in cell_value:
        return "BUY"
    elif "SELL" in cell_value:
        return "SELL"
    elif "HOLD" in cell_value:
        return "HOLD"

    return None


def parse_price_from_cell(cell_value: str) -> Optional[float]:
    """
    Parse price from cell value (format: "$95,000.00")

    Args:
        cell_value: Cell value with price

    Returns:
        Price as float or None
    """
    if not cell_value:
        return None

    try:
        # Remove $ and commas
        clean = cell_value.replace("$", "").replace(",", "")
        return parse_float(clean)
    except:
        return None


def calculate_pips_or_percent(entry: float, exit_price: float, signal: str, market: str) -> tuple:
    """
    Calculate profit in pips (forex) or percentage (crypto)

    Returns:
        (pips_or_pct, is_forex) tuple
    """
    if "/" in market:  # Crypto
        pct = ((exit_price - entry) / entry) * 100 if signal == "BUY" else ((entry - exit_price) / entry) * 100
        return pct, False
    else:  # Forex
        if "JPY" in market.upper():
            pips = abs(exit_price - entry) * 100
        else:
            pips = abs(exit_price - entry) * 10000

        if signal == "BUY":
            pips = pips if exit_price > entry else -pips
        else:  # SELL
            pips = pips if entry > exit_price else -pips

        return pips, True


def collect_weekly_trades(ws, cols, days: int = 7) -> List[Dict]:
    """
    Collect closed trades from last N days

    Args:
        ws: Google Sheets worksheet
        cols: Column mapping
        days: Number of days to look back

    Returns:
        List of trade dictionaries
    """
    logger.info(f"📊 Collecting trades from last {days} days...")

    all_rows = ws.get_all_values()

    if len(all_rows) < 2:
        logger.warning("  ⚠️  No data found")
        return []

    # Skip header
    data_rows = all_rows[1:]

    # Calculate date threshold
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)

    trades = []

    for i, row in enumerate(data_rows, start=2):
        row_index = i

        # Skip if row is too short
        if len(row) <= max(cols.AS, cols.AY, cols.BH) - 1:
            continue

        # Get timestamp (A column)
        timestamp_str = row[cols.A - 1] if len(row) > cols.A - 1 else ""

        if not timestamp_str or "📊" in timestamp_str:
            continue  # Skip separator rows

        # Parse timestamp
        try:
            # Format: "2025-01-15 10:30:00" or similar
            row_date = datetime.strptime(timestamp_str[:19], "%Y-%m-%d %H:%M:%S")

            # Skip if older than threshold
            if row_date < date_threshold:
                continue
        except:
            # If can't parse, include it anyway
            pass

        # Get position status (BH column)
        position_status = row[cols.BH - 1] if len(row) > cols.BH - 1 else ""

        # Only include closed positions
        if position_status != "CLOSED":
            continue

        # Get market and signal
        market = row[cols.B - 1] if len(row) > cols.B - 1 else ""
        final_signal_str = row[cols.AS - 1] if len(row) > cols.AS - 1 else ""
        final_signal = parse_signal_from_cell(final_signal_str)

        if not market or not final_signal or final_signal == "HOLD":
            continue

        # Get prices (Risk columns: AY-BB)
        entry_str = row[cols.AY - 1] if len(row) > cols.AY - 1 else ""
        tp1_str = row[cols.BA - 1] if len(row) > cols.BA - 1 else ""
        tp2_str = row[cols.BB - 1] if len(row) > cols.BB - 1 else ""
        sl_str = row[cols.AZ - 1] if len(row) > cols.AZ - 1 else ""

        entry_price = parse_price_from_cell(entry_str)

        if not entry_price:
            continue

        # Get hit status (TP/SL tracking columns: BE-BG)
        tp1_hit = row[cols.BE - 1] if len(row) > cols.BE - 1 else ""
        tp2_hit = row[cols.BF - 1] if len(row) > cols.BF - 1 else ""
        sl_hit = row[cols.BG - 1] if len(row) > cols.BG - 1 else ""

        # Determine outcome
        outcome = None
        exit_price = None

        if sl_hit == "YES":
            outcome = "SL"
            exit_price = parse_price_from_cell(sl_str)
        elif tp2_hit == "YES":
            outcome = "TP2"
            exit_price = parse_price_from_cell(tp2_str)
        elif tp1_hit == "YES":
            outcome = "TP1"
            exit_price = parse_price_from_cell(tp1_str)

        if not outcome or not exit_price:
            continue

        # Calculate profit
        pips_or_pct, is_forex = calculate_pips_or_percent(entry_price, exit_price, final_signal, market)

        trades.append({
            "row_index": row_index,
            "timestamp": timestamp_str,
            "market": market,
            "signal": final_signal,
            "entry": entry_price,
            "exit": exit_price,
            "outcome": outcome,
            "profit": pips_or_pct,
            "is_forex": is_forex
        })

    logger.info(f"  ✅ Found {len(trades)} closed trades")
    return trades


def calculate_weekly_stats(trades: List[Dict]) -> Dict:
    """
    Calculate weekly performance statistics

    Args:
        trades: List of trade dictionaries

    Returns:
        Statistics dictionary
    """
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_pips": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "profit_factor": 0.0,
            "trades_by_market": {}
        }

    total_trades = len(trades)

    # Separate wins and losses
    wins = [t for t in trades if t["profit"] > 0]
    losses = [t for t in trades if t["profit"] <= 0]

    winning_trades = len(wins)
    losing_trades = len(losses)

    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    # Calculate profit metrics
    total_profit = sum(t["profit"] for t in wins)
    total_loss = abs(sum(t["profit"] for t in losses))

    avg_win = (total_profit / winning_trades) if winning_trades > 0 else 0.0
    avg_loss = (total_loss / losing_trades) if losing_trades > 0 else 0.0

    best_trade = max(t["profit"] for t in trades) if trades else 0.0
    worst_trade = min(t["profit"] for t in trades) if trades else 0.0

    profit_factor = (total_profit / total_loss) if total_loss > 0 else 0.0

    # Total pips/percentage (net)
    total_pips = sum(t["profit"] for t in trades)

    # Group by market
    trades_by_market = {}
    for trade in trades:
        market = trade["market"]
        if market not in trades_by_market:
            trades_by_market[market] = {"count": 0, "profit": 0.0, "wins": 0}

        trades_by_market[market]["count"] += 1
        trades_by_market[market]["profit"] += trade["profit"]
        if trade["profit"] > 0:
            trades_by_market[market]["wins"] += 1

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "total_pips": total_pips,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "profit_factor": profit_factor,
        "trades_by_market": trades_by_market
    }


def send_weekly_report(token: str, chat_id: str, stats: Dict, trades: List[Dict]):
    """
    Send weekly performance report to Telegram

    Format matches the user's reference:
    📊 VIP Kanal Raporu (Cuma 30):
    - XAUUSD: +160 pips ✅
    - GBPUSD: +50 pips ✅
    ...
    """
    try:
        # Get current week info
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=7)

        message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>📊 HAFTALIK PERFORMANS RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📅 Tarih Aralığı:</b>
{week_start.strftime("%d.%m.%Y")} - {now.strftime("%d.%m.%Y")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>📈 GENEL İSTATİSTİKLER</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Toplam Sinyal:</b> {stats['total_trades']} pozisyon
<b>Kazanan:</b> {stats['winning_trades']} ✅
<b>Kaybeden:</b> {stats['losing_trades']} ❌

<b>💰 Başarı Oranı:</b> {stats['win_rate']:.1f}%
<b>📊 Net Kazanç:</b> {stats['total_pips']:+.1f} pips
<b>⚡ Profit Factor:</b> {stats['profit_factor']:.2f}

<b>Ortalama Kazanç:</b> +{stats['avg_win']:.1f} pips
<b>Ortalama Kayıp:</b> -{stats['avg_loss']:.1f} pips

<b>En İyi İşlem:</b> {stats['best_trade']:+.1f} pips 🎯
<b>En Kötü İşlem:</b> {stats['worst_trade']:+.1f} pips 🚨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>📊 PİYASA BAZINDA DETAYLAR</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # Add market breakdown
        for market, data in sorted(stats['trades_by_market'].items(), key=lambda x: x[1]['profit'], reverse=True):
            emoji = "✅" if data['profit'] > 0 else "❌"
            win_rate = (data['wins'] / data['count'] * 100) if data['count'] > 0 else 0

            message += f"\n<b>{market}</b>: {data['profit']:+.1f} pips {emoji}"
            message += f"\n  └─ {data['count']} sinyal • %{win_rate:.0f} başarı\n"

        message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>🎯 SON 5 İŞLEM</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # Add last 5 trades
        recent_trades = sorted(trades, key=lambda x: x['timestamp'], reverse=True)[:5]

        for trade in recent_trades:
            emoji = "✅" if trade['profit'] > 0 else "❌"
            position = "LONG" if trade['signal'] == "BUY" else "SHORT"

            message += f"\n<b>{trade['market']}</b> ({position}) - {trade['outcome']}"
            message += f"\n  {trade['profit']:+.1f} pips {emoji}\n"

        message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>💡 Bu hafta toplam <b>{stats['total_trades']}</b> pozisyon kapatıldı.</i>
<i>🎯 Başarı oranımız: <b>%{stats['win_rate']:.1f}</b></i>

<b>Bir sonraki rapora kadar başarılar! 🚀</b>
"""

        # Send via Telegram HTTP API
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message.strip(),
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        logger.info(f"  ✅ Haftalık rapor Telegram'a gönderildi")

    except Exception as e:
        logger.error(f"  ❌ Telegram rapor gönderilemedi: {e}")
        raise


def run():
    """Main execution function for weekly Telegram report"""
    logger.info("=" * 80)
    logger.info("📊 ROBOT 6: WEEKLY TELEGRAM REPORT - BAŞLAT")
    logger.info("=" * 80)

    try:
        # Initialize services
        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
        telegram_token = get_secret("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = get_secret("TELEGRAM_CHAT_ID")

        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        # Collect weekly trades (last 7 days)
        trades = collect_weekly_trades(ws, cols, days=7)

        if not trades:
            logger.warning("⚠️  Son 7 günde kapalı işlem yok")

            # Send empty report
            message = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>📊 HAFTALIK PERFORMANS RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>Son 7 günde kapalı pozisyon yok.</i>

<b>Yeni fırsatları bekliyoruz! 🎯</b>
"""
            # Send via Telegram HTTP API
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            payload = {
                "chat_id": telegram_chat_id,
                "text": message.strip(),
                "parse_mode": "HTML"
            }
            requests.post(url, json=payload, timeout=30).raise_for_status()

            # Update Robot 6 status (BP sütunu)
            ws.update_cell(2, cols.BP, status_text(6, True))
            return

        # Calculate statistics
        stats = calculate_weekly_stats(trades)

        logger.info(f"\n📊 HAFTALIK İSTATİSTİKLER:")
        logger.info(f"  Toplam İşlem: {stats['total_trades']}")
        logger.info(f"  Kazanan: {stats['winning_trades']} ✅")
        logger.info(f"  Kaybeden: {stats['losing_trades']} ❌")
        logger.info(f"  Başarı Oranı: {stats['win_rate']:.1f}%")
        logger.info(f"  Net Kazanç: {stats['total_pips']:+.1f} pips")
        logger.info(f"  Profit Factor: {stats['profit_factor']:.2f}")

        # Send Telegram report
        send_weekly_report(telegram_token, telegram_chat_id, stats, trades)

        # Update Robot 6 status (BP sütunu)
        ws.update_cell(2, cols.BP, status_text(6, True))

        logger.info("=" * 80)
        logger.info(f"✅ ROBOT 6 TAMAMLANDI")
        logger.info(f"  Rapor gönderildi: {stats['total_trades']} işlem")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ ROBOT 6 BAŞARISIZ: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()
