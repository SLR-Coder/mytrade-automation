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

    def __init__(self, api_key: Optional[str] = None, model: str = "o3"):
        """
        Initialize OpenAI client

        Args:
            api_key: OpenAI API key (if None, fetches from secrets)
            model: Model to use (default: o3 - en güçlü OpenAI modeli)
                   Alternatifler: o3-mini (ucuz), gpt-4-turbo (eski)
        """
        self.api_key = api_key or get_secret("OPENAI_API_KEY", required=False)
        self.model = model
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        if self.client:
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
                    # Note: o3 model only supports default temperature (1.0)
                    max_completion_tokens=500  # o3 model requires max_completion_tokens instead of max_tokens
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
        """Analiz prompt'u oluştur"""
        prompt = f"""{market} piyasasını analiz et ve işlem sinyali ver.

Mevcut Fiyat: ${price:,.2f}

Teknik Göstergeler:
- RSI: {indicators.get('rsi', 'Yok')}
- MACD: {indicators.get('macd', 'Yok')}
- MACD Sinyali: {indicators.get('macd_signal', 'Yok')}
- Bollinger Bantları: Üst={indicators.get('bb_upper', 'Yok')}, Alt={indicators.get('bb_lower', 'Yok')}
- EMA 9: {indicators.get('ema_9', 'Yok')}
- EMA 21: {indicators.get('ema_21', 'Yok')}
- Eğilim: {indicators.get('trend', 'Yok')}
"""

        if news_sentiment:
            prompt += f"\nHaber Duyarlılığı: {news_sentiment}\n"

        prompt += """
Analizini tam olarak şu formatta ver:
SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [1-2 cümlelik kısa açıklama - TÜRKÇE yaz]
"""
        return prompt

    def _parse_response(self, content: str, market: str) -> Dict:
        """GPT-4 yanıtını yapılandırılmış formata dönüştür"""
        lines = content.strip().split('\n')

        signal = "HOLD"
        confidence = 50
        reasoning = "Yanıt ayrıştırılamadı"

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