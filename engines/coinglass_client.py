# engines/coinglass_client.py
# -*- coding: utf-8 -*-
"""
CoinGlass API Client
====================
Fetches on-chain and derivatives data:
- Net flow (exchange inflow/outflow)
- Open Interest (OI)
- Funding rates
- Liquidations
- Exchange balances

API Docs: https://docs.coinglass.com/
"""

import os
import time
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("CoinGlassClient")

# CoinGlass API base URL
COINGLASS_BASE_URL = "https://open-api.coinglass.com/public/v2"

# Rate limiting
RATE_LIMIT_DELAY = 0.5  # seconds between requests


class CoinGlassClient:
    """CoinGlass API client for derivatives and flow data"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize CoinGlass client

        Args:
            api_key: CoinGlass API key. If not provided, reads from COINGLASS_API_KEY env var
        """
        self.api_key = api_key or os.getenv("COINGLASS_API_KEY")
        if not self.api_key:
            logger.warning("COINGLASS_API_KEY not set - some features may not work")

        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json",
            "coinglassSecret": self.api_key or ""
        })
        self.last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Make API request with error handling

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response data or None on error
        """
        self._rate_limit()

        url = f"{COINGLASS_BASE_URL}/{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data.get("code") == "0" or data.get("success"):
                return data.get("data")
            else:
                logger.error(f"CoinGlass API error: {data.get('msg', 'Unknown error')}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"CoinGlass request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"CoinGlass unexpected error: {e}")
            return None

    # ==================== FUNDING RATES ====================

    def get_funding_rates(self, symbol: str = None) -> Optional[List[Dict]]:
        """
        Get current funding rates across exchanges

        Args:
            symbol: Optional symbol filter (e.g., "BTC")

        Returns:
            List of funding rate data
        """
        params = {}
        if symbol:
            params["symbol"] = symbol.upper().replace("/USDT", "").replace("USDT", "")

        return self._request("funding", params)

    def get_funding_rate_history(self, symbol: str, interval: str = "h8") -> Optional[List[Dict]]:
        """
        Get historical funding rates

        Args:
            symbol: Symbol (e.g., "BTC")
            interval: Time interval (h1, h4, h8, h24)

        Returns:
            Historical funding rate data
        """
        clean_symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
        return self._request(f"funding_chart/{clean_symbol}", {"interval": interval})

    # ==================== OPEN INTEREST ====================

    def get_open_interest(self, symbol: str = None) -> Optional[List[Dict]]:
        """
        Get open interest data across exchanges

        Args:
            symbol: Optional symbol filter

        Returns:
            Open interest data
        """
        params = {}
        if symbol:
            params["symbol"] = symbol.upper().replace("/USDT", "").replace("USDT", "")

        return self._request("open_interest", params)

    def get_oi_history(self, symbol: str, interval: str = "h4") -> Optional[List[Dict]]:
        """
        Get historical open interest

        Args:
            symbol: Symbol
            interval: Time interval

        Returns:
            Historical OI data
        """
        clean_symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
        return self._request(f"open_interest_history/{clean_symbol}", {"interval": interval})

    # ==================== LIQUIDATIONS ====================

    def get_liquidations(self, symbol: str = None, time_type: str = "h24") -> Optional[List[Dict]]:
        """
        Get liquidation data

        Args:
            symbol: Optional symbol filter
            time_type: Time period (h1, h4, h12, h24)

        Returns:
            Liquidation data
        """
        params = {"time_type": time_type}
        if symbol:
            params["symbol"] = symbol.upper().replace("/USDT", "").replace("USDT", "")

        return self._request("liquidation", params)

    def get_liquidation_history(self, symbol: str, interval: str = "h4") -> Optional[List[Dict]]:
        """
        Get historical liquidations

        Args:
            symbol: Symbol
            interval: Time interval

        Returns:
            Historical liquidation data
        """
        clean_symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
        return self._request(f"liquidation_chart/{clean_symbol}", {"interval": interval})

    # ==================== EXCHANGE FLOW ====================

    def get_exchange_flow(self, symbol: str, time_type: str = "h24") -> Optional[Dict]:
        """
        Get exchange inflow/outflow data

        Args:
            symbol: Symbol (e.g., "BTC")
            time_type: Time period (h1, h4, h12, h24, d7)

        Returns:
            Flow data with inflow/outflow amounts
        """
        clean_symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
        return self._request(f"exchange_flow/{clean_symbol}", {"time_type": time_type})

    def get_exchange_balance(self, symbol: str) -> Optional[List[Dict]]:
        """
        Get exchange balance data

        Args:
            symbol: Symbol

        Returns:
            Exchange balance data
        """
        clean_symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
        return self._request(f"exchange_balance/{clean_symbol}")

    # ==================== LONG/SHORT RATIO ====================

    def get_long_short_ratio(self, symbol: str, time_type: str = "h24") -> Optional[Dict]:
        """
        Get long/short ratio

        Args:
            symbol: Symbol
            time_type: Time period

        Returns:
            Long/short ratio data
        """
        clean_symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
        return self._request(f"long_short/{clean_symbol}", {"time_type": time_type})

    # ==================== AGGREGATED DATA ====================

    def get_market_metrics(self, symbol: str) -> Dict:
        """
        Get all market metrics for a symbol in one call

        Args:
            symbol: Symbol (e.g., "BTC/USDT")

        Returns:
            Aggregated metrics dict with:
            - funding_rate
            - open_interest
            - liquidations_24h
            - net_flow_24h
            - long_short_ratio
        """
        clean_symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")

        metrics = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "funding_rate": None,
            "funding_rate_avg": None,
            "open_interest_usd": None,
            "oi_change_24h_pct": None,
            "liquidations_long_24h": None,
            "liquidations_short_24h": None,
            "liquidations_total_24h": None,
            "net_flow_24h": None,
            "inflow_24h": None,
            "outflow_24h": None,
            "long_ratio": None,
            "short_ratio": None,
            "data_available": False
        }

        # Funding rates
        funding_data = self.get_funding_rates(clean_symbol)
        if funding_data and len(funding_data) > 0:
            # Get average funding rate across exchanges
            rates = [float(f.get("rate", 0)) for f in funding_data if f.get("rate")]
            if rates:
                metrics["funding_rate_avg"] = sum(rates) / len(rates)
                metrics["funding_rate"] = rates[0]  # First exchange rate

        # Open Interest
        oi_data = self.get_open_interest(clean_symbol)
        if oi_data and len(oi_data) > 0:
            total_oi = sum(float(o.get("openInterest", 0)) for o in oi_data)
            metrics["open_interest_usd"] = total_oi

        # Liquidations
        liq_data = self.get_liquidations(clean_symbol, "h24")
        if liq_data and len(liq_data) > 0:
            long_liq = sum(float(l.get("longLiquidation", 0)) for l in liq_data)
            short_liq = sum(float(l.get("shortLiquidation", 0)) for l in liq_data)
            metrics["liquidations_long_24h"] = long_liq
            metrics["liquidations_short_24h"] = short_liq
            metrics["liquidations_total_24h"] = long_liq + short_liq

        # Exchange Flow
        flow_data = self.get_exchange_flow(clean_symbol, "h24")
        if flow_data:
            inflow = float(flow_data.get("inflow", 0))
            outflow = float(flow_data.get("outflow", 0))
            metrics["inflow_24h"] = inflow
            metrics["outflow_24h"] = outflow
            metrics["net_flow_24h"] = inflow - outflow

        # Long/Short Ratio
        ls_data = self.get_long_short_ratio(clean_symbol, "h24")
        if ls_data:
            metrics["long_ratio"] = float(ls_data.get("longRate", 50))
            metrics["short_ratio"] = float(ls_data.get("shortRate", 50))

        # Mark as available if we got any data
        if any(v is not None for k, v in metrics.items() if k not in ["symbol", "timestamp", "data_available"]):
            metrics["data_available"] = True

        return metrics

    def get_batch_metrics(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get metrics for multiple symbols

        Args:
            symbols: List of symbols

        Returns:
            Dict mapping symbol to metrics
        """
        results = {}
        for symbol in symbols:
            logger.info(f"Fetching CoinGlass metrics for {symbol}...")
            results[symbol] = self.get_market_metrics(symbol)
        return results


# Singleton instance
_client_instance = None

def get_coinglass_client() -> CoinGlassClient:
    """Get or create CoinGlass client singleton"""
    global _client_instance
    if _client_instance is None:
        _client_instance = CoinGlassClient()
    return _client_instance
