# utils/grok_wrapper.py
# -*- coding: utf-8 -*-
"""
Grok AI Wrapper (X.AI)
Model: Grok-3 - Real-time X/Twitter entegrasyonu
"""

import time
import logging
from typing import Dict, Optional
from openai import OpenAI

from utils.secrets import get_secret

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GrokWrapper")


class GrokClient:
    """
    Grok AI client for trading signal analysis

    Grok-3 özellikleri:
    - Real-time X/Twitter entegrasyonu
    - Social sentiment analizi
    - Breaking news detection
    - Whale hareketleri ve influencer sinyalleri
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Grok client

        Args:
            api_key: Grok API key (if None, fetches from secrets)
        """
        if api_key is None:
            api_key = get_secret("GROK_API_KEY", required=False)

        if not api_key:
            raise ValueError("GROK_API_KEY not found")

        # Grok uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        self.model = "grok-2"  # Stable Grok-2 model (Nov 2025)
        logger.info(f"Grok client initialized with model: {self.model}")

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
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Sen real-time piyasa duyarlılığı ve sosyal medya analizinde uzman bir trading asistanısın. X/Twitter'daki whale hareketlerini, influencer sinyallerini ve viral haberleri takip ediyorsun."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,  # Biraz yaratıcılık için
                    max_tokens=500
                )

                content = response.choices[0].message.content
                result = self._parse_response(content, market)

                logger.info(f"Grok analyzed {market}: {result['signal']} ({result['confidence']}%)")
                return result

            except Exception as e:
                logger.warning(f"Grok deneme {attempt + 1}/{max_retries} başarısız: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Üstel geri çekilme
                else:
                    logger.error(f"Grok {max_retries} denemeden sonra {market} için başarısız oldu")
                    return None

    def _build_prompt(
        self,
        market: str,
        price: float,
        indicators: Dict,
        news_sentiment: Optional[str]
    ) -> str:
        """Analiz prompt'u oluştur"""
        prompt = f"""{market} için real-time sentiment ve sosyal medya analizi yap.

Mevcut Fiyat: ${price:,.2f}

Teknik Göstergeler (Referans):
- RSI: {indicators.get('rsi', 'Yok')}
- MACD Histogram: {indicators.get('macd_histogram', 'Yok')}
- Eğilim: {indicators.get('trend', 'Yok')}

SMC (Smart Money Concepts) Göstergeleri:
- FVG (Fair Value Gap): {indicators.get('fvg_status', 'Yok')}
- Liquidity Sweep: {indicators.get('liquidity_sweep', 'Yok')}
- RSI Divergence: {indicators.get('rsi_divergence', 'Yok')}
- Structure Break: {indicators.get('structure_break', 'Yok')}
- Swing High: {indicators.get('swing_high', 'Yok')}
- Swing Low: {indicators.get('swing_low', 'Yok')}
- ADR Kullanım: {indicators.get('adr_exhaustion', 'Yok')}
- HTF Trend (1H): {indicators.get('htf_trend', 'Yok')}
- Session: {indicators.get('session', 'Yok')}
"""

        if indicators.get('temporal_summary'):
            prompt += f"\nSon 30 Dakika Trendi: {indicators['temporal_summary']}\n"

        if news_sentiment:
            prompt += f"\nHaber Duyarlılığı: {news_sentiment}\n"

        prompt += """
**X/Twitter ve Social Sentiment Analizi (SMC verileri dahil):**
1. Son saatte viral olan tweetler var mı?
2. Whale hareketleri veya büyük transferler?
3. Influencer'lar ne diyor?
4. Retail trader sentiment (pozitif/negatif)?
5. Breaking news veya kırılma haberleri?

NOT: Eğer gerçek zamanlı veri yoksa, teknik göstergelere ve genel piyasa sentiment'ına göre karar ver.

Analizini tam olarak şu formatta ver:
SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [Social sentiment ve viral olayları vurgula, 2-3 cümle - TÜRKÇE yaz]
"""
        return prompt

    def _parse_response(self, content: str, market: str) -> Dict:
        """Grok yanıtını yapılandırılmış formata dönüştür"""
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
            "ai_model": "Grok-3"
        }


def get_grok_signal(market: str, price: float, indicators: Dict, news_sentiment: Optional[str] = None) -> Optional[Dict]:
    """
    Convenience function to get Grok trading signal

    Args:
        market: Market symbol
        price: Current price
        indicators: Technical indicators
        news_sentiment: Optional news sentiment

    Returns:
        Signal dict or None
    """
    try:
        client = GrokClient()
        return client.analyze_market(market, price, indicators, news_sentiment)
    except Exception as e:
        logger.error(f"Grok wrapper failed: {e}")
        return None
