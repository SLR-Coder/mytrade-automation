# -*- coding: utf-8 -*-
"""
Robot 4: Chart Generator
Creates technical analysis charts for markets
"""

import os
import time
import logging
from typing import Dict, List, Optional
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from pathlib import Path

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.common import status_text, parse_float, is_ready_for_analysis  # DRY: Import from common
from utils.api_clients import BinanceClient, PolygonClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-4-ChartGenerator")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")
CHART_DIR = os.getenv("CHART_DIR", "/tmp/charts")
CHART_CANDLES = int(os.getenv("CHART_CANDLES", "100"))  # Number of candles to plot
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", "65"))  # Only chart high-confidence signals


def ensure_chart_dir():
    """Ensure chart directory exists"""
    Path(CHART_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"Chart directory: {CHART_DIR}")


def read_latest_signals(ws, cols) -> List[Dict]:
    """
    Read latest AI signals from Google Sheets

    Returns list of signal dicts with market data and row indices
    """
    logger.info("Reading latest AI signals from Google Sheets...")

    # Get all rows
    all_rows = ws.get_all_values()

    if len(all_rows) <= 1:
        logger.warning("No data in sheet")
        return []

    # Son ayırıcıyı bul (Robot 1 separator with "📊 VERİ TOPLAMA RAPORU" in column B)
    separator_idx = None
    for i in range(len(all_rows) - 1, 0, -1):
        if len(all_rows[i]) > cols.B - 1:
            market_value = all_rows[i][cols.B - 1]
            if market_value and ("📊" in market_value or "RAPORU" in market_value):
                separator_idx = i
                break

    if separator_idx is None:
        logger.warning("Ayırıcı bulunamadı (separator not found)")
        data_rows = all_rows[1:]
        start_row = 2  # Row 1 is header, data starts at row 2
    else:
        data_rows = all_rows[separator_idx + 1:]
        start_row = separator_idx + 2  # +1 for separator, +1 for 1-indexed

    logger.info(f"Found {len(data_rows)} rows in latest batch (starting at row {start_row})")

    # Parse signal data
    signals = []
    for idx, row in enumerate(data_rows):
        row_index = start_row + idx
        if len(row) < cols.B:
            continue

        market = row[cols.B - 1] if len(row) > cols.B - 1 else ""
        if not market or market == "":
            continue

        # Batch status kontrolü - Robot 1 "✅ Analiz Hazır" yazmış mı? (AU sütunu)
        robot1_status = row[cols.AU - 1] if len(row) > cols.AU - 1 else ""
        if not is_ready_for_analysis(robot1_status):
            continue  # Henüz hazır değil

        # Check if this row has Robot 7 Command Center decision (AG column)
        final_signal = row[cols.AG - 1] if len(row) > cols.AG - 1 else ""
        if not final_signal or final_signal == "":
            continue  # Skip rows without Robot 7 decision

        try:
            # Parse data (handle Turkish decimal format)
            price = parse_float(row[cols.C - 1]) if len(row) > cols.C - 1 else 0.0

            # Robot 7 Command Center output (AG-AL)
            final_confidence_str = row[cols.AH - 1] if len(row) > cols.AH - 1 else "0"
            final_confidence = int(float(final_confidence_str.replace('%', ''))) if final_confidence_str else 0

            final_reasoning = row[cols.AI - 1] if len(row) > cols.AI - 1 else ""
            risk_level = row[cols.AK - 1] if len(row) > cols.AK - 1 else "MEDIUM"
            suggested_action = row[cols.AL - 1] if len(row) > cols.AL - 1 else "SET ALERT"

            # Parse indicators (corrected columns, handle Turkish decimal format)
            indicators = {}
            if len(row) > cols.G - 1 and row[cols.G - 1]:  # RSI
                indicators['rsi'] = parse_float(row[cols.G - 1])
            if len(row) > cols.I - 1 and row[cols.I - 1]:  # Bollinger Upper
                indicators['bb_upper'] = parse_float(row[cols.I - 1])
            if len(row) > cols.J - 1 and row[cols.J - 1]:  # Bollinger Middle
                indicators['bb_middle'] = parse_float(row[cols.J - 1])
            if len(row) > cols.K - 1 and row[cols.K - 1]:  # Bollinger Lower
                indicators['bb_lower'] = parse_float(row[cols.K - 1])
            if len(row) > cols.R - 1 and row[cols.R - 1]:  # Support
                indicators['support'] = parse_float(row[cols.R - 1])
            if len(row) > cols.S - 1 and row[cols.S - 1]:  # Resistance
                indicators['resistance'] = parse_float(row[cols.S - 1])

            signals.append({
                "row_index": row_index,
                "market": market,
                "price": price,
                "ensemble_signal": final_signal.upper(),
                "ensemble_confidence": final_confidence,
                "reasoning": final_reasoning,
                "risk_level": risk_level,
                "suggested_action": suggested_action,
                "indicators": indicators
            })

        except Exception as e:
            logger.warning(f"Error parsing signal for {market}: {e}")
            continue

    logger.info(f"✓ Parsed {len(signals)} signals")
    return signals


