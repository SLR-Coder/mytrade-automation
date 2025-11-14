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