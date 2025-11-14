# robots/market_harvester.py
# -*- coding: utf-8 -*-
"""
Robot 1: Market Harvester
Collects real-time market data from all sources and calculates technical indicators
"""

import os
import time
import datetime
import pytz
import logging
from typing import Dict, List, Optional

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.api_clients import BinanceClient, PolygonClient, AlphaVantageClient, GoldPriceClient
from utils.indicators import TechnicalIndicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-1-MarketHarvester")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")
CANDLE_LIMIT = int(os.getenv("CANDLE_LIMIT", "200"))  # For technical indicators

# ============================================================================
# MARKETS TO TRACK
# ============================================================================
# 🧪 TEST MODE: Only Crypto + Commodities (FREE APIs)
# 🚀 LIVE MODE: Add Forex (requires paid API)
# ============================================================================

# FOREX - DISABLED FOR TEST (Enable when LIVE)
# Requires: Polygon.io ($199/mo) OR Alpha Vantage ($49/mo)
FOREX_PAIRS = [
    # ("USD", "TRY"),  # 🇹🇷 Dolar/TL
    # ("EUR", "TRY"),  # 🇹🇷 Euro/TL
    # ("EUR", "USD"),  # 🇪🇺 Euro/Dolar
    # ("GBP", "USD"),  # 🇬🇧 Pound/Dolar
]

CRYPTO_PAIRS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
]

COMMODITIES = [
    "GOLD",  # XAU/USD
    "SILVER",  # XAG/USD
]


def status_text(robot_no: int, ok: bool) -> str:
    """Generate status text for robot"""
    return f"Robot {robot_no} {'✅' if ok else '❌'}"


def fetch_forex_data(
    polygon_client: Optional[PolygonClient],
    alphavantage_client: AlphaVantageClient,
    from_cur: str,
    to_cur: str
) -> Optional[Dict]:
    """
    Fetch forex data with fallback

    Priority: Polygon.io → Alpha Vantage
    """
    pair_name = f"{from_cur}/{to_cur}"
    logger.info(f"Fetching forex data: {pair_name}")

    # Try Polygon first (if API key available)
    if polygon_client:
        try:
            price_data = polygon_client.get_forex_price(from_cur, to_cur)
            candles = polygon_client.get_forex_candles(from_cur, to_cur, timespan="hour", limit=CANDLE_LIMIT)

            # Calculate indicators
            indicators = TechnicalIndicators.calculate_all(candles)

            return {
                "market": pair_name,
                "price": price_data["price"],
                "volume": 0,  # Forex doesn't have volume like stocks
                "change_percent": 0,  # Calculate from 24h if needed
                "indicators": indicators,
                "source": "Polygon.io"
            }
        except Exception as e:
            logger.warning(f"Polygon failed for {pair_name}, trying fallback: {e}")

    # Fallback to Alpha Vantage
    try:
        price_data = alphavantage_client.get_forex_price(from_cur, to_cur)

        # Try to get candles for indicators
        candles = alphavantage_client.get_forex_candles(from_cur, to_cur, interval="60min", limit=CANDLE_LIMIT)

        # Calculate indicators if we have candles
        indicators = {}
        if candles and len(candles) >= 20:  # Need minimum candles for indicators
            indicators = TechnicalIndicators.calculate_all(candles)
        else:
            logger.warning(f"Not enough candles from Alpha Vantage for {pair_name}, skipping indicators")

        return {
            "market": pair_name,
            "price": price_data["price"],
            "volume": 0,
            "change_percent": 0,
            "indicators": indicators,
            "source": "Alpha Vantage"
        }
    except Exception as e:
        logger.error(f"All forex APIs failed for {pair_name}: {e}")
        return None


def fetch_crypto_data(binance_client: BinanceClient, symbol: str) -> Optional[Dict]:
    """Fetch crypto data from Binance"""
    logger.info(f"Fetching crypto data: {symbol}")

    try:
        # Get 24h ticker
        ticker = binance_client.get_24h_ticker(symbol)

        # Get candles for indicators
        candles = binance_client.get_klines(symbol, interval="1h", limit=CANDLE_LIMIT)

        # Calculate indicators
        indicators = TechnicalIndicators.calculate_all(candles)

        # Format symbol (BTCUSDT → BTC/USDT)
        formatted_symbol = f"{symbol[:-4]}/{symbol[-4:]}" if symbol.endswith("USDT") else symbol

        return {
            "market": formatted_symbol,
            "price": ticker["price"],
            "volume": ticker["volume"],
            "change_percent": ticker["change_percent"],
            "indicators": indicators,
            "source": "Binance"
        }
    except Exception as e:
        logger.error(f"Binance failed for {symbol}: {e}")
        return None


def fetch_commodity_data(gold_client: GoldPriceClient, commodity: str) -> Optional[Dict]:
    """Fetch commodity data (gold, silver)"""
    logger.info(f"Fetching commodity data: {commodity}")

    try:
        if commodity == "GOLD":
            data = gold_client.get_gold_price()
        elif commodity == "SILVER":
            data = gold_client.get_silver_price()
        else:
            return None

        # Note: Free API doesn't provide historical data
        return {
            "market": data["symbol"],
            "price": data["price"],
            "volume": 0,
            "change_percent": 0,
            "indicators": {},  # No indicators without historical data
            "source": "Metals API"
        }
    except Exception as e:
        logger.error(f"Commodity API failed for {commodity}: {e}")
        return None