def fetch_candles_for_chart(market: str, limit: int) -> Optional[pd.DataFrame]:
    """
    Fetch historical candles for chart generation

    Returns pandas DataFrame with OHLCV data
    """
    logger.info(f"Fetching {limit} candles for {market}...")

    try:
        # Determine market type
        if "/" in market and "USDT" in market:
            # Crypto (e.g., BTC/USDT)
            symbol = market.replace("/", "")  # BTC/USDT -> BTCUSDT
            binance = BinanceClient()
            candles = binance.get_klines(symbol, interval="1h", limit=limit)

            # Convert to DataFrame
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Ensure numeric types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])

            logger.info(f"✓ Fetched {len(df)} candles for {market}")
            return df

        elif "/" in market:
            # Forex (e.g., USD/TRY)
            parts = market.split("/")
            if len(parts) == 2:
                polygon_key = get_secret("POLYGON_API_KEY", required=False)
                if polygon_key:
                    polygon = PolygonClient(polygon_key)
                    candles = polygon.get_forex_candles(parts[0], parts[1], timespan="hour", limit=limit)

                    # Convert to DataFrame
                    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)

                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col])

                    logger.info(f"✓ Fetched {len(df)} candles for {market}")
                    return df

        else:
            # Commodity or other (skip for now)
            logger.warning(f"Unsupported market type: {market}")
            return None

    except Exception as e:
        logger.error(f"Failed to fetch candles for {market}: {e}")
        return None


