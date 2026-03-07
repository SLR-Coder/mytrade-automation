# engines/commander.py
# -*- coding: utf-8 -*-
"""
GPT Commander Engine
====================
Final synthesis and message generation.
Does NOT replace deterministic scoring - only formats output.

Role:
- Read deterministic scores and all inputs
- Generate human-readable summary
- Create Telegram-ready messages
- Add risk warnings where appropriate

Output:
- Unified Bias message
- Top 4 NOW + Next 2 summary
- Risk warnings
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("Commander")


class Commander:
    """
    GPT-based commander for final synthesis.
    Creates readable output from deterministic scores.
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize Commander

        Args:
            openai_api_key: OpenAI API key
        """
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

    def build_synthesis_prompt(self, unified_score: Dict, context: Dict = None) -> str:
        """
        Build prompt for final synthesis

        Args:
            unified_score: Deterministic scorer output
            context: Additional context

        Returns:
            Synthesis prompt
        """
        symbol = unified_score.get("symbol", "UNKNOWN")
        bias = unified_score.get("unified_bias", "NEUTRAL")
        direction = unified_score.get("direction", "NEUTRAL")
        confidence = unified_score.get("confidence", 50)
        conflicts = unified_score.get("conflicts", [])

        prompt = f"""You are the final synthesizer for a trading signal system.
Your job is to create a BRIEF, CLEAR summary for traders.

ASSET: {symbol}
UNIFIED BIAS: {bias}
DIRECTION: {direction}
CONFIDENCE: {confidence}%

COMPONENT SCORES:
{json.dumps(unified_score.get("component_scores", {}), indent=2)}

CONFLICTS DETECTED: {len(conflicts)}
{json.dumps(conflicts, indent=2) if conflicts else "None"}

