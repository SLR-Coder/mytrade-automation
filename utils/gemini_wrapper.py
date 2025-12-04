# utils/gemini_wrapper.py
# -*- coding: utf-8 -*-
"""
Google Gemini AI Wrapper
Model: Gemini 2.0 Flash Thinking - Fast reasoning model
"""

import time
import logging
from typing import Dict, Optional
import google.generativeai as genai

from utils.secrets import get_secret

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiWrapper")


class GeminiClient:
    """
    Gemini AI client for trading signal analysis

    Uses Gemini 2.0 Flash Thinking for fast, efficient analysis
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client

        Args:
            api_key: Gemini API key (if None, fetches from secrets)
        """
        if api_key is None:
            api_key = get_secret("GEMINI_API_KEY", required=False)

        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-pro")

    def analyze_market(
        self,
        market: str,
        price: float,
        indicators: Dict,
        news_sentiment: Optional[str] = None,
        max_retries: int = 2
    ) -> Optional[Dict]:
        """
        Analyze market and return trading signal

        Args:
            market: Market symbol
            price: Current price
            indicators: Technical indicators
            news_sentiment: Optional news sentiment
            max_retries: Number of retry attempts

        Returns:
            Signal dict with signal/confidence/reasoning
        """
        prompt = self._build_prompt(market, price, indicators, news_sentiment)

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                text = response.text

                # Parse response
                result = self._parse_response(text)
                if result:
                    logger.info(f"Gemini analyzed {market}: {result['signal']} ({result['confidence']}%)")
                    return result

            except Exception as e:
                logger.warning(f"Gemini deneme {attempt + 1}/{max_retries} başarısız: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        logger.error(f"Gemini {max_retries} denemeden sonra {market} için başarısız oldu")
        return None

    def _build_prompt(self, market: str, price: float, indicators: Dict, news_sentiment: Optional[str] = None) -> str:
        """Build analysis prompt"""

        prompt = f"""Sen profesyonel bir kripto ve forex trading analistisin.

Piyasa: {market}
Mevcut Fiyat: ${price:,.2f}

Teknik Göstergeler:
"""

        # Add technical indicators
        if indicators.get('rsi'):
            prompt += f"- RSI: {indicators['rsi']:.2f}\n"
        if indicators.get('macd'):
            prompt += f"- MACD: {indicators['macd']:.4f}\n"
        if indicators.get('macd_signal'):
            prompt += f"- MACD Sinyal: {indicators['macd_signal']:.4f}\n"
        if indicators.get('macd_histogram'):
            prompt += f"- MACD Histogram: {indicators['macd_histogram']:.4f}\n"

        if indicators.get('bb_upper') and indicators.get('bb_lower'):
            prompt += f"- Bollinger Bandı: ${indicators['bb_lower']:.2f} - ${indicators['bb_upper']:.2f}\n"

        if indicators.get('ema_9'):
            prompt += f"- EMA 9: ${indicators['ema_9']:.2f}\n"
        if indicators.get('ema_21'):
            prompt += f"- EMA 21: ${indicators['ema_21']:.2f}\n"
        if indicators.get('ema_50'):
            prompt += f"- EMA 50: ${indicators['ema_50']:.2f}\n"
        if indicators.get('ema_200'):
            prompt += f"- EMA 200: ${indicators['ema_200']:.2f}\n"

        support = indicators.get('support_levels', [])
        resistance = indicators.get('resistance_levels', [])
        if support:
            prompt += f"- Destek: ${support[0]:.2f}\n"
        if resistance:
            prompt += f"- Direnç: ${resistance[0]:.2f}\n"
        if indicators.get('trend'):
            prompt += f"- Eğilim: {indicators['trend']}\n"

        if news_sentiment:
            prompt += f"\nHaber Duyarlılığı: {news_sentiment}\n"

        prompt += """

Bu piyasayı analiz et ve şu formatta cevap ver:

SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100 arası sayı]
REASONING: [2-3 cümle TÜRKÇE açıklama - teknik göstergelere dayalı]

ÖNEMLİ: Sadece bu formatı kullan, başka açıklama ekleme!
"""

        return prompt

    def _parse_response(self, text: str) -> Optional[Dict]:
        """Parse AI response"""
        try:
            import re

            lines = text.strip().split('\n')

            signal = None
            confidence = None
            reasoning = ""

            for line in lines:
                line = line.strip()

                if line.startswith("SIGNAL:"):
                    signal_text = line.split("SIGNAL:")[1].strip().upper()
                    if "BUY" in signal_text:
                        signal = "BUY"
                    elif "SELL" in signal_text:
                        signal = "SELL"
                    elif "HOLD" in signal_text:
                        signal = "HOLD"

                elif line.startswith("CONFIDENCE:"):
                    conf_text = line.split("CONFIDENCE:")[1].strip()
                    match = re.search(r'\d+', conf_text)
                    if match:
                        confidence = int(match.group())

                elif line.startswith("REASONING:"):
                    reasoning = line.split("REASONING:")[1].strip()
                elif reasoning and line and not line.startswith(("SIGNAL:", "CONFIDENCE:")):
                    reasoning += " " + line

            if not signal or confidence is None:
                logger.warning(f"Gemini parse başarısız: {text[:200]}")
                return None

            return {
                "signal": signal,
                "confidence": min(100, max(0, confidence)),
                "reasoning": reasoning.strip()
            }

        except Exception as e:
            logger.error(f"Gemini parse hatası: {e}")
            return None


def get_gemini_signal(market: str, price: float, indicators: Dict) -> Optional[Dict]:
    """
    Wrapper function for Gemini signal generation

    Args:
        market: Market symbol
        price: Current price
        indicators: Technical indicators

    Returns:
        Signal dict or None
    """
    try:
        client = GeminiClient()
        return client.analyze_market(market, price, indicators)
    except Exception as e:
        logger.error(f"Gemini client error: {e}")
        return None
