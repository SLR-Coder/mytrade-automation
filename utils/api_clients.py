# -*- coding: utf-8 -*-
"""
API clients for market data providers
- Binance (Crypto)
- Polygon.io (Forex)
- AllTick (Gold/Commodities)
- Alpha Vantage (Backup + Technical Indicators)
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MyTrade-APIClients")


class BinanceClient:
    """
    Binance API client for cryptocurrency data
    FREE, real-time, <100ms latency
    """
    BASE_URL = "https://api.binance.com"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Binance client

        Args:
            api_key: Binance API key (not required for public endpoints)
        """
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-MBX-APIKEY": api_key})

    def get_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get current price for a symbol

        Args:
            symbol: Trading pair (e.g., "BTCUSDT", "ETHUSDT")

        Returns:
            {"symbol": "BTCUSDT", "price": 68450.0, "timestamp": 1699776000}
        """
        try:
            url = f"{self.BASE_URL}/api/v3/ticker/price"
            resp = self.session.get(url, params={"symbol": symbol}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                "symbol": data["symbol"],
                "price": float(data["price"]),
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"Binance get_price error for {symbol}: {e}")
            raise

    def get_24h_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get 24-hour ticker data (price, volume, change %)

        Args:
            symbol: Trading pair

        Returns:
            {
                "symbol": "BTCUSDT",
                "price": 68450.0,
                "change": 1200.0,
                "change_percent": 1.78,
                "volume": 28450.5,
                "high": 69000.0,
                "low": 67000.0
            }
        """
        try:
            url = f"{self.BASE_URL}/api/v3/ticker/24hr"
            resp = self.session.get(url, params={"symbol": symbol}, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            return {
                "symbol": data["symbol"],
                "price": float(data["lastPrice"]),
                "change": float(data["priceChange"]),
                "change_percent": float(data["priceChangePercent"]),
                "volume": float(data["volume"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"Binance get_24h_ticker error for {symbol}: {e}")
            raise

    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> List[Dict]:
        """
        Get candlestick data (OHLCV)

        Args:
            symbol: Trading pair
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles (max 1000)

        Returns:
            List of candles:
            [
                {
                    "timestamp": 1699776000,
                    "open": 68000.0,
                    "high": 68500.0,
                    "low": 67800.0,
                    "close": 68450.0,
                    "volume": 1234.5
                },
                ...
            ]
        """
        try:
            url = f"{self.BASE_URL}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            klines = []
            for k in data:
                klines.append({
                    "timestamp": k[0] // 1000,  # Convert ms to seconds
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                })

            return klines
        except Exception as e:
            logger.error(f"Binance get_klines error for {symbol}: {e}")
            raise


class PolygonClient:
    """
    Polygon.io API client for Forex data
    Premium: $199/mo, institutional-grade
    """
    BASE_URL = "https://api.polygon.io"

    def __init__(self, api_key: str):
        """
        Initialize Polygon client

        Args:
            api_key: Polygon.io API key
        """
        self.api_key = api_key
        self.session = requests.Session()

    def get_forex_price(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """
        Get current forex price

        Args:
            from_currency: Base currency (e.g., "USD")
            to_currency: Quote currency (e.g., "TRY")

        Returns:
            {
                "pair": "USD/TRY",
                "price": 34.12,
                "timestamp": 1699776000
            }
        """
        try:
            pair = f"C:{from_currency}{to_currency}"
            url = f"{self.BASE_URL}/v2/last/nbbo/{pair}"
            params = {"apiKey": self.api_key}
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Extract bid/ask
            results = data.get("results", {})
            bid = results.get("P", 0)  # Bid price
            ask = results.get("p", 0)  # Ask price
            mid_price = (bid + ask) / 2 if bid and ask else bid or ask

            return {
                "pair": f"{from_currency}/{to_currency}",
                "price": mid_price,
                "bid": bid,
                "ask": ask,
                "timestamp": results.get("t", int(time.time() * 1000)) // 1000
            }
        except Exception as e:
            logger.error(f"Polygon get_forex_price error for {from_currency}/{to_currency}: {e}")
            raise

    def get_forex_candles(
        self,
        from_currency: str,
        to_currency: str,
        timespan: str = "hour",
        limit: int = 100
    ) -> List[Dict]:
        """
        Get forex candlestick data

        Args:
            from_currency: Base currency
            to_currency: Quote currency
            timespan: "minute", "hour", "day"
            limit: Number of candles

        Returns:
            List of candles (same format as BinanceClient.get_klines)
        """
        try:
            pair = f"C:{from_currency}{to_currency}"
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=7)  # Last 7 days

            url = f"{self.BASE_URL}/v2/aggs/ticker/{pair}/range/1/{timespan}/{from_date.strftime('%Y-%m-%d')}/{to_date.strftime('%Y-%m-%d')}"
            params = {"apiKey": self.api_key, "limit": limit}
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            candles = []
            for result in data.get("results", [])[:limit]:
                candles.append({
                    "timestamp": result["t"] // 1000,
                    "open": result["o"],
                    "high": result["h"],
                    "low": result["l"],
                    "close": result["c"],
                    "volume": result.get("v", 0)
                })

            return candles
        except Exception as e:
            logger.error(f"Polygon get_forex_candles error: {e}")
            raise


class AlphaVantageClient:
    """
    Alpha Vantage API client
    - Forex, Crypto, Commodities backup
    - 50+ built-in technical indicators
    Premium: $49/mo
    """
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()

    def get_forex_price(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """Get forex exchange rate"""
        try:
            params = {
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": from_currency,
                "to_currency": to_currency,
                "apikey": self.api_key
            }
            resp = self.session.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            rate_data = data.get("Realtime Currency Exchange Rate", {})
            price = float(rate_data.get("5. Exchange Rate", 0))

            return {
                "pair": f"{from_currency}/{to_currency}",
                "price": price,
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"AlphaVantage get_forex_price error: {e}")
            raise

    def get_crypto_price(self, symbol: str, market: str = "USD") -> Dict[str, Any]:
        """Get cryptocurrency price"""
        try:
            params = {
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": symbol,
                "to_currency": market,
                "apikey": self.api_key
            }
            resp = self.session.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            rate_data = data.get("Realtime Currency Exchange Rate", {})
            price = float(rate_data.get("5. Exchange Rate", 0))

            return {
                "symbol": f"{symbol}/{market}",
                "price": price,
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"AlphaVantage get_crypto_price error: {e}")
            raise

    def get_forex_candles(self, from_currency: str, to_currency: str, interval: str = "60min", limit: int = 100) -> List[Dict]:
        """
        Get forex candles from Alpha Vantage (FX_INTRADAY)

        Args:
            from_currency: Base currency (e.g., USD)
            to_currency: Quote currency (e.g., TRY)
            interval: Time interval (1min, 5min, 15min, 30min, 60min)
            limit: Number of candles to fetch

        Returns:
            List of candles with OHLC data
        """
        try:
            params = {
                "function": "FX_INTRADAY",
                "from_symbol": from_currency,
                "to_symbol": to_currency,
                "interval": interval,
                "outputsize": "compact" if limit <= 100 else "full",
                "apikey": self.api_key
            }
            resp = self.session.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # Parse time series
            time_series_key = f"Time Series FX ({interval})"
            time_series = data.get(time_series_key, {})

            if not time_series:
                logger.warning(f"No FX data from AlphaVantage for {from_currency}/{to_currency}")
                return []

            # Convert to candles format
            candles = []
            for timestamp_str, values in sorted(time_series.items(), reverse=True)[:limit]:
                try:
                    dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    timestamp = int(dt.timestamp())
                    candles.append({
                        "timestamp": timestamp,
                        "open": float(values.get("1. open", 0)),
                        "high": float(values.get("2. high", 0)),
                        "low": float(values.get("3. low", 0)),
                        "close": float(values.get("4. close", 0)),
                        "volume": 0  # FX doesn't have volume
                    })
                except Exception as e:
                    logger.warning(f"Error parsing candle: {e}")
                    continue

            # Reverse to get oldest first (for indicators)
            candles.reverse()
            return candles

        except Exception as e:
            logger.error(f"AlphaVantage get_forex_candles error: {e}")
            return []  # Return empty list instead of raising (fallback)


# Simple Gold price client (free API fallback)
class GoldPriceClient:
    """
    Simple gold price client using free API
    For production, use AllTick ($99/mo)
    """
    BASE_URL = "https://api.metals.live/v1/spot"

    def __init__(self):
        self.session = requests.Session()

    def get_gold_price(self) -> Dict[str, Any]:
        """
        Get current gold price (XAU/USD)

        Returns:
            {"symbol": "XAU/USD", "price": 2045.50, "timestamp": ...}
        """
        try:
            resp = self.session.get(f"{self.BASE_URL}/gold", timeout=10)
            resp.raise_for_status()
            data = resp.json()

            return {
                "symbol": "XAU/USD",
                "price": float(data[0]["price"]),
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"GoldPrice error: {e}")
            raise

    def get_silver_price(self) -> Dict[str, Any]:
        """Get silver price (XAG/USD)"""
        try:
            resp = self.session.get(f"{self.BASE_URL}/silver", timeout=10)
            resp.raise_for_status()
            data = resp.json()

            return {
                "symbol": "XAG/USD",
                "price": float(data[0]["price"]),
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"SilverPrice error: {e}")
            raise


class TCMBClient:
    """
    TCMB (Türkiye Cumhuriyet Merkez Bankası) Exchange Rate API
    - FREE, no API key required
    - Official Turkish Lira exchange rates from Central Bank of Turkey
    - Daily updates
    - Source: https://www.tcmb.gov.tr/kurlar/today.xml
    """
    BASE_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"

    # Currency code mapping (XML ForexBuying field names)
    CURRENCY_CODES = {
        "USD": "USD",
        "EUR": "EUR",
        "GBP": "GBP",
        "JPY": "JPY",
        "CHF": "CHF",
        "CAD": "CAD",
        "AUD": "AUD",
        "SAR": "SAR",  # Saudi Riyal
        "SEK": "SEK",  # Swedish Krona
        "NOK": "NOK",  # Norwegian Krone
        "DKK": "DKK",  # Danish Krone
    }

    def __init__(self):
        """Initialize TCMB client (no auth needed)"""
        self.session = requests.Session()

    def get_all_rates(self) -> Dict[str, float]:
        """
        Get all forex rates to TRY from TCMB

        Returns:
            {"USD": 31.25, "EUR": 33.50, "GBP": 39.80, ...}
        """
        try:
            import xml.etree.ElementTree as ET

            resp = self.session.get(self.BASE_URL, timeout=10)
            resp.raise_for_status()

            # Parse XML
            root = ET.fromstring(resp.content)
            rates = {}

            # Iterate through currency elements
            for currency_elem in root.findall("Currency"):
                code = currency_elem.get("CurrencyCode")
                if code in self.CURRENCY_CODES:
                    # Get ForexBuying rate (döviz alış)
                    forex_buying = currency_elem.find("ForexBuying")
                    if forex_buying is not None and forex_buying.text:
                        rates[code] = float(forex_buying.text)

            return rates
        except Exception as e:
            logger.error(f"TCMB get_all_rates error: {e}")
            raise

    def get_rate(self, from_currency: str) -> Dict[str, Any]:
        """
        Get specific forex rate to TRY

        Args:
            from_currency: Currency code (e.g., "USD", "EUR")

        Returns:
            {
                "pair": "USD/TRY",
                "rate": 31.25,
                "timestamp": 1699776000
            }
        """
        try:
            rates = self.get_all_rates()

            if from_currency not in rates:
                raise ValueError(f"Currency {from_currency} not supported by TCMB")

            return {
                "pair": f"{from_currency}/TRY",
                "rate": rates[from_currency],
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"TCMB get_rate error for {from_currency}/TRY: {e}")
            raise


class FrankfurterClient:
    """
    Frankfurter API - Free forex rates from European Central Bank
    - FREE, no API key required
    - Real-time forex data for 30+ currencies
    - Open source: https://frankfurter.app
    - Note: Used as fallback, TCMB preferred for TRY rates
    """
    BASE_URL = "https://api.frankfurter.app"

    def __init__(self):
        """Initialize Frankfurter client (no auth needed)"""
        self.session = requests.Session()

    def get_forex_rate(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """
        Get forex exchange rate

        Args:
            from_currency: Base currency (e.g., "USD")
            to_currency: Target currency (e.g., "EUR")

        Returns:
            {
                "pair": "USD/EUR",
                "rate": 0.92,
                "timestamp": 1699776000
            }
        """
        try:
            url = f"{self.BASE_URL}/latest"
            params = {
                "from": from_currency,
                "to": to_currency
            }
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Response format: {"amount": 1.0, "base": "USD", "date": "2025-01-15", "rates": {"EUR": 0.92}}
            rate = data["rates"][to_currency]

            return {
                "pair": f"{from_currency}/{to_currency}",
                "rate": float(rate),
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"Frankfurter forex rate error for {from_currency}/{to_currency}: {e}")
            raise


class TwelveDataClient:
    """
    Twelve Data API Client - Universal market data provider
    - FREE TIER: 800 API calls/day (plenty for 25 markets)
    - Covers: FOREX, CRYPTO, STOCKS, INDICES, COMMODITIES
    - Real-time quotes with OHLC, volume, change%
    - Historical candles for technical analysis
    - API Docs: https://twelvedata.com/docs
    """
    BASE_URL = "https://api.twelvedata.com"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Twelve Data client

        Args:
            api_key: Twelve Data API key (can also be set via TWELVE_DATA_API_KEY env var)
        """
        from utils.secrets import get_secret
        self.api_key = api_key or get_secret("TWELVE_DATA_API_KEY")
        self.session = requests.Session()

    def _normalize_symbol(self, symbol: str, category: str) -> str:
        """
        Normalize symbol format for Twelve Data API

        Args:
            symbol: Input symbol (e.g., "BTC/USDT", "XAU/USD", "NVDA")
            category: Market category (FOREX, CRYPTO, INDEX, COMMODITY, STOCK_CFD)

        Returns:
            Normalized symbol for Twelve Data
        """
        # Remove slashes for most symbols
        if category == "CRYPTO":
            # BTC/USDT -> BTC/USD (Twelve Data uses USD, not USDT)
            return symbol.replace("/USDT", "/USD")
        elif category in ["FOREX", "COMMODITY"]:
            # EUR/USD -> EUR/USD (keep as is)
            return symbol
        elif category == "INDEX":
            # SPX -> SPX (keep as is)
            return symbol
        elif category == "STOCK_CFD":
            # NVDA -> NVDA (keep as is)
            return symbol
        return symbol

    def get_quote(self, symbol: str, category: str = "FOREX") -> Dict[str, Any]:
        """
        Get real-time quote with OHLC, volume, and change%

        Args:
            symbol: Market symbol (e.g., "EUR/USD", "BTC/USD", "AAPL")
            category: Market category for symbol normalization

        Returns:
            {
                "symbol": "EUR/USD",
                "price": 1.0850,
                "open": 1.0840,
                "high": 1.0860,
                "low": 1.0830,
                "close": 1.0850,
                "volume": 12345,
                "change": 0.0010,
                "change_percent": 0.092,
                "timestamp": 1699776000
            }
        """
        try:
            normalized_symbol = self._normalize_symbol(symbol, category)

            params = {
                "symbol": normalized_symbol,
                "apikey": self.api_key
            }

            resp = self.session.get(f"{self.BASE_URL}/quote", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # Check for errors
            if "code" in data and data["code"] != 200:
                raise ValueError(f"Twelve Data API error: {data.get('message', 'Unknown error')}")

            return {
                "symbol": symbol,  # Return original symbol
                "price": float(data.get("close", 0)),
                "open": float(data.get("open", 0)),
                "high": float(data.get("high", 0)),
                "low": float(data.get("low", 0)),
                "close": float(data.get("close", 0)),
                "volume": float(data.get("volume", 0)) if data.get("volume") else 0,
                "change": float(data.get("change", 0)) if data.get("change") else 0,
                "change_percent": float(data.get("percent_change", 0)) if data.get("percent_change") else 0,
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"TwelveData get_quote error for {symbol}: {e}")
            raise

    def get_time_series(
        self,
        symbol: str,
        interval: str = "1h",
        outputsize: int = 100,
        category: str = "FOREX"
    ) -> List[Dict]:
        """
        Get historical candlestick data (OHLCV)

        Args:
            symbol: Market symbol
            interval: Time interval (1min, 5min, 15min, 30min, 1h, 4h, 1day)
            outputsize: Number of candles (max 5000)
            category: Market category for symbol normalization

        Returns:
            List of candles (same format as BinanceClient.get_klines)
        """
        try:
            normalized_symbol = self._normalize_symbol(symbol, category)

            params = {
                "symbol": normalized_symbol,
                "interval": interval,
                "outputsize": outputsize,
                "apikey": self.api_key
            }

            resp = self.session.get(f"{self.BASE_URL}/time_series", params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            # Check for errors
            if "code" in data and data["code"] != 200:
                raise ValueError(f"Twelve Data API error: {data.get('message', 'Unknown error')}")

            # Parse time series
            values = data.get("values", [])
            if not values:
                logger.warning(f"No time series data for {symbol}")
                return []

            candles = []
            for item in values:
                try:
                    # Parse datetime
                    dt_str = item.get("datetime", "")
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                    timestamp = int(dt.timestamp())

                    candles.append({
                        "timestamp": timestamp,
                        "open": float(item.get("open", 0)),
                        "high": float(item.get("high", 0)),
                        "low": float(item.get("low", 0)),
                        "close": float(item.get("close", 0)),
                        "volume": float(item.get("volume", 0)) if item.get("volume") else 0
                    })
                except Exception as e:
                    logger.warning(f"Error parsing candle for {symbol}: {e}")
                    continue

            # Reverse to get oldest first (for technical indicators)
            candles.reverse()
            return candles

        except Exception as e:
            logger.error(f"TwelveData get_time_series error for {symbol}: {e}")
            raise

    def get_price(self, symbol: str, category: str = "FOREX") -> Dict[str, Any]:
        """
        Get simple real-time price (lightweight endpoint)

        Args:
            symbol: Market symbol
            category: Market category for symbol normalization

        Returns:
            {"symbol": "EUR/USD", "price": 1.0850, "timestamp": 1699776000}
        """
        try:
            normalized_symbol = self._normalize_symbol(symbol, category)

            params = {
                "symbol": normalized_symbol,
                "apikey": self.api_key
            }

            resp = self.session.get(f"{self.BASE_URL}/price", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Check for errors
            if "code" in data and data["code"] != 200:
                raise ValueError(f"Twelve Data API error: {data.get('message', 'Unknown error')}")

            return {
                "symbol": symbol,  # Return original symbol
                "price": float(data.get("price", 0)),
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"TwelveData get_price error for {symbol}: {e}")
            raise