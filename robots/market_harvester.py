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

from config.markets import MARKETS, get_market_category, TOTAL_MARKETS
from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns
from utils.common import status_text  # DRY: Import from common
from utils.api_clients import (
    BinanceClient, PolygonClient, AlphaVantageClient,
    GoldPriceClient, TCMBClient, FrankfurterClient, TwelveDataClient
)
from utils.indicators import TechnicalIndicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-1-MarketHarvester")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")
CANDLE_LIMIT = int(os.getenv("CANDLE_LIMIT", "200"))  # For technical indicators

# ============================================================================
# MARKETS IMPORTED FROM config/markets.py
# ============================================================================
# 27 MARKETS TOTAL: 5 Categories (FOREX: 7, others: 5 each)
# FOREX, CRYPTO, INDEX, COMMODITY, STOCK_CFD
# ============================================================================


def convert_to_try(usd_price: float, usd_try_rate: float) -> float:
    """
    Convert USD price to TRY

    Args:
        usd_price: Price in USD
        usd_try_rate: USD/TRY exchange rate

    Returns:
        Price in TRY
    """
    if not usd_price or not usd_try_rate:
        return 0
    return round(usd_price * usd_try_rate, 2)


def fetch_forex_data(
    polygon_client: Optional[PolygonClient],
    alphavantage_client: AlphaVantageClient,
    pair: str
) -> Optional[Dict]:
    """
    Fetch forex data with fallback

    Args:
        pair: Format "EUR/USD"

    Priority: Polygon.io → Alpha Vantage
    """
    # Parse pair (e.g., "EUR/USD" -> "EUR", "USD")
    from_cur, to_cur = pair.split("/")
    logger.info(f"Fetching forex data: {pair}")

    # Try Polygon first (if API key available)
    if polygon_client:
        try:
            price_data = polygon_client.get_forex_price(from_cur, to_cur)
            candles = polygon_client.get_forex_candles(from_cur, to_cur, timespan="hour", limit=CANDLE_LIMIT)

            # Calculate indicators
            indicators = TechnicalIndicators.calculate_all(candles)

            return {
                "market": pair,
                "price": price_data["price"],
                "volume": 0,  # Forex doesn't have volume like stocks
                "change_percent": 0,  # Calculate from 24h if needed
                "indicators": indicators,
                "source": "Polygon.io"
            }
        except Exception as e:
            logger.warning(f"Polygon failed for {pair}, trying fallback: {e}")

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
            logger.warning(f"Not enough candles from Alpha Vantage for {pair}, skipping indicators")

        return {
            "market": pair,
            "price": price_data["price"],
            "volume": 0,
            "change_percent": 0,
            "indicators": indicators,
            "source": "Alpha Vantage"
        }
    except Exception as e:
        logger.error(f"All forex APIs failed for {pair}: {e}")
        return None


def fetch_crypto_data(binance_client: BinanceClient, pair: str) -> Optional[Dict]:
    """
    Fetch crypto data from Binance

    Args:
        pair: Format "BTC/USDT"
    """
    # Convert "BTC/USDT" to "BTCUSDT" for Binance API
    symbol = pair.replace("/", "")
    logger.info(f"Fetching crypto data: {pair}")

    try:
        # Get 24h ticker
        ticker = binance_client.get_24h_ticker(symbol)

        # Get candles for indicators
        candles = binance_client.get_klines(symbol, interval="1h", limit=CANDLE_LIMIT)

        # Calculate indicators
        indicators = TechnicalIndicators.calculate_all(candles)

        return {
            "market": pair,  # Keep original format "BTC/USDT"
            "price": ticker["price"],
            "volume": ticker["volume"],
            "change_percent": ticker["change_percent"],
            "indicators": indicators,
            "source": "Binance"
        }
    except Exception as e:
        logger.error(f"Binance failed for {pair}: {e}")
        return None