def write_to_sheet(ws, cols, data_list: List[Dict]):
    """
    Write market data to Google Sheets

    Args:
        ws: Worksheet object
        cols: Column mapping
        data_list: List of market data dicts
    """
    # Türkiye saati (UTC+3)
    turkey_tz = pytz.timezone('Europe/Istanbul')
    timestamp = datetime.datetime.now(turkey_tz).strftime("%Y-%m-%d %H:%M:%S")

    rows_to_add = []
    row_len = cols.AL  # Last column (AL)

    for data in data_list:
        if not data:
            continue

        indicators = data.get("indicators", {})
        support_levels = indicators.get("support_levels", [])
        resistance_levels = indicators.get("resistance_levels", [])

        row = [""] * row_len

        # Basic data
        row[cols.A - 1] = timestamp
        row[cols.B - 1] = data["market"]
        row[cols.C - 1] = data["price"]
        row[cols.D - 1] = data.get("change_percent", 0)
        row[cols.E - 1] = data.get("volume", 0)

        # Technical indicators
        row[cols.F - 1] = indicators.get("rsi", "")
        row[cols.G - 1] = indicators.get("macd", "")
        row[cols.H - 1] = indicators.get("macd_signal", "")
        row[cols.I - 1] = indicators.get("macd_histogram", "")
        row[cols.J - 1] = indicators.get("bb_upper", "")
        row[cols.K - 1] = indicators.get("bb_middle", "")
        row[cols.L - 1] = indicators.get("bb_lower", "")
        row[cols.M - 1] = indicators.get("ema_9", "")
        row[cols.N - 1] = indicators.get("ema_21", "")
        row[cols.O - 1] = indicators.get("ema_50", "")
        row[cols.P - 1] = indicators.get("ema_200", "")

        # Support/Resistance
        row[cols.Q - 1] = support_levels[0] if support_levels else ""
        row[cols.R - 1] = resistance_levels[0] if resistance_levels else ""

        # Trend
        row[cols.S - 1] = indicators.get("trend", "")

        # Durum
        row[cols.AH - 1] = status_text(1, True)
        row[cols.AI - 1] = f"Kaynak: {data.get('source', 'Bilinmiyor')}"

        rows_to_add.append(row)

    # Ayırıcı satır ekle
    separator = [""] * row_len
    separator[cols.A - 1] = f"📊 Piyasa Verisi Güncelleme: {timestamp}"
    separator[cols.AH - 1] = "Ayırıcı"

    # Write to sheet
    ws.append_rows([separator] + rows_to_add, value_input_option="RAW")
    logger.info(f"✓ Written {len(rows_to_add)} market entries to Google Sheets")


def run():
    """Main execution function for Robot 1"""
    logger.info("=" * 60)
    logger.info("ROBOT 1: MARKET HARVESTER - STARTING")
    logger.info("=" * 60)

    try:
        # Get secrets
        sheet_id = get_secret("GOOGLE_SHEET_ID")
        polygon_key = get_secret("POLYGON_API_KEY", required=False)
        alphavantage_key = get_secret("ALPHA_VANTAGE_KEY", required=False)

        # Initialize clients
        binance = BinanceClient()
        polygon = PolygonClient(polygon_key) if polygon_key else None
        alphavantage = AlphaVantageClient(alphavantage_key) if alphavantage_key else None
        gold_client = GoldPriceClient()

        # Get Google Sheets client
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        logger.info(f"Connected to Google Sheet: {SHEET_TAB}")

        # Collect all market data
        all_data = []

        # 1. Forex
        logger.info("Fetching FOREX data...")
        for from_cur, to_cur in FOREX_PAIRS:
            if alphavantage:  # Need at least one forex API
                data = fetch_forex_data(polygon, alphavantage, from_cur, to_cur)
                if data:
                    all_data.append(data)
                time.sleep(1)  # Rate limiting

        # 2. Crypto
        logger.info("Fetching CRYPTO data...")
        for symbol in CRYPTO_PAIRS:
            data = fetch_crypto_data(binance, symbol)
            if data:
                all_data.append(data)
            time.sleep(0.5)  # Binance is fast

        # 3. Commodities
        logger.info("Fetching COMMODITY data...")
        for commodity in COMMODITIES:
            data = fetch_commodity_data(gold_client, commodity)
            if data:
                all_data.append(data)
            time.sleep(0.5)

        # Write to Google Sheets
        if all_data:
            logger.info(f"Writing {len(all_data)} markets to Google Sheets...")
            write_to_sheet(ws, cols, all_data)
            logger.info("✓ ROBOT 1 COMPLETED SUCCESSFULLY")
        else:
            logger.warning("⚠ No market data collected")

    except Exception as e:
        logger.error(f"❌ ROBOT 1 FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()