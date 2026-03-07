# engines/deterministic_scorer.py
# -*- coding: utf-8 -*-
"""
Deterministic Scoring Engine
============================
The BACKBONE of the scoring system.
Combines all inputs with weighted scoring to produce unified bias.

This is NOT an AI - it's pure deterministic logic.
AI models inform this scorer, but don't replace it.

Inputs:
- Pre-score (market, flow, derivatives, momentum)
- Grok narrative (normalized by Gemini)
- Event data (parsed by Gemini)
- Macro context (if event day)

Output:
- Unified Bias: BULLISH / BEARISH / NEUTRAL
- Confidence: 0-100
- Signal Strength: STRONG / MODERATE / WEAK
- Conflict flags
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("DeterministicScorer")

# Master weights for final score
MASTER_WEIGHTS = {
    "pre_score": 0.50,      # Quantitative foundation
    "narrative": 0.20,      # Grok + Gemini narrative
    "events": 0.15,         # Parsed events
    "macro": 0.15           # Macro context
}

# Conflict detection thresholds
CONFLICT_THRESHOLD = 25     # Points difference to flag conflict
CONFIDENCE_PENALTY = 15     # Penalty for conflicts


class DeterministicScorer:
    """
    Deterministic scoring engine.
    Produces unified bias from all inputs.
    """

    def __init__(self):
        self.weights = MASTER_WEIGHTS.copy()

    def set_weights(self, weights: Dict) -> None:
        """Override default weights"""
        self.weights.update(weights)

    def score_narrative(self, narrative: Dict) -> Dict:
        """
        Convert narrative data to score

        Args:
            narrative: Parsed narrative from Gemini

        Returns:
            Narrative score dict
        """
        if not narrative.get("parsed_success"):
            return {
                "score": 50,
                "confidence": 0,
                "available": False
            }

        # Get narrative summary
        summary = narrative.get("narrative_summary", {})
        sentiment = summary.get("sentiment", "neutral").lower()

        # Base score from sentiment
        if sentiment == "bullish":
            score = 70
        elif sentiment == "bearish":
            score = 30
        elif sentiment == "mixed":
            score = 50
        else:
            score = 50

        # Adjust by parse confidence
        meta = narrative.get("meta", {})
        parse_confidence = meta.get("parse_confidence", 50)

        # Check for contradictions
        contradictions = summary.get("contradictions", [])
        if len(contradictions) > 0:
            score = 50 + (score - 50) * 0.5  # Pull toward neutral
            parse_confidence -= len(contradictions) * 10

        return {
            "score": int(score),
            "confidence": max(0, min(100, parse_confidence)),
            "sentiment": sentiment,
            "contradictions": len(contradictions),
            "available": True
        }

    def score_events(self, events: List[Dict]) -> Dict:
        """
        Convert events to aggregated score

        Args:
            events: List of parsed events

        Returns:
            Events score dict
        """
        if not events:
            return {
                "score": 50,
                "confidence": 0,
                "available": False,
                "event_count": 0
            }

        bullish_impact = 0
        bearish_impact = 0
        total_importance = 0

        for event in events:
            importance_score = event.get("importance_score", 2)
            total_importance += importance_score

            # Check asset impact
            asset_impact = event.get("asset_impact", {})

            for asset, impact in asset_impact.items():
                if impact == "bullish":
                    bullish_impact += importance_score
                elif impact == "bearish":
                    bearish_impact += importance_score

        # Calculate net impact
        if total_importance > 0:
            net_impact = (bullish_impact - bearish_impact) / total_importance
        else:
            net_impact = 0

        # Convert to score (net_impact is -1 to +1)
        score = 50 + (net_impact * 30)  # Range: 20-80

        # Confidence based on event quality
        high_importance_count = sum(1 for e in events if e.get("importance_score", 0) >= 4)
        confidence = min(80, 30 + (high_importance_count * 15))

        return {
            "score": int(score),
            "confidence": confidence,
            "available": True,
            "event_count": len(events),
            "bullish_impact": bullish_impact,
            "bearish_impact": bearish_impact,
            "net_impact": net_impact
        }

    def score_macro(self, macro_context: Dict) -> Dict:
        """
        Convert macro context to score

        Args:
            macro_context: Macro overlay data

        Returns:
            Macro score dict
        """
        if not macro_context or not macro_context.get("is_event_day"):
            return {
                "score": 50,
                "confidence": 0,
                "available": False,
                "is_event_day": False
            }

        # Get event day bias
        bias = macro_context.get("event_bias", "neutral").lower()
        risk_tone = macro_context.get("risk_tone", "neutral").lower()

        # Score based on bias
        if bias == "bullish" or risk_tone == "risk_on":
            score = 65
        elif bias == "bearish" or risk_tone == "risk_off":
            score = 35
        else:
            score = 50

        # Adjust by event importance
        importance = macro_context.get("event_importance", "MEDIUM")
        if importance == "CRITICAL":
            confidence = 80
            # Amplify signal
            score = 50 + (score - 50) * 1.3
        elif importance == "HIGH":
            confidence = 65
        else:
            confidence = 40

        return {
            "score": int(min(85, max(15, score))),
            "confidence": confidence,
            "available": True,
            "is_event_day": True,
            "event_importance": importance,
            "risk_tone": risk_tone
        }

    def detect_conflicts(self, scores: Dict) -> List[Dict]:
        """
        Detect conflicts between scoring components

        Args:
            scores: Dict of all component scores

        Returns:
            List of conflict flags
        """
        conflicts = []

        pre_score = scores.get("pre_score", {}).get("score", 50)
        narrative_score = scores.get("narrative", {}).get("score", 50)
        events_score = scores.get("events", {}).get("score", 50)
        macro_score = scores.get("macro", {}).get("score", 50)

        # Check pre_score vs narrative conflict
        if scores.get("narrative", {}).get("available"):
            diff = abs(pre_score - narrative_score)
            if diff > CONFLICT_THRESHOLD:
                conflicts.append({
                    "type": "PRE_SCORE_VS_NARRATIVE",
                    "severity": "high" if diff > 35 else "medium",
                    "pre_score": pre_score,
                    "narrative_score": narrative_score,
                    "difference": diff
                })

        # Check quantitative vs qualitative conflict
        quant_avg = pre_score
        qual_scores = [s.get("score", 50) for k, s in scores.items()
                       if k != "pre_score" and s.get("available")]

        if qual_scores:
            qual_avg = sum(qual_scores) / len(qual_scores)
            diff = abs(quant_avg - qual_avg)
            if diff > CONFLICT_THRESHOLD:
                conflicts.append({
                    "type": "QUANT_VS_QUAL",
                    "severity": "high" if diff > 35 else "medium",
                    "quant_score": quant_avg,
                    "qual_score": qual_avg,
                    "difference": diff
                })

        # Check for extreme divergence
        all_scores = [pre_score]
        if scores.get("narrative", {}).get("available"):
            all_scores.append(narrative_score)
        if scores.get("events", {}).get("available"):
            all_scores.append(events_score)
        if scores.get("macro", {}).get("available"):
            all_scores.append(macro_score)

        if len(all_scores) >= 3:
            score_range = max(all_scores) - min(all_scores)
            if score_range > 40:
                conflicts.append({
                    "type": "EXTREME_DIVERGENCE",
                    "severity": "high",
                    "range": score_range,
                    "scores": all_scores
                })

        return conflicts

    def calculate_unified_score(
        self,
        pre_score: Dict,
        narrative: Dict = None,
        events: List[Dict] = None,
        macro_context: Dict = None
    ) -> Dict:
        """
        Calculate unified score from all inputs

        Args:
            pre_score: Pre-score engine output
            narrative: Parsed narrative from Gemini
            events: Parsed events list
            macro_context: Macro overlay data

        Returns:
            Unified scoring result
        """
        # Score each component
        scores = {
            "pre_score": {
                "score": pre_score.get("composite", {}).get("composite_score", 50),
                "confidence": pre_score.get("composite", {}).get("confidence", 50),
                "available": True
            },
            "narrative": self.score_narrative(narrative or {}),
            "events": self.score_events(events or []),
            "macro": self.score_macro(macro_context or {})
        }

        # Detect conflicts
        conflicts = self.detect_conflicts(scores)

        # Calculate weighted average
        total_weight = 0
        weighted_sum = 0
        weighted_confidence = 0

        for component, weight in self.weights.items():
            comp_scores = scores.get(component, {})
            if comp_scores.get("available"):
                comp_score = comp_scores.get("score", 50)
                comp_conf = comp_scores.get("confidence", 50)

                weighted_sum += comp_score * weight
                weighted_confidence += comp_conf * weight
                total_weight += weight

        # Normalize
        if total_weight > 0:
            unified_score = weighted_sum / total_weight
            base_confidence = weighted_confidence / total_weight
        else:
            unified_score = 50
            base_confidence = 30

        # Apply conflict penalty
        conflict_penalty = len(conflicts) * CONFIDENCE_PENALTY
        final_confidence = max(20, base_confidence - conflict_penalty)

        # Determine bias
        if unified_score >= 70:
            bias = "STRONG_BULLISH"
            signal = "STRONG"
        elif unified_score >= 60:
            bias = "BULLISH"
            signal = "MODERATE"
        elif unified_score >= 55:
            bias = "LEAN_BULLISH"
            signal = "WEAK"
        elif unified_score >= 45:
            bias = "NEUTRAL"
            signal = "NONE"
        elif unified_score >= 40:
            bias = "LEAN_BEARISH"
            signal = "WEAK"
        elif unified_score >= 30:
            bias = "BEARISH"
            signal = "MODERATE"
        else:
            bias = "STRONG_BEARISH"
            signal = "STRONG"

        # Direction for trading
        if unified_score > 55:
            direction = "LONG"
        elif unified_score < 45:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": pre_score.get("symbol", "UNKNOWN"),
            "unified_score": round(unified_score, 1),
            "unified_bias": bias,
            "direction": direction,
            "signal_strength": signal,
            "confidence": round(final_confidence, 1),
            "component_scores": scores,
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "weights_used": self.weights,
            "scoring_complete": True
        }

    def score_batch(
        self,
        pre_scores: List[Dict],
        narratives: Dict[str, Dict] = None,
        events_by_symbol: Dict[str, List[Dict]] = None,
        macro_context: Dict = None
    ) -> List[Dict]:
        """
        Score multiple assets

        Args:
            pre_scores: List of pre-score results
            narratives: Dict of symbol -> parsed narrative
            events_by_symbol: Dict of symbol -> events list
            macro_context: Shared macro context

        Returns:
            List of unified scoring results
        """
        results = []

        narratives = narratives or {}
        events_by_symbol = events_by_symbol or {}

        for pre_score in pre_scores:
            symbol = pre_score.get("symbol")

            unified = self.calculate_unified_score(
                pre_score=pre_score,
                narrative=narratives.get(symbol),
                events=events_by_symbol.get(symbol, []),
                macro_context=macro_context
            )

            results.append(unified)

        # Sort by signal strength and confidence
        results.sort(
            key=lambda x: (
                {"STRONG": 3, "MODERATE": 2, "WEAK": 1, "NONE": 0}.get(x["signal_strength"], 0),
                x["confidence"]
            ),
            reverse=True
        )

        return results
