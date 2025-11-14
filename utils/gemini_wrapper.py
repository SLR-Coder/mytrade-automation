# -*- coding: utf-8 -*-
"""
Google Gemini API Wrapper
Provides trading signal analysis using Gemini 2.5 Pro
"""

import time
import logging
from typing import Optional, Dict
import google.generativeai as genai

from utils.secrets import get_secret

logger = logging.getLogger("Gemini-Wrapper")


class GeminiClient:
    """Wrapper for Google Gemini API"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-exp"):
        """
        Initialize Gemini client

        Args:
            api_key: Google API key (if None, fetches from secrets)
            model: Model to use (default: gemini-2.0-flash-exp, less strict safety filters)
        """
        self.api_key = api_key or get_secret("GEMINI_API_KEY")
        self.model_name = model

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Generation config
        self.generation_config = {
            "temperature": 0.3,  # Lower temperature for consistent analysis
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
        }

        # Safety settings (permissive for financial analysis)
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            system_instruction="You are an expert quantitative analyst and trader with expertise in technical analysis, market microstructure, and algorithmic trading. Analyze market data and provide precise trading signals (BUY/SELL/HOLD) with confidence levels and comprehensive reasoning."
        )

        logger.info(f"Gemini client initialized with model: {model}")

    def analyze_market(
        self,
        market: str,
        price: float,
        indicators: Dict,
        news_sentiment: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """
        Get trading signal from Gemini

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
                # Start chat session
                chat = self.model.start_chat(history=[])

                # Send message
                response = chat.send_message(prompt)

                # Check if response was blocked by safety filters
                if not response.candidates or not response.candidates[0].content.parts:
                    logger.warning(f"Gemini blocked response for {market} (safety filter)")
                    # Return a default HOLD signal when blocked
                    return {
                        "signal": "HOLD",
                        "confidence": 50,
                        "reasoning": "Gemini güvenlik filtreleri nedeniyle analiz yapılamadı. Varsayılan: HOLD"
                    }

                # Parse response
                content = response.text
                result = self._parse_response(content, market)

                logger.info(f"Gemini analyzed {market}: {result['signal']} ({result['confidence']}%)")
                return result

            except Exception as e:
                logger.warning(f"Gemini attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Gemini failed for {market} after {max_retries} attempts")
                    # Return default HOLD on complete failure
                    return {
                        "signal": "HOLD",
                        "confidence": 50,
                        "reasoning": f"Gemini API hatası: {str(e)[:100]}"
                    }

    def _build_prompt(
        self,
        market: str,
        price: float,
        indicators: Dict,
        news_sentiment: Optional[str]
    ) -> str:
        """Build analysis prompt"""
        prompt = f"""{market} piyasasını al/sat fırsatları için analiz et.

**Güncel Piyasa Durumu:**
- Fiyat: ${price:,.2f}

**Teknik Göstergeler:**
- RSI: {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- MACD Histogram: {indicators.get('macd_histogram', 'N/A')}
- Bollinger Bantları:
  - Üst: {indicators.get('bb_upper', 'N/A')}
  - Orta: {indicators.get('bb_middle', 'N/A')}
  - Alt: {indicators.get('bb_lower', 'N/A')}
- EMA'lar:
  - EMA 9: {indicators.get('ema_9', 'N/A')}
  - EMA 21: {indicators.get('ema_21', 'N/A')}
  - EMA 50: {indicators.get('ema_50', 'N/A')}
  - EMA 200: {indicators.get('ema_200', 'N/A')}
- Destek Seviyesi: {indicators.get('support_levels', ['N/A'])[0] if indicators.get('support_levels') else 'N/A'}
- Direnç Seviyesi: {indicators.get('resistance_levels', ['N/A'])[0] if indicators.get('resistance_levels') else 'N/A'}
- Trend: {indicators.get('trend', 'N/A')}
"""

        if news_sentiment:
            prompt += f"\n**Haber Duyarlılığı:** {news_sentiment}\n"

        prompt += """
**Görev:** Kapsamlı teknik analize dayalı bir alım satım sinyali ver.

**Cevap Formatı (kesinlikle uyulmalı):**
SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [Detaylı analiz: trend uyumu, gösterge yakınsaması, destek/direnç seviyeleri, risk faktörleri ve giriş/çıkış noktaları. Türkçe olarak 2-4 cümle.]
"""
        return prompt

    def _parse_response(self, content: str, market: str) -> Dict:
        """Parse Gemini response into structured format"""
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
            "ai_model": "Gemini-2.5-Pro"
        }


def get_gemini_signal(market: str, price: float, indicators: Dict, news_sentiment: Optional[str] = None) -> Optional[Dict]:
    """
    Convenience function to get Gemini trading signal

    Args:
        market: Market symbol
        price: Current price
        indicators: Technical indicators
        news_sentiment: Optional news sentiment

    Returns:
        Signal dict or None
    """
    try:
        client = GeminiClient()
        return client.analyze_market(market, price, indicators, news_sentiment)
    except Exception as e:
        logger.error(f"Gemini wrapper failed: {e}")
        return None