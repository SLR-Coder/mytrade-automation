# engines/shortlist.py
# -*- coding: utf-8 -*-
"""
Shortlist Engine
================
Selects TOP candidates from pre-scored universe.
Only shortlisted assets go through expensive AI analysis.

Selection criteria:
- Composite score extremes (strong signals)
- Anomaly detection (unusual flow, liquidations)
- Narrative potential (recent news/events)

Output: Top 4 NOW + Next 2 CANDIDATES
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger("ShortlistEngine")

# Shortlist configuration
TOP_NOW_COUNT = 4      # Primary opportunities
NEXT_CANDIDATES = 2     # Secondary watchlist
MIN_CONFIDENCE = 55     # Minimum confidence to consider
ANOMALY_THRESHOLD = 2.0 # Standard deviations for anomaly


class ShortlistEngine:
    """
    Shortlist engine for candidate selection.
    Reduces the universe to actionable set.
    """

    def __init__(self):
        pass

    def detect_anomalies(self, pre_score: Dict) -> List[str]:
        """
        Detect anomalies in pre-score data

        Args:
            pre_score: Pre-score result for asset

        Returns:
            List of anomaly flags
        """
        anomalies = []

        scores = pre_score.get("scores", {})
        coinglass = pre_score.get("coinglass_data", {})

        # Flow anomaly - significant net flow
        flow_score = scores.get("flow", {}).get("score", 50)
        if flow_score >= 80 or flow_score <= 20:
            anomalies.append("FLOW_ANOMALY")

        # Derivatives anomaly - extreme funding or liquidations
        deriv = scores.get("derivatives", {})
        if "extreme_funding_high" in deriv.get("components", []):
            anomalies.append("EXTREME_FUNDING_HIGH")
        if "extreme_funding_low" in deriv.get("components", []):
            anomalies.append("EXTREME_FUNDING_LOW")
        if "long_liquidation_dominant" in deriv.get("components", []):
            anomalies.append("LONG_LIQUIDATION_SPIKE")
        if "short_liquidation_dominant" in deriv.get("components", []):
            anomalies.append("SHORT_LIQUIDATION_SPIKE")

        # Momentum anomaly - extreme RSI
        momentum = scores.get("momentum", {})
        if "overbought" in momentum.get("components", []):
            anomalies.append("RSI_OVERBOUGHT")
        if "oversold" in momentum.get("components", []):
            anomalies.append("RSI_OVERSOLD")

        # Crowded trade anomaly
        if "overcrowded_long" in deriv.get("components", []):
            anomalies.append("OVERCROWDED_LONG")
        if "overcrowded_short" in deriv.get("components", []):
            anomalies.append("OVERCROWDED_SHORT")

        return anomalies

    def calculate_priority_score(self, pre_score: Dict) -> float:
        """
        Calculate priority score for shortlist ranking

        Args:
            pre_score: Pre-score result

        Returns:
            Priority score (higher = more important)
        """
        composite = pre_score.get("composite", {})
        base_score = composite.get("composite_score", 50)
        confidence = composite.get("confidence", 50)

        # Distance from neutral (50) indicates stronger signal
        signal_strength = abs(base_score - 50)

        # Anomaly bonus
        anomalies = self.detect_anomalies(pre_score)
        anomaly_bonus = len(anomalies) * 5

        # Calculate priority
        priority = (signal_strength * 1.5) + (confidence * 0.5) + anomaly_bonus

        return priority

    def rank_assets(self, pre_scores: List[Dict]) -> List[Dict]:
        """
        Rank assets by priority score

        Args:
            pre_scores: List of pre-score results

        Returns:
            Sorted list with priority scores
        """
        ranked = []

        for ps in pre_scores:
            if not ps.get("pre_score_complete"):
                continue

            priority = self.calculate_priority_score(ps)
            anomalies = self.detect_anomalies(ps)

            ranked.append({
                **ps,
                "priority_score": priority,
                "anomalies": anomalies,
                "has_anomaly": len(anomalies) > 0
            })

        # Sort by priority (descending)
        ranked.sort(key=lambda x: x["priority_score"], reverse=True)

        return ranked

    def select_shortlist(self, pre_scores: List[Dict]) -> Dict:
        """
        Select shortlist from pre-scored assets

        Args:
            pre_scores: List of pre-score results

        Returns:
            Shortlist with Top 4 Now + Next 2 Candidates
        """
        logger.info(f"Selecting shortlist from {len(pre_scores)} assets...")

        # Rank all assets
        ranked = self.rank_assets(pre_scores)

        # Separate bullish and bearish signals
        bullish = [r for r in ranked if r["composite"]["bias"] in ["STRONG_BULLISH", "BULLISH", "LEAN_BULLISH"]]
        bearish = [r for r in ranked if r["composite"]["bias"] in ["STRONG_BEARISH", "BEARISH", "LEAN_BEARISH"]]
        neutral = [r for r in ranked if r["composite"]["bias"] == "NEUTRAL"]

        # Select Top 4 NOW - mix of strongest signals
        top_now = []

        # Take top bullish
        top_now.extend(bullish[:2])

        # Take top bearish
        top_now.extend(bearish[:2])

        # If not enough, fill from remaining
        if len(top_now) < TOP_NOW_COUNT:
            remaining = [r for r in ranked if r not in top_now]
            top_now.extend(remaining[:TOP_NOW_COUNT - len(top_now)])

        # Ensure we have max TOP_NOW_COUNT
        top_now = top_now[:TOP_NOW_COUNT]

        # Select Next 2 CANDIDATES - assets with anomalies or potential
        used_symbols = {t["symbol"] for t in top_now}
        candidates = [r for r in ranked if r["symbol"] not in used_symbols]

        # Prioritize anomalies
        anomaly_candidates = [c for c in candidates if c["has_anomaly"]]
        regular_candidates = [c for c in candidates if not c["has_anomaly"]]

        next_candidates = anomaly_candidates[:NEXT_CANDIDATES]
        if len(next_candidates) < NEXT_CANDIDATES:
            next_candidates.extend(regular_candidates[:NEXT_CANDIDATES - len(next_candidates)])

        # Summary stats
        market_sentiment = self._calculate_market_sentiment(ranked)

        shortlist = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_analyzed": len(pre_scores),
            "total_ranked": len(ranked),
            "top_now": [self._format_shortlist_entry(t, "TOP_NOW") for t in top_now],
            "next_candidates": [self._format_shortlist_entry(c, "NEXT") for c in next_candidates],
            "market_sentiment": market_sentiment,
            "anomaly_count": sum(1 for r in ranked if r["has_anomaly"]),
            "all_ranked": ranked  # Keep for debugging
        }

        logger.info(f"Shortlist: {len(top_now)} TOP NOW + {len(next_candidates)} NEXT")
        logger.info(f"Market sentiment: {market_sentiment['overall']}")

        return shortlist

    def _format_shortlist_entry(self, entry: Dict, category: str) -> Dict:
        """Format shortlist entry for output"""
        composite = entry.get("composite", {})

        return {
            "symbol": entry["symbol"],
            "category": category,
            "bias": composite.get("bias", "NEUTRAL"),
            "composite_score": composite.get("composite_score", 50),
            "confidence": composite.get("confidence", 50),
            "priority_score": entry.get("priority_score", 0),
            "anomalies": entry.get("anomalies", []),
            "breakdown": composite.get("breakdown", {}),
            "action_hint": self._get_action_hint(composite)
        }

    def _get_action_hint(self, composite: Dict) -> str:
        """Get action hint based on composite score"""
        bias = composite.get("bias", "NEUTRAL")
        confidence = composite.get("confidence", 50)

        if bias in ["STRONG_BULLISH", "STRONG_BEARISH"] and confidence >= 75:
            return "HIGH_CONVICTION"
        elif bias in ["BULLISH", "BEARISH"] and confidence >= 60:
            return "MODERATE_CONVICTION"
        elif bias in ["LEAN_BULLISH", "LEAN_BEARISH"]:
            return "WATCH_CLOSELY"
        else:
            return "WAIT_FOR_CLARITY"

    def _calculate_market_sentiment(self, ranked: List[Dict]) -> Dict:
        """Calculate overall market sentiment from all assets"""
        if not ranked:
            return {"overall": "NEUTRAL", "bullish_pct": 50, "bearish_pct": 50}

        bullish_count = sum(1 for r in ranked if r["composite"]["composite_score"] > 55)
        bearish_count = sum(1 for r in ranked if r["composite"]["composite_score"] < 45)
        total = len(ranked)

        bullish_pct = (bullish_count / total) * 100
        bearish_pct = (bearish_count / total) * 100

        if bullish_pct > 60:
            overall = "RISK_ON"
        elif bearish_pct > 60:
            overall = "RISK_OFF"
        elif bullish_pct > bearish_pct:
            overall = "LEAN_BULLISH"
        elif bearish_pct > bullish_pct:
            overall = "LEAN_BEARISH"
        else:
            overall = "MIXED"

        # Average composite score
        avg_score = sum(r["composite"]["composite_score"] for r in ranked) / total

        return {
            "overall": overall,
            "bullish_pct": round(bullish_pct, 1),
            "bearish_pct": round(bearish_pct, 1),
            "neutral_pct": round(100 - bullish_pct - bearish_pct, 1),
            "avg_score": round(avg_score, 1),
            "total_assets": total
        }