def create_chart(market: str, df: pd.DataFrame, signal: Dict) -> Optional[str]:
    """
    Create technical analysis chart

    Args:
        market: Market symbol
        df: OHLCV DataFrame
        signal: Signal dict with indicators

    Returns:
        Path to saved chart file
    """
    logger.info(f"Creating chart for {market}...")

    try:
        # Prepare chart filename
        safe_market = market.replace("/", "_")
        chart_path = os.path.join(CHART_DIR, f"{safe_market}_chart.png")

        # Additional plots (indicators)
        apds = []

        # Bollinger Bands
        if all(k in signal['indicators'] for k in ['bb_upper', 'bb_middle', 'bb_lower']):
            bb_upper = [signal['indicators']['bb_upper']] * len(df)
            bb_middle = [signal['indicators']['bb_middle']] * len(df)
            bb_lower = [signal['indicators']['bb_lower']] * len(df)

            apds.append(mpf.make_addplot(bb_upper, color='red', linestyle='--', width=0.7))
            apds.append(mpf.make_addplot(bb_middle, color='blue', linestyle='--', width=0.7))
            apds.append(mpf.make_addplot(bb_lower, color='green', linestyle='--', width=0.7))

        # Support/Resistance lines
        if 'support' in signal['indicators']:
            support_line = [signal['indicators']['support']] * len(df)
            apds.append(mpf.make_addplot(support_line, color='green', linestyle=':', width=1.5))

        if 'resistance' in signal['indicators']:
            resistance_line = [signal['indicators']['resistance']] * len(df)
            apds.append(mpf.make_addplot(resistance_line, color='red', linestyle=':', width=1.5))

        # Chart style
        mc = mpf.make_marketcolors(
            up='green', down='red',
            edge='inherit',
            wick='inherit',
            volume='in'
        )
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=False)

        # Title with signal info (Robot 7 Command Center)
        signal_emoji = "🚀" if signal['ensemble_signal'] == "BUY" else "🔻" if signal['ensemble_signal'] == "SELL" else "⏸"
        risk_emoji = "🟢" if signal.get('risk_level') == "LOW" else "🟡" if signal.get('risk_level') == "MEDIUM" else "🔴"
        title = f"{market} - {signal_emoji} {signal['ensemble_signal']} ({signal['ensemble_confidence']}%) | {risk_emoji} {signal.get('risk_level', 'MEDIUM')} | {signal.get('suggested_action', 'SET ALERT')}"

        # Create chart
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=s,
            title=title,
            ylabel='Price',
            volume=True,
            addplot=apds if apds else None,
            figsize=(12, 8),
            returnfig=True,
            warn_too_much_data=500
        )

        # Save chart
        fig.savefig(chart_path, dpi=100, bbox_inches='tight')
        plt.close(fig)

        logger.info(f"✓ Chart saved: {chart_path}")
        return chart_path

    except Exception as e:
        logger.error(f"Failed to create chart for {market}: {e}")
        return None


def run():
    """Main execution function for Robot 4"""
    logger.info("=" * 60)
    logger.info("ROBOT 4: CHART GENERATOR - STARTING")
    logger.info("=" * 60)

    try:
        # Ensure chart directory exists
        ensure_chart_dir()

        # Get secrets
        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")

        # Get Google Sheets client
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        logger.info(f"Connected to Google Sheet: {SHEET_TAB}")

        # Read latest signals
        signals = read_latest_signals(ws, cols)

        if not signals:
            logger.warning("⚠ No AI signals found in sheet")
            return

        # Filter by confidence
        high_confidence_signals = [s for s in signals if s['ensemble_confidence'] >= MIN_CONFIDENCE]

        if not high_confidence_signals:
            logger.warning(f"⚠ No signals above {MIN_CONFIDENCE}% confidence")
            return

        logger.info(f"Creating charts for {len(high_confidence_signals)} high-confidence signals...")

        successful = 0
        failed = 0
        processed_rows = []  # Track successfully processed rows for status update

        for signal in high_confidence_signals:
            try:
                # Fetch candles
                df = fetch_candles_for_chart(signal['market'], CHART_CANDLES)

                if df is None or len(df) < 10:
                    logger.warning(f"Insufficient data for {signal['market']}")
                    failed += 1
                    continue

                # Create chart
                chart_path = create_chart(signal['market'], df, signal)

                if chart_path:
                    successful += 1
                    processed_rows.append(signal['row_index'])  # Track for status update
                else:
                    failed += 1

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to process {signal['market']}: {e}")
                failed += 1
                continue

        # Update Robot 4 status in Google Sheets (AX column)
        if processed_rows:
            logger.info("Updating Robot 4 status in Google Sheets...")
            updated = 0
            for row_idx in processed_rows:
                try:
                    ws.update_cell(row_idx, cols.AX, status_text(4, True))
                    updated += 1
                except Exception as e:
                    logger.warning(f"Failed to update status for row {row_idx}: {e}")
                    continue

            logger.info(f"✓ Updated {updated}/{len(processed_rows)} rows with Robot 4 ✅")

        # Summary
        logger.info("=" * 60)
        logger.info(f"✓ ROBOT 4 COMPLETED!")
        logger.info(f"  Charts created: {successful}/{len(high_confidence_signals)}")
        logger.info(f"  Failed: {failed}/{len(high_confidence_signals)}")
        logger.info(f"  Chart directory: {CHART_DIR}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ ROBOT 4 FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()