def fetch_commodity_data(gold_client: GoldPriceClient, pair: str) -> Optional[Dict]:
    """
    Fetch commodity data (gold, silver, oil, etc.)

    Args:
        pair: Format "XAU/USD", "XAG/USD", etc.
    """
    logger.info(f"Fetching commodity data: {pair}")

    # Map commodity symbols
    commodity_map = {
        "XAU/USD": "GOLD",     # Gold
        "XAG/USD": "SILVER",   # Silver
        "WTI/USD": None,       # WTI Oil - Not available in current API
        "BRN/USD": None,       # Brent Oil - Not available in current API
        "NG/USD": None,        # Natural Gas - Not available in current API
    }

    commodity_type = commodity_map.get(pair)
    if commodity_type is None:
        logger.warning(f"Commodity {pair} not available (API missing)")
        return None

    try:
        if commodity_type == "GOLD":
            data = gold_client.get_gold_price()
        elif commodity_type == "SILVER":
            data = gold_client.get_silver_price()
        else:
            return None

        # Note: Free API doesn't provide historical data
        return {
            "market": pair,  # Use standard format
            "price": data["price"],
            "volume": 0,
            "change_percent": 0,
            "indicators": {},  # No indicators without historical data
            "source": "Metals API"
        }
    except Exception as e:
        logger.error(f"Commodity API failed for {pair}: {e}")
        return None