YOUR TASK:
1. Write a 2-3 sentence summary explaining the signal
2. Highlight the KEY DRIVER (what's causing this signal)
3. Note any RISK or CAUTION if conflicts exist
4. Do NOT invent data - only use what's provided

RESPOND IN JSON FORMAT:
{{
    "summary": "2-3 sentence summary for traders",
    "key_driver": "main factor driving this signal",
    "risk_warning": "warning if applicable, null otherwise",
    "action_hint": "ENTER/WAIT/AVOID",
    "confidence_note": "brief note on confidence level"
}}
"""

        if context:
            prompt += f"\n\nADDITIONAL CONTEXT:\n{json.dumps(context, indent=2)}"

        return prompt

    def synthesize(self, unified_score: Dict, context: Dict = None) -> Dict:
        """
        Generate final synthesis for a single asset

        Args:
            unified_score: Deterministic scorer output
            context: Additional context

        Returns:
            Synthesis result
        """
        from utils.openai_wrapper import analyze_with_gpt

        prompt = self.build_synthesis_prompt(unified_score, context)

        try:
            response = analyze_with_gpt(prompt, max_tokens=500)

            if response:
                try:
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        result = json.loads(response[json_start:json_end])
                        result["synthesis_success"] = True
                        result["timestamp"] = datetime.utcnow().isoformat()
                        result["symbol"] = unified_score.get("symbol")
                        result["unified_bias"] = unified_score.get("unified_bias")
                        result["confidence"] = unified_score.get("confidence")
                        return result
                except json.JSONDecodeError:
                    pass

            # Fallback: generate basic synthesis without GPT
            return self._fallback_synthesis(unified_score)

        except Exception as e:
            logger.error(f"Commander synthesis error: {e}")
            return self._fallback_synthesis(unified_score)

    def _fallback_synthesis(self, unified_score: Dict) -> Dict:
        """Generate basic synthesis without GPT"""
        symbol = unified_score.get("symbol", "UNKNOWN")
        bias = unified_score.get("unified_bias", "NEUTRAL")
        confidence = unified_score.get("confidence", 50)
        direction = unified_score.get("direction", "NEUTRAL")
        conflicts = unified_score.get("conflicts", [])

        # Generate basic summary
        if bias in ["STRONG_BULLISH", "BULLISH"]:
            summary = f"{symbol} shows bullish signals with {confidence:.0f}% confidence."
            action = "ENTER" if confidence > 70 else "WAIT"
        elif bias in ["STRONG_BEARISH", "BEARISH"]:
            summary = f"{symbol} shows bearish signals with {confidence:.0f}% confidence."
            action = "ENTER" if confidence > 70 else "WAIT"
        else:
            summary = f"{symbol} is neutral. No clear directional signal."
            action = "AVOID"

        # Key driver from component scores
        comp_scores = unified_score.get("component_scores", {})
        drivers = []
        for comp, data in comp_scores.items():
            if data.get("available") and abs(data.get("score", 50) - 50) > 15:
                drivers.append(comp)

        key_driver = ", ".join(drivers) if drivers else "Mixed signals"

        # Risk warning
        risk_warning = None
        if len(conflicts) > 0:
            risk_warning = f"{len(conflicts)} conflict(s) detected - exercise caution"

        return {
            "synthesis_success": True,
            "fallback": True,
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "unified_bias": bias,
            "confidence": confidence,
            "summary": summary,
            "key_driver": key_driver,
            "risk_warning": risk_warning,
            "action_hint": action,
            "confidence_note": f"Confidence: {confidence:.0f}%"
        }

    def generate_top_summary(self, unified_scores: List[Dict]) -> Dict:
        """
        Generate Top 4 NOW + Next 2 summary

        Args:
            unified_scores: List of unified scores (sorted by priority)

        Returns:
            Top summary dict
        """
        # Separate by direction
        longs = [s for s in unified_scores if s.get("direction") == "LONG"]
        shorts = [s for s in unified_scores if s.get("direction") == "SHORT"]
        neutrals = [s for s in unified_scores if s.get("direction") == "NEUTRAL"]

        # Select Top 4 NOW
        top_now = []

        # Take best longs
        top_now.extend(longs[:2])

        # Take best shorts
        top_now.extend(shorts[:2])

        # Fill if needed
        if len(top_now) < 4:
            remaining = [s for s in unified_scores if s not in top_now]
            top_now.extend(remaining[:4 - len(top_now)])

        top_now = top_now[:4]

        # Select Next 2
        used_symbols = {t["symbol"] for t in top_now}
        remaining = [s for s in unified_scores if s["symbol"] not in used_symbols]
        next_two = remaining[:2]

        # Calculate market sentiment
        total = len(unified_scores)
        bullish_count = len([s for s in unified_scores if "BULLISH" in s.get("unified_bias", "")])
        bearish_count = len([s for s in unified_scores if "BEARISH" in s.get("unified_bias", "")])

        if bullish_count > bearish_count * 1.5:
            market_tone = "RISK_ON"
        elif bearish_count > bullish_count * 1.5:
            market_tone = "RISK_OFF"
        else:
            market_tone = "MIXED"

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "top_now": [self._format_top_entry(s) for s in top_now],
            "next_candidates": [self._format_top_entry(s) for s in next_two],
            "market_tone": market_tone,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "total_analyzed": total
        }

    def _format_top_entry(self, score: Dict) -> Dict:
        """Format entry for top summary"""
        return {
            "symbol": score.get("symbol"),
            "bias": score.get("unified_bias"),
            "direction": score.get("direction"),
            "confidence": score.get("confidence"),
            "signal_strength": score.get("signal_strength"),
            "conflict_count": score.get("conflict_count", 0)
        }

    def format_telegram_message(self, synthesis: Dict, include_details: bool = False) -> str:
        """
        Format synthesis for Telegram

        Args:
            synthesis: Synthesis result
            include_details: Include detailed breakdown

        Returns:
            Telegram-formatted message
        """
        symbol = synthesis.get("symbol", "UNKNOWN")
        bias = synthesis.get("unified_bias", "NEUTRAL")
        confidence = synthesis.get("confidence", 50)
        summary = synthesis.get("summary", "")
        key_driver = synthesis.get("key_driver", "")
        risk_warning = synthesis.get("risk_warning")
        action = synthesis.get("action_hint", "WAIT")

        # Emoji mapping
        if "BULLISH" in bias:
            emoji = "🟢" if "STRONG" in bias else "🔵"
            direction_emoji = "📈"
        elif "BEARISH" in bias:
            emoji = "🔴" if "STRONG" in bias else "🟠"
            direction_emoji = "📉"
        else:
            emoji = "⚪"
            direction_emoji = "➡️"

        # Action emoji
        action_emoji = {"ENTER": "✅", "WAIT": "⏳", "AVOID": "❌"}.get(action, "❓")

        message = f"{emoji} <b>{symbol}</b> - {bias}\n"
        message += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"{direction_emoji} <b>Özet:</b> {summary}\n\n"
        message += f"🎯 <b>Ana Faktör:</b> {key_driver}\n"
        message += f"📊 <b>Güven:</b> %{confidence:.0f}\n"
        message += f"{action_emoji} <b>Aksiyon:</b> {action}\n"

        if risk_warning:
            message += f"\n⚠️ <b>Risk:</b> {risk_warning}\n"

        return message

    def format_top_summary_message(self, top_summary: Dict) -> str:
        """
        Format Top 4 + Next 2 summary for Telegram

        Args:
            top_summary: Top summary from generate_top_summary

        Returns:
            Telegram-formatted message
        """
        market_tone = top_summary.get("market_tone", "MIXED")
        tone_emoji = {"RISK_ON": "🟢", "RISK_OFF": "🔴", "MIXED": "🟡"}.get(market_tone, "⚪")

        message = f"🎯 <b>TOP 4 NOW + NEXT 2</b>\n"
        message += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"{tone_emoji} Piyasa Tonu: <b>{market_tone}</b>\n\n"

        message += f"<b>🔥 TOP 4 NOW:</b>\n"
        for i, entry in enumerate(top_summary.get("top_now", []), 1):
            direction_emoji = "📈" if entry["direction"] == "LONG" else "📉" if entry["direction"] == "SHORT" else "➡️"
            message += f"{i}. {direction_emoji} <b>{entry['symbol']}</b> - {entry['bias']} (%{entry['confidence']:.0f})\n"

        message += f"\n<b>👀 NEXT 2:</b>\n"
        for entry in top_summary.get("next_candidates", []):
            direction_emoji = "📈" if entry["direction"] == "LONG" else "📉" if entry["direction"] == "SHORT" else "➡️"
            message += f"• {direction_emoji} {entry['symbol']} - {entry['bias']}\n"

        message += f"\n📊 Analiz: {top_summary.get('total_analyzed', 0)} varlık"

        return message
