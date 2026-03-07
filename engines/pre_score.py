# engines/pre_score.py
# -*- coding: utf-8 -*-
"""
Pre-Score Engine
================
Calculates base quantitative scores for ALL assets in the universe.
This is the first stage of the pipeline - pure numerical analysis.

Scores calculated:
- Market Score: price trend, volume, market cap
- Flow Score: net inflow/outflow, exchange balance shift
- Derivatives Score: OI, funding, liquidation pressure
- Momentum Score: RSI, MACD, trend strength

Output: Normalized scores (0-100) for each category + composite score
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from .coinglass_client import get_coinglass_client

logger = logging.getLogger("PreScoreEngine")

# Score weights for composite calculation
SCORE_WEIGHTS = {
    "market": 0.20,      # Price, volume, market cap
    "flow": 0.30,        # Exchange flow - strong signal in crypto
    "derivatives": 0.30, # OI, funding, liquidations
    "momentum": 0.20     # Technical indicators
}

# Thresholds for scoring
FUNDING_EXTREME_HIGH = 0.01    # 1% = extreme bullish sentiment
FUNDING_EXTREME_LOW = -0.01   # -1% = extreme bearish sentiment
FUNDING_NEUTRAL = 0.0001      # Near-zero funding

OI_CHANGE_SIGNIFICANT = 5.0   # 5% OI change is significant
LIQUIDATION_RATIO_EXTREME = 3.0  # 3:1 long/short liquidation ratio

FLOW_SIGNIFICANT_PCT = 2.0    # 2% of supply moving is significant


class PreScoreEngine:
    """
    Pre-score engine for quantitative analysis.
    Calculates normalized scores for all assets before AI analysis.
    """

    def __init__(self):
        self.coinglass = get_coinglass_client()

    def calculate_market_score(self, market_data: Dict) -> Dict:
        """
        Calculate market score from price/volume data

        Args:
            market_data: Dict with price, volume, market_cap, change_24h

        Returns:
            Dict with score and components
        """
        score = 50  # Neutral baseline

        # Price change component (0-100)
        change_24h = float(market_data.get("change_24h", 0) or 0)

        if change_24h > 10:
            price_score = 90
        elif change_24h > 5:
            price_score = 75
        elif change_24h > 2:
            price_score = 60
        elif change_24h > 0:
            price_score = 55
        elif change_24h > -2:
            price_score = 45
        elif change_24h > -5:
            price_score = 35
        elif change_24h > -10:
            price_score = 20
        else:
            price_score = 10

        # Volume component - high volume confirms move
        volume_24h = float(market_data.get("volume_24h", 0) or 0)
        avg_volume = float(market_data.get("avg_volume", volume_24h) or volume_24h)

        if avg_volume > 0:
            volume_ratio = volume_24h / avg_volume
            if volume_ratio > 2.0:
                volume_score = 80
            elif volume_ratio > 1.5:
                volume_score = 65
            elif volume_ratio > 1.0:
                volume_score = 50
            elif volume_ratio > 0.5:
                volume_score = 35
            else:
                volume_score = 20
        else:
            volume_score = 50

        # Combined market score
        score = int(price_score * 0.6 + volume_score * 0.4)

        return {
            "score": score,
            "price_score": price_score,
            "volume_score": volume_score,
            "change_24h": change_24h,
            "direction": "bullish" if score > 55 else "bearish" if score < 45 else "neutral"
        }

    def calculate_flow_score(self, flow_data: Dict) -> Dict:
        """
        Calculate flow score from exchange flow data

        Args:
            flow_data: Dict with net_flow_24h, inflow, outflow

        Returns:
            Dict with score and components
        """
        score = 50  # Neutral baseline

        net_flow = float(flow_data.get("net_flow_24h", 0) or 0)
        inflow = float(flow_data.get("inflow_24h", 0) or 0)
        outflow = float(flow_data.get("outflow_24h", 0) or 0)

        # Net outflow is bullish (coins leaving exchanges)
        # Net inflow is bearish (coins entering exchanges for selling)

        total_flow = inflow + outflow
        if total_flow > 0:
            flow_ratio = net_flow / total_flow
        else:
            flow_ratio = 0

        # Significant outflow = bullish
        if net_flow < 0:  # Outflow
            if abs(net_flow) > total_flow * 0.1:  # >10% net outflow
                score = 85
            elif abs(net_flow) > total_flow * 0.05:
                score = 70
            else:
                score = 60
        elif net_flow > 0:  # Inflow
            if net_flow > total_flow * 0.1:  # >10% net inflow
                score = 15
            elif net_flow > total_flow * 0.05:
                score = 30
            else:
                score = 40
        else:
            score = 50

        return {
            "score": score,
            "net_flow": net_flow,
            "inflow": inflow,
            "outflow": outflow,
            "flow_direction": "outflow" if net_flow < 0 else "inflow" if net_flow > 0 else "neutral",
            "signal": "bullish" if score > 55 else "bearish" if score < 45 else "neutral"
        }

    def calculate_derivatives_score(self, deriv_data: Dict) -> Dict:
        """
        Calculate derivatives score from OI, funding, liquidations

        Args:
            deriv_data: Dict with funding_rate, open_interest, liquidations

        Returns:
            Dict with score and components
        """
        score = 50
        components = []

        # Funding rate analysis
        funding_rate = float(deriv_data.get("funding_rate_avg", 0) or 0)

        if funding_rate > FUNDING_EXTREME_HIGH:
            funding_score = 20  # Extreme bullish = contrarian bearish
            components.append("extreme_funding_high")
        elif funding_rate > 0.0005:
            funding_score = 40  # High funding = caution
            components.append("high_funding")
        elif funding_rate > FUNDING_NEUTRAL:
            funding_score = 55  # Slightly bullish
        elif funding_rate > -0.0005:
            funding_score = 50  # Neutral
        elif funding_rate > FUNDING_EXTREME_LOW:
            funding_score = 60  # Negative = bullish potential
            components.append("negative_funding")
        else:
            funding_score = 80  # Extreme negative = contrarian bullish
            components.append("extreme_funding_low")

        # Liquidation analysis
        long_liq = float(deriv_data.get("liquidations_long_24h", 0) or 0)
        short_liq = float(deriv_data.get("liquidations_short_24h", 0) or 0)

        if long_liq > 0 and short_liq > 0:
            liq_ratio = long_liq / short_liq
        elif long_liq > 0:
            liq_ratio = LIQUIDATION_RATIO_EXTREME
        elif short_liq > 0:
            liq_ratio = 1 / LIQUIDATION_RATIO_EXTREME
        else:
            liq_ratio = 1.0

        if liq_ratio > LIQUIDATION_RATIO_EXTREME:
            liq_score = 30  # More longs liquidated = bearish
            components.append("long_liquidation_dominant")
        elif liq_ratio > 1.5:
            liq_score = 40
        elif liq_ratio > 0.67:
            liq_score = 50  # Balanced
        elif liq_ratio > 1 / LIQUIDATION_RATIO_EXTREME:
            liq_score = 60
        else:
            liq_score = 70  # More shorts liquidated = bullish
            components.append("short_liquidation_dominant")

        # Long/Short ratio
        long_ratio = float(deriv_data.get("long_ratio", 50) or 50)
        short_ratio = float(deriv_data.get("short_ratio", 50) or 50)

        if long_ratio > 70:
            ls_score = 30  # Too many longs = contrarian bearish
            components.append("overcrowded_long")
        elif long_ratio > 55:
            ls_score = 45
        elif long_ratio > 45:
            ls_score = 50  # Balanced
        elif long_ratio > 30:
            ls_score = 55
        else:
            ls_score = 70  # Too many shorts = contrarian bullish
            components.append("overcrowded_short")

        # Combined derivatives score
        score = int(funding_score * 0.4 + liq_score * 0.3 + ls_score * 0.3)

        return {
            "score": score,
            "funding_score": funding_score,
            "liquidation_score": liq_score,
            "long_short_score": ls_score,
            "funding_rate": funding_rate,
            "long_ratio": long_ratio,
            "short_ratio": short_ratio,
            "liquidation_ratio": liq_ratio,
            "components": components,
            "signal": "bullish" if score > 55 else "bearish" if score < 45 else "neutral"
        }

    def calculate_momentum_score(self, indicators: Dict) -> Dict:
        """
        Calculate momentum score from technical indicators

        Args:
            indicators: Dict with rsi, macd, trend, etc.

        Returns:
            Dict with score and components
        """
        score = 50
        components = []

        # RSI analysis
        rsi = float(indicators.get("rsi", 50) or 50)

        if rsi > 80:
            rsi_score = 20  # Overbought
            components.append("overbought")
        elif rsi > 70:
            rsi_score = 35
        elif rsi > 55:
            rsi_score = 60  # Bullish momentum
        elif rsi > 45:
            rsi_score = 50  # Neutral
        elif rsi > 30:
            rsi_score = 40  # Bearish momentum
        elif rsi > 20:
            rsi_score = 65  # Oversold = potential bounce
        else:
            rsi_score = 80  # Extremely oversold
            components.append("oversold")

        # Trend analysis
        trend = indicators.get("trend", "").lower()

        if "strong" in trend and "up" in trend:
            trend_score = 75
            components.append("strong_uptrend")
        elif "up" in trend:
            trend_score = 60
        elif "strong" in trend and "down" in trend:
            trend_score = 25
            components.append("strong_downtrend")
        elif "down" in trend:
            trend_score = 40
        else:
            trend_score = 50  # Sideways

        # Combined momentum score
        score = int(rsi_score * 0.5 + trend_score * 0.5)

        return {
            "score": score,
            "rsi_score": rsi_score,
            "trend_score": trend_score,
            "rsi": rsi,
            "trend": trend,
            "components": components,
            "signal": "bullish" if score > 55 else "bearish" if score < 45 else "neutral"
        }

    def calculate_composite_score(self, scores: Dict) -> Dict:
        """
        Calculate weighted composite score from all components

        Args:
            scores: Dict with market, flow, derivatives, momentum scores

        Returns:
            Dict with composite score and breakdown
        """
        market_score = scores.get("market", {}).get("score", 50)
        flow_score = scores.get("flow", {}).get("score", 50)
        derivatives_score = scores.get("derivatives", {}).get("score", 50)
        momentum_score = scores.get("momentum", {}).get("score", 50)

        # Weighted average
        composite = int(
            market_score * SCORE_WEIGHTS["market"] +
            flow_score * SCORE_WEIGHTS["flow"] +
            derivatives_score * SCORE_WEIGHTS["derivatives"] +
            momentum_score * SCORE_WEIGHTS["momentum"]
        )

        # Determine bias
        if composite >= 70:
            bias = "STRONG_BULLISH"
            confidence = min(95, 50 + (composite - 50))
        elif composite >= 60:
            bias = "BULLISH"
            confidence = min(85, 40 + (composite - 50))
        elif composite >= 55:
            bias = "LEAN_BULLISH"
            confidence = min(70, 30 + (composite - 50))
        elif composite >= 45:
            bias = "NEUTRAL"
            confidence = max(30, 60 - abs(composite - 50))
        elif composite >= 40:
            bias = "LEAN_BEARISH"
            confidence = min(70, 30 + (50 - composite))
        elif composite >= 30:
            bias = "BEARISH"
            confidence = min(85, 40 + (50 - composite))
        else:
            bias = "STRONG_BEARISH"
            confidence = min(95, 50 + (50 - composite))

        return {
            "composite_score": composite,
            "bias": bias,
            "confidence": confidence,
            "breakdown": {
                "market": market_score,
                "flow": flow_score,
                "derivatives": derivatives_score,
                "momentum": momentum_score
            },
            "weights": SCORE_WEIGHTS
        }

    def score_asset(self, symbol: str, market_data: Dict, indicators: Dict = None) -> Dict:
        """
        Calculate full pre-score for a single asset

        Args:
            symbol: Asset symbol (e.g., "BTC/USDT")
            market_data: Price/volume data from CoinGecko/exchange
            indicators: Optional technical indicators

        Returns:
            Complete pre-score analysis
        """
        logger.info(f"Calculating pre-score for {symbol}...")

        # Get CoinGlass derivatives data
        cg_metrics = self.coinglass.get_market_metrics(symbol)

        # Calculate individual scores
        scores = {
            "market": self.calculate_market_score(market_data),
            "flow": self.calculate_flow_score(cg_metrics),
            "derivatives": self.calculate_derivatives_score(cg_metrics),
            "momentum": self.calculate_momentum_score(indicators or {})
        }

        # Calculate composite
        composite = self.calculate_composite_score(scores)

        return {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "scores": scores,
            "composite": composite,
            "coinglass_data": cg_metrics,
            "pre_score_complete": True
        }

    def score_batch(self, assets: List[Dict]) -> List[Dict]:
        """
        Calculate pre-scores for multiple assets

        Args:
            assets: List of dicts with symbol, market_data, indicators

        Returns:
            List of pre-score results
        """
        results = []

        for asset in assets:
            symbol = asset.get("symbol")
            market_data = asset.get("market_data", {})
            indicators = asset.get("indicators", {})

            try:
                score = self.score_asset(symbol, market_data, indicators)
                results.append(score)
            except Exception as e:
                logger.error(f"Error scoring {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "error": str(e),
                    "pre_score_complete": False
                })

        return results