def fetch_twelve_data(twelve_client: TwelveDataClient, symbol: str, category: str) -> Optional[Dict]:
    """
    Fetch market data from Twelve Data API (Universal provider)

    Args:
        twelve_client: TwelveDataClient instance
        symbol: Market symbol (e.g., "EUR/USD", "SPX", "AAPL", "XAU/USD")
        category: Market category (FOREX, INDEX, COMMODITY, STOCK_CFD)

    Returns:
        Market data dict with price, indicators, etc.
    """
    logger.info(f"Fetching {category} data: {symbol}")

    try:
        # Get quote (price, volume, change%)
        quote = twelve_client.get_quote(symbol, category=category)

        # Get time series for indicators
        candles = twelve_client.get_time_series(
            symbol,
            interval="1h",
            outputsize=CANDLE_LIMIT,
            category=category
        )

        # Calculate indicators if we have enough candles
        indicators = {}
        if candles and len(candles) >= 20:
            indicators = TechnicalIndicators.calculate_all(candles)
        else:
            logger.warning(f"Not enough candles for {symbol}, skipping indicators")

        return {
            "market": symbol,
            "price": quote["price"],
            "volume": quote.get("volume", 0),
            "change_percent": quote.get("change_percent", 0),
            "indicators": indicators,
            "source": "Twelve Data"
        }
    except Exception as e:
        logger.error(f"Twelve Data failed for {symbol} ({category}): {e}")
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
    row_len = cols.BB  # Last column (BB - yeni yapı, 54 sütun)

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
        row[cols.C - 1] = data["price"]  # USD Price
        row[cols.D - 1] = data.get("price_try", "")  # TRY Price - YENİ!
        row[cols.E - 1] = data.get("change_percent", 0)
        row[cols.F - 1] = data.get("volume", 0)

        # Technical indicators
        row[cols.G - 1] = indicators.get("rsi", "")
        row[cols.H - 1] = indicators.get("macd", "")
        row[cols.I - 1] = indicators.get("macd_signal", "")
        row[cols.J - 1] = indicators.get("macd_histogram", "")
        row[cols.K - 1] = indicators.get("bb_upper", "")
        row[cols.L - 1] = indicators.get("bb_middle", "")
        row[cols.M - 1] = indicators.get("bb_lower", "")
        row[cols.N - 1] = indicators.get("ema_9", "")
        row[cols.O - 1] = indicators.get("ema_21", "")
        row[cols.P - 1] = indicators.get("ema_50", "")
        row[cols.Q - 1] = indicators.get("ema_200", "")

        # Support/Resistance
        row[cols.R - 1] = support_levels[0] if support_levels else ""
        row[cols.S - 1] = resistance_levels[0] if resistance_levels else ""

        # Trend
        row[cols.T - 1] = indicators.get("trend", "")

        # Durum (Robot 1: AU sütunu)
        row[cols.AU - 1] = status_text(1, True)
        row[cols.AS - 1] = f"Kaynak: {data.get('source', 'Bilinmiyor')}"  # Notlar

        rows_to_add.append(row)

    # Ayırıcı satır ekle (detaylı bilgi)
    separator = [""] * row_len
    now = datetime.datetime.now(turkey_tz)

    separator[cols.A - 1] = now.strftime("%Y-%m-%d %H:%M:%S")  # Tarih-saat
    separator[cols.B - 1] = "📊 VERİ TOPLAMA RAPORU"  # Başlık (separator marker)
    separator[cols.C - 1] = f"Toplam: {len(rows_to_add)} piyasa"  # Piyasa sayısı
    separator[cols.D - 1] = "Robot 1 - Market Harvester"  # Robot bilgisi
    separator[cols.E - 1] = now.strftime("%A, %d %B %Y")  # Uzun tarih
    separator[cols.AS - 1] = f"Veri kaynakları: Twelve Data, Binance, TCMB"  # Notlar

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
        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
        polygon_key = get_secret("POLYGON_API_KEY", required=False)
        alphavantage_key = get_secret("ALPHA_VANTAGE_KEY", required=False)
        twelve_data_key = get_secret("TWELVE_DATA_API_KEY", required=False)

        # Initialize clients
        binance = BinanceClient()
        polygon = PolygonClient(polygon_key) if polygon_key else None
        alphavantage = AlphaVantageClient(alphavantage_key) if alphavantage_key else None
        gold_client = GoldPriceClient()
        tcmb = TCMBClient()  # TRY exchange rates (FREE, no API key)
        twelve_data = TwelveDataClient(twelve_data_key) if twelve_data_key else None

        # Log API availability
        logger.info(f"API Keys Available:")
        logger.info(f"  - Binance (Crypto): ✅ Always available")
        logger.info(f"  - Twelve Data (Universal): {'✅' if twelve_data else '❌'}")
        logger.info(f"  - Polygon (Forex): {'✅' if polygon else '❌'}")
        logger.info(f"  - Alpha Vantage (Forex): {'✅' if alphavantage else '❌'}")
        logger.info(f"  - TCMB (TRY rates): ✅ Always available")

        # Get Google Sheets client
        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)
        cols = resolve_columns(ws)

        logger.info(f"Connected to Google Sheet: {SHEET_TAB}")
        logger.info(f"Processing {sum(len(v) for v in MARKETS.values())} markets across {len(MARKETS)} categories")

        # Get USD/TRY exchange rate from TCMB
        usd_try_rate = None
        try:
            result = tcmb.get_rate("USD")
            usd_try_rate = result["rate"]
            logger.info(f"📌 USD/TRY kuru: ₺{usd_try_rate:.4f} (TCMB)")
        except Exception as e:
            logger.warning(f"TCMB USD/TRY kuru alınamadı: {e}")
            logger.warning("⚠️  TL fiyatları hesaplanamayacak!")

        # Collect all market data
        all_data = []
        skipped_markets = []

        # Twelve Data rate limiting: 8 API calls/minute (free tier)
        # Each market uses 2 calls (quote + time_series)
        # So we can fetch 4 markets per minute
        twelve_data_call_count = 0
        TWELVE_DATA_RATE_LIMIT = 4  # Markets per minute (8 calls / 2 per market)

        # 1. FOREX (5 markets)
        logger.info("=" * 60)
        logger.info(f"📊 FOREX: {len(MARKETS['FOREX'])} markets")
        logger.info("=" * 60)
        for pair in MARKETS["FOREX"]:
            # Priority: Twelve Data → Polygon → Alpha Vantage
            data = None

            if twelve_data:
                # Rate limiting check
                if twelve_data_call_count >= TWELVE_DATA_RATE_LIMIT:
                    logger.info(f"⏱️  Rate limit reached ({twelve_data_call_count} markets), waiting 60 seconds...")
                    time.sleep(60)
                    twelve_data_call_count = 0

                data = fetch_twelve_data(twelve_data, pair, "FOREX")
                twelve_data_call_count += 1

                if data and usd_try_rate:
                    data["price_try"] = convert_to_try(data["price"], usd_try_rate)
            elif alphavantage or polygon:
                data = fetch_forex_data(polygon, alphavantage, pair)
                if data and usd_try_rate:
                    data["price_try"] = convert_to_try(data["price"], usd_try_rate)
            else:
                logger.warning(f"Skipping {pair} - No Forex API available")
                skipped_markets.append((pair, "No Forex API"))

            if data:
                all_data.append(data)
            time.sleep(1)  # Base delay between requests

        # 2. CRYPTO (5 markets)
        logger.info("=" * 60)
        logger.info(f"💰 CRYPTO: {len(MARKETS['CRYPTO'])} markets")
        logger.info("=" * 60)
        for pair in MARKETS["CRYPTO"]:
            data = fetch_crypto_data(binance, pair)
            if data and usd_try_rate:
                # Add TRY price
                data["price_try"] = convert_to_try(data["price"], usd_try_rate)
                all_data.append(data)
            elif data:
                all_data.append(data)
            time.sleep(0.5)  # Binance is fast

        # 3. INDEX (5 markets)
        logger.info("=" * 60)
        logger.info(f"📈 INDEX: {len(MARKETS['INDEX'])} markets")
        logger.info("=" * 60)
        for symbol in MARKETS["INDEX"]:
            if twelve_data:
                # Rate limiting check
                if twelve_data_call_count >= TWELVE_DATA_RATE_LIMIT:
                    logger.info(f"⏱️  Rate limit reached ({twelve_data_call_count} markets), waiting 60 seconds...")
                    time.sleep(60)
                    twelve_data_call_count = 0

                data = fetch_twelve_data(twelve_data, symbol, "INDEX")
                twelve_data_call_count += 1

                if data and usd_try_rate:
                    data["price_try"] = convert_to_try(data["price"], usd_try_rate)
                if data:
                    all_data.append(data)
                time.sleep(1)
            else:
                logger.warning(f"⏭️  Skipping {symbol} - Twelve Data API not available")
                skipped_markets.append((symbol, "Twelve Data required"))

        # 4. COMMODITY (5 markets)
        logger.info("=" * 60)
        logger.info(f"🪙 COMMODITY: {len(MARKETS['COMMODITY'])} markets")
        logger.info("=" * 60)
        for pair in MARKETS["COMMODITY"]:
            data = None

            # Priority: Twelve Data → GoldPriceClient (fallback)
            if twelve_data:
                # Rate limiting check
                if twelve_data_call_count >= TWELVE_DATA_RATE_LIMIT:
                    logger.info(f"⏱️  Rate limit reached ({twelve_data_call_count} markets), waiting 60 seconds...")
                    time.sleep(60)
                    twelve_data_call_count = 0

                data = fetch_twelve_data(twelve_data, pair, "COMMODITY")
                twelve_data_call_count += 1
            elif pair in ["XAU/USD", "XAG/USD"]:
                # Fallback to GoldPriceClient for gold/silver only
                data = fetch_commodity_data(gold_client, pair)
            else:
                logger.warning(f"⏭️  Skipping {pair} - Twelve Data API not available")
                skipped_markets.append((pair, "Twelve Data required"))

            if data and usd_try_rate:
                data["price_try"] = convert_to_try(data["price"], usd_try_rate)
            if data:
                all_data.append(data)
            time.sleep(0.5)

        # 5. STOCK_CFD (5 markets)
        logger.info("=" * 60)
        logger.info(f"📊 STOCK_CFD: {len(MARKETS['STOCK_CFD'])} markets")
        logger.info("=" * 60)
        for symbol in MARKETS["STOCK_CFD"]:
            if twelve_data:
                # Rate limiting check
                if twelve_data_call_count >= TWELVE_DATA_RATE_LIMIT:
                    logger.info(f"⏱️  Rate limit reached ({twelve_data_call_count} markets), waiting 60 seconds...")
                    time.sleep(60)
                    twelve_data_call_count = 0

                data = fetch_twelve_data(twelve_data, symbol, "STOCK_CFD")
                twelve_data_call_count += 1

                if data and usd_try_rate:
                    data["price_try"] = convert_to_try(data["price"], usd_try_rate)
                if data:
                    all_data.append(data)
                time.sleep(1)
            else:
                logger.warning(f"⏭️  Skipping {symbol} - Twelve Data API not available")
                skipped_markets.append((symbol, "Twelve Data required"))

        # Summary
        logger.info("=" * 60)
        logger.info("📊 COLLECTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Collected: {len(all_data)}/{TOTAL_MARKETS} markets")
        if skipped_markets:
            logger.info(f"⏭️  Skipped: {len(skipped_markets)}/{TOTAL_MARKETS} markets")
            for market, reason in skipped_markets:
                logger.info(f"   - {market}: {reason}")

        # Write to Google Sheets
        if all_data:
            logger.info("=" * 60)
            logger.info(f"Writing {len(all_data)} markets to Google Sheets...")
            write_to_sheet(ws, cols, all_data)
            logger.info("=" * 60)
            logger.info("✅ ROBOT 1 COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
        else:
            logger.warning("⚠ No market data collected")

    except Exception as e:
        logger.error(f"❌ ROBOT 1 FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()