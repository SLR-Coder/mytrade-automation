# engines/grok_scout.py
# -*- coding: utf-8 -*-
"""
Grok Scout Engine
=================
X (Twitter) and headline scanning for narrative detection.
Only runs on SHORTLISTED assets to minimize API costs.

Role:
- Scan allowlisted X accounts for narrative shifts
- Detect trending topics and sentiment changes
- Flag contradictions and urgency signals

Output: Structured JSON with narrative analysis
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("GrokScout")

# Default X accounts allowlist by category
DEFAULT_ALLOWLIST = {
    "whale_alerts": [
        "whale_alert",
        "lookonchain",
        "spotonchain"
    ],
    "analysts": [
        "CryptoQuant_Alert",
        "glaboratorybtc",
        "WClementeIII"
    ],
    "news": [
        "CoinDesk",
        "Cointelegraph",
        "TheBlock__"
    ],
    "projects": {
        "BTC": ["sabordo_btc", "BitcoinMagazine"],
        "ETH": ["VitalikButerin", "ethereum"],
        "SOL": ["solaboratory", "SolanaFloor"],
        "XRP": ["Ripple", "WrathofKahneman"],
    }
}

# Keywords for each asset
ASSET_KEYWORDS = {
    "BTC": ["bitcoin", "btc", "sats", "halving", "etf"],
    "ETH": ["ethereum", "eth", "layer2", "rollup", "eip"],
    "SOL": ["solana", "sol", "jito", "jupiter"],
    "XRP": ["xrp", "ripple", "sec", "lawsuit", "settlement"],
    "BNB": ["bnb", "binance", "cz"],
    "ADA": ["cardano", "ada", "vasil", "hydra"],
    "SUI": ["sui", "move", "mysten"],
    "TON": ["ton", "telegram", "toncoin"],
}


class GrokScout:
    """
    Grok-based X/news scanner.
    Uses Grok AI for narrative extraction from social signals.
    """

    def __init__(self, grok_api_key: Optional[str] = None):
        """
        Initialize Grok Scout

        Args:
            grok_api_key: Grok API key (uses env var if not provided)
        """
        self.api_key = grok_api_key or os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
        self.allowlist = DEFAULT_ALLOWLIST

    def load_allowlist(self, config_path: str = None) -> None:
        """Load custom allowlist from config file"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.allowlist = json.load(f)
            logger.info(f"Loaded allowlist from {config_path}")

    def get_accounts_for_asset(self, symbol: str) -> List[str]:
        """Get relevant X accounts for an asset"""
        accounts = []

        # Add general accounts
        accounts.extend(self.allowlist.get("whale_alerts", []))
        accounts.extend(self.allowlist.get("analysts", []))
        accounts.extend(self.allowlist.get("news", []))

        # Add asset-specific accounts
        clean_symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
        project_accounts = self.allowlist.get("projects", {}).get(clean_symbol, [])
        accounts.extend(project_accounts)

        return list(set(accounts))

    def get_keywords_for_asset(self, symbol: str) -> List[str]:
        """Get search keywords for an asset"""
        clean_symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
        return ASSET_KEYWORDS.get(clean_symbol, [clean_symbol.lower()])

    def build_scout_prompt(self, symbol: str, context: Dict = None) -> str:
        """
        Build prompt for Grok narrative scanning

        Args:
            symbol: Asset symbol
            context: Optional context (price, recent events)

        Returns:
            Structured prompt for Grok
        """
        clean_symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
        keywords = self.get_keywords_for_asset(symbol)
        accounts = self.get_accounts_for_asset(symbol)

        prompt = f"""Analyze recent X (Twitter) posts and news headlines for {clean_symbol}.

TARGET ACCOUNTS to check: {', '.join(accounts[:10])}
KEYWORDS to search: {', '.join(keywords)}

YOUR TASK:
1. Find the dominant narrative around {clean_symbol} in the last 4-12 hours
2. Detect any narrative SHIFT (change from previous sentiment)
3. Identify trending topics or recurring themes
4. Flag any contradictions between different sources
5. Note urgency signals (breaking news, sudden activity)

RESPOND IN JSON FORMAT ONLY:
{{
    "symbol": "{clean_symbol}",
    "narrative_direction": "bullish" | "bearish" | "neutral" | "mixed",
    "narrative_score": 0-100,
    "dominant_theme": "brief description of main narrative",
    "topic_clusters": ["topic1", "topic2"],
    "shift_detected": true | false,
    "shift_description": "what changed if shift detected",
    "contradiction_flags": ["flag1"] or [],
    "urgency_level": "low" | "medium" | "high",
    "urgency_reason": "reason if high urgency",
    "source_quality": "high" | "medium" | "low",
    "key_posts": [
        {{"account": "@handle", "summary": "brief summary", "sentiment": "bullish/bearish/neutral"}}
    ],
    "confidence": 0-100
}}
"""

        if context:
            prompt += f"\n\nCONTEXT:\n- Current price: ${context.get('price', 'N/A')}\n"
            prompt += f"- 24h change: {context.get('change_24h', 'N/A')}%\n"
            if context.get('pre_score'):
                prompt += f"- Pre-score bias: {context['pre_score'].get('bias', 'N/A')}\n"

        return prompt

    def scout_asset(self, symbol: str, context: Dict = None) -> Dict:
        """
        Scout narrative for a single asset using Grok

        Args:
            symbol: Asset symbol
            context: Optional context data

        Returns:
            Narrative analysis result
        """
        from utils.grok_wrapper import analyze_with_grok

        logger.info(f"Scouting narrative for {symbol}...")

        prompt = self.build_scout_prompt(symbol, context)

        try:
            # Call Grok API
            response = analyze_with_grok(prompt, max_tokens=1000)

            # Parse JSON response
            if response:
                # Try to extract JSON from response
                try:
                    # Find JSON in response
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response[json_start:json_end]
                        result = json.loads(json_str)
                        result["scout_success"] = True
                        result["timestamp"] = datetime.utcnow().isoformat()
                        return result
                except json.JSONDecodeError:
                    pass

                # Fallback: return raw response with parsing failure
                return {
                    "symbol": symbol,
                    "scout_success": False,
                    "raw_response": response,
                    "parse_error": "Failed to parse JSON from Grok response",
                    "timestamp": datetime.utcnow().isoformat()
                }

            return {
                "symbol": symbol,
                "scout_success": False,
                "error": "No response from Grok",
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Grok scout error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "scout_success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def scout_batch(self, shortlist: List[Dict]) -> Dict[str, Dict]:
        """
        Scout narratives for shortlisted assets

        Args:
            shortlist: List of shortlisted assets with context

        Returns:
            Dict mapping symbol to narrative result
        """
        results = {}

        for asset in shortlist:
            symbol = asset.get("symbol")
            context = {
                "price": asset.get("price"),
                "change_24h": asset.get("change_24h"),
                "pre_score": asset.get("composite", {})
            }

            results[symbol] = self.scout_asset(symbol, context)

        return results

    def summarize_market_narrative(self, scout_results: Dict[str, Dict]) -> Dict:
        """
        Summarize overall market narrative from all scout results

        Args:
            scout_results: Dict of symbol -> scout result

        Returns:
            Market-wide narrative summary
        """
        bullish_count = 0
        bearish_count = 0
        mixed_count = 0
        high_urgency = []
        shifts_detected = []

        for symbol, result in scout_results.items():
            if not result.get("scout_success"):
                continue

            direction = result.get("narrative_direction", "neutral")
            if direction == "bullish":
                bullish_count += 1
            elif direction == "bearish":
                bearish_count += 1
            elif direction == "mixed":
                mixed_count += 1

            if result.get("urgency_level") == "high":
                high_urgency.append({
                    "symbol": symbol,
                    "reason": result.get("urgency_reason", "Unknown")
                })

            if result.get("shift_detected"):
                shifts_detected.append({
                    "symbol": symbol,
                    "shift": result.get("shift_description", "Unknown shift")
                })

        total = bullish_count + bearish_count + mixed_count

        if total == 0:
            market_tone = "NO_DATA"
        elif bullish_count > bearish_count * 1.5:
            market_tone = "BULLISH_DOMINANT"
        elif bearish_count > bullish_count * 1.5:
            market_tone = "BEARISH_DOMINANT"
        elif mixed_count > total * 0.5:
            market_tone = "CONFUSED"
        else:
            market_tone = "BALANCED"

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "market_tone": market_tone,
            "bullish_assets": bullish_count,
            "bearish_assets": bearish_count,
            "mixed_assets": mixed_count,
            "high_urgency_alerts": high_urgency,
            "narrative_shifts": shifts_detected,
            "scout_coverage": total
        }
