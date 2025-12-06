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
from utils.api_clients import BinanceClient, PolygonClient
from utils.supabase_client import get_pending_batches_for_robot, update_batch_analysis
from utils.monitoring import update_robot_status as update_monitoring

# Google Cloud Storage for chart uploads
try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None

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


def upload_chart_to_gcs(local_path: str, market: str) -> Optional[str]:
    """
    Upload chart to Google Cloud Storage and return public URL

    Args:
        local_path: Local file path of the chart
        market: Market symbol (used for naming)

    Returns:
        Public URL of the uploaded chart, or None if failed
    """
    if not GCS_AVAILABLE:
        logger.warning("Google Cloud Storage not available (install google-cloud-storage)")
        return None

    try:
        # Get bucket name from environment or use default
        bucket_name = os.getenv("GCS_BUCKET_NAME", "mytrade-charts")

        # Initialize GCS client
        client = storage.Client()

        # Get or create bucket
        try:
            bucket = client.get_bucket(bucket_name)
        except Exception:
            # Create bucket if not exists
            bucket = client.create_bucket(bucket_name, location="us-central1")
            logger.info(f"Created GCS bucket: {bucket_name}")

        # Generate blob name with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_market = market.replace("/", "_").replace(" ", "_")
        blob_name = f"charts/{safe_market}_{timestamp}.png"

        # Upload file
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)

        # Make public
        blob.make_public()

        public_url = blob.public_url
        logger.info(f"✓ Chart uploaded to GCS: {public_url}")

        return public_url

    except Exception as e:
        logger.error(f"Failed to upload chart to GCS: {e}")
        return None


