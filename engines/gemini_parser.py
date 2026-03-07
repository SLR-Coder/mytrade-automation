# engines/gemini_parser.py
# -*- coding: utf-8 -*-
"""
Gemini Parser Engine
====================
Normalizes raw text and events to structured JSON.
Standardizes output from Grok Scout and external sources.

Role:
- Parse and clean raw narrative data
- Classify events (listing, unlock, exploit, ETF, etc.)
- Assign importance and urgency labels
- Map to affected assets

Output: Standardized event JSON with consistent schema
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("GeminiParser")

# Event type classifications
EVENT_TYPES = {
    "crypto": [
        "LISTING",          # New exchange listing
        "DELISTING",        # Exchange delisting
        "UNLOCK",           # Token unlock
        "AIRDROP",          # Airdrop announcement
        "EXPLOIT",          # Security exploit
        "UPGRADE",          # Protocol upgrade
        "PARTNERSHIP",      # Partnership announcement
        "ETF",              # ETF related news
        "REGULATION",       # Regulatory news
        "TREASURY",         # Treasury/buyback
        "BURN",             # Token burn
        "STAKING",          # Staking changes
        "WHALE_MOVE",       # Large wallet movement
    ],
    "macro": [
        "CPI",              # Consumer Price Index
        "NFP",              # Non-Farm Payrolls
        "FOMC",             # Fed meeting/decision
        "GDP",              # GDP data
        "PMI",              # PMI data
        "RETAIL_SALES",     # Retail sales
        "JOBLESS_CLAIMS",   # Unemployment claims
        "FED_SPEAK",        # Fed official speech
        "ECB",              # ECB decision
        "BOJ",              # BOJ decision
        "BOE",              # BOE decision
        "GEOPOLITICAL",     # Geopolitical event
        "ENERGY",           # Oil/gas news
    ]
}

# Importance levels
IMPORTANCE_LEVELS = {
    "CRITICAL": 5,      # Market-moving event
    "HIGH": 4,          # Significant impact
    "MEDIUM": 3,        # Notable
    "LOW": 2,           # Minor
    "NOISE": 1          # Likely noise
}


class GeminiParser:
    """
    Gemini-based parser for normalizing raw data to structured JSON.
    """

    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize Gemini Parser

        Args:
            gemini_api_key: Gemini API key
        """
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY")

    def build_parse_prompt(self, raw_data: Dict, data_type: str = "narrative") -> str:
        """
        Build prompt for Gemini parsing

        Args:
            raw_data: Raw data to parse
            data_type: Type of data (narrative, event, headline)

        Returns:
            Structured prompt for Gemini
        """
        event_types_str = ", ".join(EVENT_TYPES["crypto"] + EVENT_TYPES["macro"])

        prompt = f"""Parse and normalize the following raw data into structured JSON format.

DATA TYPE: {data_type}
RAW DATA:
{json.dumps(raw_data, indent=2, default=str)}

YOUR TASK:
1. Extract key information and normalize to standard fields
2. Classify any events by type: {event_types_str}
3. Assign importance level: CRITICAL, HIGH, MEDIUM, LOW, or NOISE
4. Identify affected assets (symbols)
5. Determine urgency and time sensitivity

RESPOND IN JSON FORMAT ONLY:
{{
    "parsed_success": true,
    "data_type": "{data_type}",
    "timestamp": "ISO timestamp",
    "events": [
        {{
            "event_type": "EVENT_TYPE from list",
            "headline": "brief headline",
            "description": "detailed description",
            "importance": "CRITICAL/HIGH/MEDIUM/LOW/NOISE",
            "importance_score": 1-5,
            "urgency": "immediate/hours/days/weeks",
            "affected_assets": ["BTC", "ETH"],
            "asset_impact": {{
                "BTC": "bullish/bearish/neutral",
                "ETH": "bullish/bearish/neutral"
            }},
            "source": "source name",
            "source_reliability": "high/medium/low",
            "time_context": "when this is relevant"
        }}
    ],
    "narrative_summary": {{
        "dominant_theme": "main theme if narrative",
        "sentiment": "bullish/bearish/neutral/mixed",
        "key_points": ["point1", "point2"],
        "contradictions": ["any contradictions noted"]
    }},
    "meta": {{
        "parse_confidence": 0-100,
        "data_quality": "high/medium/low",
        "missing_info": ["any missing information"]
    }}
}}
"""
        return prompt

    def parse_narrative(self, grok_output: Dict) -> Dict:
        """
        Parse Grok scout output to normalized format

        Args:
            grok_output: Raw output from Grok Scout

        Returns:
            Normalized narrative data
        """
        from utils.gemini_wrapper import analyze_with_gemini

        if not grok_output.get("scout_success"):
            return {
                "parsed_success": False,
                "error": "Invalid Grok output",
                "raw_input": grok_output
            }

        prompt = self.build_parse_prompt(grok_output, "narrative")

        try:
            response = analyze_with_gemini(prompt, max_tokens=1500)

            if response:
                try:
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        result = json.loads(response[json_start:json_end])
                        result["parsed_success"] = True
                        result["parse_timestamp"] = datetime.utcnow().isoformat()
                        result["original_symbol"] = grok_output.get("symbol")
                        return result
                except json.JSONDecodeError:
                    pass

            return {
                "parsed_success": False,
                "error": "Failed to parse Gemini response",
                "raw_response": response,
                "original_symbol": grok_output.get("symbol")
            }

        except Exception as e:
            logger.error(f"Gemini parse error: {e}")
            return {
                "parsed_success": False,
                "error": str(e),
                "original_symbol": grok_output.get("symbol")
            }

    def parse_headline(self, headline: str, source: str = "unknown") -> Dict:
        """
        Parse a single headline to structured event

        Args:
            headline: News headline text
            source: Source of headline

        Returns:
            Structured event data
        """
        raw_data = {
            "headline": headline,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }

        return self.parse_raw_event(raw_data, "headline")

    def parse_raw_event(self, raw_data: Dict, data_type: str = "event") -> Dict:
        """
        Parse raw event data to structured format

        Args:
            raw_data: Raw event data
            data_type: Type of data

        Returns:
            Structured event data
        """
        from utils.gemini_wrapper import analyze_with_gemini

        prompt = self.build_parse_prompt(raw_data, data_type)

        try:
            response = analyze_with_gemini(prompt, max_tokens=1000)

            if response:
                try:
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        result = json.loads(response[json_start:json_end])
                        result["parsed_success"] = True
                        result["parse_timestamp"] = datetime.utcnow().isoformat()
                        return result
                except json.JSONDecodeError:
                    pass

            return {
                "parsed_success": False,
                "error": "Parse failed",
                "raw_data": raw_data
            }

        except Exception as e:
            logger.error(f"Gemini parse error: {e}")
            return {
                "parsed_success": False,
                "error": str(e),
                "raw_data": raw_data
            }

    def parse_batch_narratives(self, scout_results: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Parse multiple Grok scout results

        Args:
            scout_results: Dict of symbol -> scout result

        Returns:
            Dict of symbol -> parsed result
        """
        parsed = {}

        for symbol, scout_output in scout_results.items():
            logger.info(f"Parsing narrative for {symbol}...")
            parsed[symbol] = self.parse_narrative(scout_output)

        return parsed

    def extract_events_from_parsed(self, parsed_results: Dict[str, Dict]) -> List[Dict]:
        """
        Extract all events from parsed results

        Args:
            parsed_results: Dict of symbol -> parsed result

        Returns:
            List of all extracted events
        """
        all_events = []

        for symbol, parsed in parsed_results.items():
            if not parsed.get("parsed_success"):
                continue

            events = parsed.get("events", [])
            for event in events:
                event["source_symbol"] = symbol
                all_events.append(event)

        # Sort by importance
        all_events.sort(
            key=lambda x: IMPORTANCE_LEVELS.get(x.get("importance", "LOW"), 2),
            reverse=True
        )

        return all_events

    def filter_high_importance_events(self, events: List[Dict], min_importance: str = "MEDIUM") -> List[Dict]:
        """
        Filter events by minimum importance level

        Args:
            events: List of events
            min_importance: Minimum importance level

        Returns:
            Filtered list of events
        """
        min_score = IMPORTANCE_LEVELS.get(min_importance, 3)

        return [
            e for e in events
            if e.get("importance_score", 2) >= min_score
        ]
