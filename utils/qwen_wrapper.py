# utils/qwen_wrapper.py
# -*- coding: utf-8 -*-
"""
Qwen AI Wrapper (Alibaba Cloud)
Model: Qwen2.5-Max (72B) - En güçlü Alibaba modeli
"""

import time
import logging
from typing import Dict, Optional
from openai import OpenAI

from utils.secrets import get_secret

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QwenWrapper")


class QwenClient:
    """
    Qwen AI client for trading signal analysis

    Qwen2.5-Max özellikleri:
    - 72B parametre
    - Çin ekonomisi ve global makro analizi
    - Güçlü matematik ve akıl yürütme
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Qwen client

        Args:
            api_key: Qwen API key (if None, fetches from secrets)
        """
        if api_key is None:
            api_key = get_secret("QWEN_API_KEY", required=False)

        if not api_key:
            raise ValueError("QWEN_API_KEY not found")

        # Qwen uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = "qwen-max"  # qwen-max = Qwen2.5-Max (72B)

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
                        {"role": "system", "content": "Sen profesyonel bir finansal analistin. Teknik ve fundamental analizi birleştirerek işlem sinyalleri üretiyorsun."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # Düşük temperature = tutarlı sonuçlar
                    max_tokens=500
                )

                content = response.choices[0].message.content
                result = self._parse_response(content, market)

                logger.info(f"Qwen analyzed {market}: {result['signal']} ({result['confidence']}%)")
                return result

            except Exception as e:
                logger.warning(f"Qwen deneme {attempt + 1}/{max_retries} başarısız: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Üstel geri çekilme
                else:
                    logger.error(f"Qwen {max_retries} denemeden sonra {market} için başarısız oldu")
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
- MACD Histogram: {indicators.get('macd_histogram', 'Yok')}
- Bollinger Bantları: Üst={indicators.get('bb_upper', 'Yok')}, Orta={indicators.get('bb_middle', 'Yok')}, Alt={indicators.get('bb_lower', 'Yok')}
- EMA 9: {indicators.get('ema_9', 'Yok')}
- EMA 21: {indicators.get('ema_21', 'Yok')}
- EMA 50: {indicators.get('ema_50', 'Yok')}
- EMA 200: {indicators.get('ema_200', 'Yok')}
- Destek: {indicators.get('support_levels', ['Yok'])[0] if indicators.get('support_levels') else 'Yok'}
- Direnç: {indicators.get('resistance_levels', ['Yok'])[0] if indicators.get('resistance_levels') else 'Yok'}
- Eğilim: {indicators.get('trend', 'Yok')}
"""

        if news_sentiment:
            prompt += f"\nHaber Duyarlılığı: {news_sentiment}\n"

        prompt += """
Özellikle global makro ekonomik faktörleri ve Çin piyasalarının etkisini değerlendir.

Analizini tam olarak şu formatta ver:
SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [2-3 cümlelik detaylı analiz - TÜRKÇE yaz, özellikle makro faktörleri vurgula]
"""
        return prompt

    def _parse_response(self, content: str, market: str) -> Dict:
        """Qwen yanıtını yapılandırılmış formata dönüştür"""
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
            "ai_model": "Qwen2.5-Max"
        }


def get_qwen_signal(market: str, price: float, indicators: Dict, news_sentiment: Optional[str] = None) -> Optional[Dict]:
    """
    Convenience function to get Qwen trading signal

    Args:
        market: Market symbol
        price: Current price
        indicators: Technical indicators
        news_sentiment: Optional news sentiment

    Returns:
        Signal dict or None
    """
    try:
        client = QwenClient()
        return client.analyze_market(market, price, indicators, news_sentiment)
    except Exception as e:
        logger.error(f"Qwen wrapper failed: {e}")
        return None