def read_latest_signals(ws, cols) -> List[Dict]:
    """
    Read AI signals from Google Sheets - ROBUST (timing-independent)

    Uses get_rows_with_signals() to find ALL unprocessed rows with signals,
    not just the latest batch. This works even if Robot 1 timing is off.

    Returns list of signal dicts with market data and row indices
    """
    logger.info("Reading AI signals from Google Sheets (ROBUST mode)...")

    # ROBUST: Find ALL rows with signals that Robot 4 hasn't processed yet
    # BN column = Robot 4 status column
    ready_rows = get_rows_with_signals(ws, cols, cols.BN, "Robot 4")

    if not ready_rows:
        logger.warning("⚠️ İşlenecek sinyal yok (Robot 4 için)")
        return []

    # Parse signal data from ready rows
    signals = []
    for market_data in ready_rows:
        row = market_data["row_data"]
        row_index = market_data["row_index"]
        market = market_data["market"]
        final_signal = market_data["final_signal"]

        # NOTE: BK, AS, and BN checks are done in get_rows_with_signals()
        # No need to check again here!

        try:
            # Parse data (handle Turkish decimal format)
            price = parse_float(row[cols.C - 1]) if len(row) > cols.C - 1 else 0.0

            # Robot 7 Command Center output (AS-AX)
            final_confidence_str = row[cols.AT - 1] if len(row) > cols.AT - 1 else "0"
            final_confidence = int(float(final_confidence_str.replace('%', ''))) if final_confidence_str else 0

            final_reasoning = row[cols.AU - 1] if len(row) > cols.AU - 1 else ""
            risk_level = row[cols.AW - 1] if len(row) > cols.AW - 1 else "MEDIUM"
            suggested_action = row[cols.AX - 1] if len(row) > cols.AX - 1 else "SET ALERT"

            # Parse indicators (corrected columns, handle Turkish decimal format)
            indicators = {}
            if len(row) > cols.G - 1 and row[cols.G - 1]:  # RSI (G = 7)
                indicators['rsi'] = parse_float(row[cols.G - 1])
            if len(row) > cols.K - 1 and row[cols.K - 1]:  # BB Upper (K = 11)
                indicators['bb_upper'] = parse_float(row[cols.K - 1])
            if len(row) > cols.L - 1 and row[cols.L - 1]:  # BB Middle (L = 12)
                indicators['bb_middle'] = parse_float(row[cols.L - 1])
            if len(row) > cols.M - 1 and row[cols.M - 1]:  # BB Lower (M = 13)
                indicators['bb_lower'] = parse_float(row[cols.M - 1])
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

    Uses:
    - Binance for Crypto (BTC/USDT, etc.)
    - TwelveData for Forex, Commodities, Stocks (Grow Plan)

    Returns pandas DataFrame with OHLCV data
    """
    logger.info(f"Fetching {limit} candles for {market}...")

    try:
        # Determine market type and fetch data
        if "/" in market and "USDT" in market:
            # Crypto (e.g., BTC/USDT) - Use Binance
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

            logger.info(f"✓ Fetched {len(df)} candles for {market} (Binance)")
            return df

        else:
            # Forex, Commodities, Stocks - Use TwelveData (Grow Plan)
            from utils.api_clients import TwelveDataClient

            twelve = TwelveDataClient()

            # Determine category
            if "/" in market:
                if "XAU" in market or "XAG" in market:
                    category = "COMMODITY"
                elif "TRY" in market or "USD" in market or "EUR" in market or "GBP" in market or "JPY" in market or "CHF" in market or "AUD" in market:
                    category = "FOREX"
                else:
                    category = "FOREX"
            else:
                # Stocks (SPY, QQQ, NVDA, etc.)
                category = "STOCK_CFD"

            candles = twelve.get_time_series(market, interval="1h", outputsize=limit, category=category)

            if not candles:
                logger.warning(f"No candles returned for {market}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(candles)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)

            # Ensure numeric types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col])

            logger.info(f"✓ Fetched {len(df)} candles for {market} (TwelveData)")
            return df

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
    """Main execution function for Robot 4 - BATCH MODE"""
    logger.info("=" * 60)
    logger.info("🎨 ROBOT 4: CHART GENERATOR - BATCH MODE")
    logger.info("=" * 60)

    processed = 0
    total_markets = 0
    error_msg = ""

    try:
        # Ensure chart directory exists
        ensure_chart_dir()

        # Get pending BATCHES from Supabase (Robot 7 completed)
        pending_batches = get_pending_batches_for_robot(4)

        if not pending_batches:
            logger.info("⏳ Bekleyen batch yok (Robot 4)")
            try:
                gc = get_gspread_client()
                sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
                update_monitoring(gc, sheet_id, 4, True, 0, "Bekleyen batch yok")
            except:
                pass
            return

        logger.info(f"🎯 {len(pending_batches)} batch için grafik oluşturuluyor...")

        for batch_info in pending_batches:
            batch_id = batch_info["batch_id"]
            markets = batch_info["markets"]

            logger.info(f"\n{'='*60}")
            logger.info(f"📦 Batch: {batch_id} - {len(markets)} market")
            logger.info(f"{'='*60}")

            for market_info in markets:
                market = market_info["market"]
                signal_data = market_info["signal_data"]

                total_markets += 1

                # Check confidence threshold
                confidence = int(signal_data.get("final_confidence", 0) or 0)
                if confidence < MIN_CONFIDENCE:
                    logger.info(f"  ⏭️ {market}: Güven düşük ({confidence}% < {MIN_CONFIDENCE}%)")
                    # Still mark as processed but without chart
                    update_batch_analysis(batch_id, market, 4, {"chart_url": None})
                    continue

                # Build signal dict for chart
                signal = {
                    "market": market,
                    "price": float(signal_data["price"]) if signal_data.get("price") else 0,
                    "ensemble_signal": signal_data.get("final_signal", "HOLD"),
                    "ensemble_confidence": confidence,
                    "risk_level": signal_data.get("risk_level", "MEDIUM"),
                    "suggested_action": "SET ALERT",
                    "indicators": {
                        "rsi": signal_data.get("rsi"),
                        "bb_upper": signal_data.get("bb_upper"),
                        "bb_middle": signal_data.get("bb_middle"),
                        "bb_lower": signal_data.get("bb_lower"),
                        "support": signal_data.get("support_1"),
                        "resistance": signal_data.get("resistance_1"),
                    }
                }

                logger.info(f"\n📊 {market} ({signal['ensemble_signal']} {confidence}%)")

                try:
                    # Fetch candles
                    df = fetch_candles_for_chart(market, CHART_CANDLES)

                    if df is None or len(df) < 10:
                        logger.warning(f"  ⚠️ Yetersiz veri: {market}")
                        update_batch_analysis(batch_id, market, 4, {"chart_url": None})
                        continue

                    # Create chart
                    chart_path = create_chart(market, df, signal)

                    if chart_path:
                        # Upload to GCS
                        chart_url = upload_chart_to_gcs(chart_path, market)

                        # Update ALL 6 sequences for this market in this batch
                        update_data = {"chart_url": chart_url or chart_path}
                        success = update_batch_analysis(batch_id, market, 4, update_data)

                        if success:
                            processed += 1
                            logger.info(f"  ✅ Grafik oluşturuldu (6 satır güncellendi)")
                        else:
                            logger.error(f"  ❌ Supabase güncellenemedi")

                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"  ❌ Grafik hatası: {e}")
                    continue

        logger.info("\n" + "=" * 60)
        logger.info(f"✅ ROBOT 4 TAMAMLANDI")
        logger.info(f"   📦 Batch: {len(pending_batches)}")
        logger.info(f"   📊 Grafik: {processed}/{total_markets}")
        logger.info(f"   💾 Supabase: ✅")
        logger.info("=" * 60)

    except Exception as e:
        error_msg = str(e)[:50]
        logger.error(f"❌ ROBOT 4 BAŞARISIZ: {e}", exc_info=True)
        raise

    finally:
        # Update monitoring dashboard
        try:
            gc = get_gspread_client()
            sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
            update_monitoring(
                gc=gc,
                sheet_id=sheet_id,
                robot_number=4,
                success=processed > 0 or not error_msg,
                count=processed,
                detail=f"{processed} grafik" if processed else "İşlenecek veri yok",
                error=error_msg
            )
        except Exception as e:
            logger.warning(f"Monitoring update failed: {e}")


if __name__ == "__main__":
    run()