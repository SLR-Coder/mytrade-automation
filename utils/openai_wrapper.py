# -*- coding: utf-8 -*-
"""
OpenAI GPT-4 API Wrapper
Provides trading signal analysis using GPT-4
"""

import time
import logging
from typing import Optional, Dict
from openai import OpenAI

from utils.secrets import get_secret

logger = logging.getLogger("OpenAI-Wrapper")


class OpenAIClient:
    """Wrapper for OpenAI GPT-4 API"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview"):
        """
        Initialize OpenAI client

        Args:
            api_key: OpenAI API key (if None, fetches from secrets)
            model: Model to use (default: gpt-4-turbo-preview)
        """
        self.api_key = api_key or get_secret("OPENAI_API_KEY")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"OpenAI client initialized with model: {model}")

    def analyze_market(
        self,
        market: str,
        price: float,
        indicators: Dict,
        news_sentiment: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """
        Get trading signal from GPT-4

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
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert financial analyst. Analyze market data and provide trading signals (BUY/SELL/HOLD) with confidence level (0-100) and brief reasoning."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for more consistent analysis
                    max_tokens=500
                )

                # Parse response
                content = response.choices[0].message.content
                result = self._parse_response(content, market)

                logger.info(f"GPT-4 analyzed {market}: {result['signal']} ({result['confidence']}%)")
                return result

            except Exception as e:
                logger.warning(f"GPT-4 attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"GPT-4 failed for {market} after {max_retries} attempts")
                    return None

    def _build_prompt(
        self,
        market: str,
        price: float,
        indicators: Dict,
        news_sentiment: Optional[str]
    ) -> str:
        """Build analysis prompt"""
        prompt = f"""Analyze {market} and provide a trading signal.

Current Price: ${price:,.2f}

Technical Indicators:
- RSI: {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- Bollinger Bands: Upper={indicators.get('bb_upper', 'N/A')}, Lower={indicators.get('bb_lower', 'N/A')}
- EMA 9: {indicators.get('ema_9', 'N/A')}
- EMA 21: {indicators.get('ema_21', 'N/A')}
- Trend: {indicators.get('trend', 'N/A')}
"""

        if news_sentiment:
            prompt += f"\nNews Sentiment: {news_sentiment}\n"

        prompt += """
Provide your analysis in this exact format:
SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [Brief explanation in 1-2 sentences]
"""
        return prompt

    def _parse_response(self, content: str, market: str) -> Dict:
        """Parse GPT-4 response into structured format"""
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
            "ai_model": "GPT-4"
        }


def get_openai_signal(market: str, price: float, indicators: Dict, news_sentiment: Optional[str] = None) -> Optional[Dict]:
    """
    Convenience function to get OpenAI trading signal

    Args:
        market: Market symbol
        price: Current price
        indicators: Technical indicators
        news_sentiment: Optional news sentiment

    Returns:
        Signal dict or None
    """
    try:
        client = OpenAIClient()
        return client.analyze_market(market, price, indicators, news_sentiment)
    except Exception as e:
        logger.error(f"OpenAI wrapper failed: {e}")
        return None