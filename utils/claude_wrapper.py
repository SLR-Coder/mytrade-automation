# -*- coding: utf-8 -*-
"""
Anthropic Claude API Wrapper
Provides trading signal analysis using Claude Opus 4
"""

import time
import logging
from typing import Optional, Dict
from anthropic import Anthropic

from utils.secrets import get_secret

logger = logging.getLogger("Claude-Wrapper")


class ClaudeClient:
    """Wrapper for Anthropic Claude API"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-20250514"):
        """
        Initialize Claude client

        Args:
            api_key: Anthropic API key (if None, fetches from secrets)
            model: Model to use (default: claude-opus-4)
        """
        self.api_key = api_key or get_secret("ANTHROPIC_API_KEY")
        self.model = model
        self.client = Anthropic(api_key=self.api_key)
        logger.info(f"Claude client initialized with model: {model}")

    def analyze_market(
        self,
        market: str,
        price: float,
        indicators: Dict,
        news_sentiment: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """
        Get trading signal from Claude

        Args:
            market: Market symbol (e.g., "BTC/USDT")
            price: Current price
            indicators: Technical indicators dict
            news_sentiment: Optional news sentiment
            max_retries: Number of retry attempts

        Returns:
            Dict with signal, confidence, reasoning
        """
        prompt = self._build_prompt(market, price, indicators, news_sentiment)

        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    temperature=0.3,  # Lower temperature for consistency
                    system="You are an expert financial analyst with deep knowledge of technical analysis, market psychology, and risk management. Analyze market data and provide trading signals (BUY/SELL/HOLD) with confidence level (0-100) and detailed reasoning.",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                # Parse response
                content = response.content[0].text
                result = self._parse_response(content, market)

                logger.info(f"Claude analyzed {market}: {result['signal']} ({result['confidence']}%)")
                return result

            except Exception as e:
                logger.warning(f"Claude attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Claude failed for {market} after {max_retries} attempts")
                    return None

    def _build_prompt(
        self,
        market: str,
        price: float,
        indicators: Dict,
        news_sentiment: Optional[str]
    ) -> str:
        """Build analysis prompt"""
        prompt = f"""Analyze {market} and provide a comprehensive trading signal.

Current Price: ${price:,.2f}

Technical Indicators:
- RSI: {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- MACD Histogram: {indicators.get('macd_histogram', 'N/A')}
- Bollinger Bands: Upper={indicators.get('bb_upper', 'N/A')}, Middle={indicators.get('bb_middle', 'N/A')}, Lower={indicators.get('bb_lower', 'N/A')}
- EMA 9: {indicators.get('ema_9', 'N/A')}
- EMA 21: {indicators.get('ema_21', 'N/A')}
- EMA 50: {indicators.get('ema_50', 'N/A')}
- EMA 200: {indicators.get('ema_200', 'N/A')}
- Support Level: {indicators.get('support_levels', ['N/A'])[0] if indicators.get('support_levels') else 'N/A'}
- Resistance Level: {indicators.get('resistance_levels', ['N/A'])[0] if indicators.get('resistance_levels') else 'N/A'}
- Trend: {indicators.get('trend', 'N/A')}
"""

        if news_sentiment:
            prompt += f"\nNews Sentiment: {news_sentiment}\n"

        prompt += """
Based on this data, provide your trading recommendation in this exact format:

SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [Your detailed analysis in 2-3 sentences, considering technical indicators, trend, and risk factors]
"""
        return prompt

    def _parse_response(self, content: str, market: str) -> Dict:
        """Parse Claude response into structured format"""
        lines = content.strip().split('\n')

        signal = "HOLD"
        confidence = 50
        reasoning = "Unable to parse response"

        for line in lines:
            line = line.strip()
            if line.startswith("SIGNAL:"):
                signal = line.split(":", 1)[1].strip().upper()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = int(line.split(":", 1)[1].strip().split()[0])
                except:
                    confidence = 50
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        return {
            "market": market,
            "signal": signal,
            "confidence": confidence,
            "reasoning": reasoning,
            "ai_model": "Claude-Opus-4"
        }


def get_claude_signal(market: str, price: float, indicators: Dict, news_sentiment: Optional[str] = None) -> Optional[Dict]:
    """
    Convenience function to get Claude trading signal

    Args:
        market: Market symbol
        price: Current price
        indicators: Technical indicators
        news_sentiment: Optional news sentiment

    Returns:
        Signal dict or None
    """
    try:
        client = ClaudeClient()
        return client.analyze_market(market, price, indicators, news_sentiment)
    except Exception as e:
        logger.error(f"Claude wrapper failed: {e}")
        return None