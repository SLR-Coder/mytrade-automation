# utils/deepseek_wrapper.py
# -*- coding: utf-8 -*-
"""
DeepSeek AI Wrapper
Model: DeepSeek-V3 (671B MoE) - MIT/AIME benchmark'ında GPT-4'ü geçti
"""

import time
import logging
from typing import Dict, Optional
from openai import OpenAI

from utils.secrets import get_secret

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DeepSeekWrapper")


class DeepSeekClient:
    """
    DeepSeek AI client for trading signal analysis

    DeepSeek-V3 özellikleri:
    - 671B parametre (Mixture of Experts)
    - Matematik ve quant analiz için mükemmel
    - Backtest ve istatistiksel hesaplamalarda güçlü
    - MIT Math benchmark: GPT-4'ü geçti
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DeepSeek client

        Args:
            api_key: DeepSeek API key (if None, fetches from secrets)
        """
        if api_key is None:
            api_key = get_secret("DEEPSEEK_API_KEY", required=False)

        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found")

        # DeepSeek uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = "deepseek-chat"  # DeepSeek-V3

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
                        {"role": "system", "content": "Sen quantitative trading ve matematiksel analiz konusunda uzman bir finansal analistin. İstatistiksel modeller ve teknik göstergelerle kesin hesaplamalar yapıyorsun."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,  # Çok düşük = matematiksel kesinlik
                    max_tokens=500
                )

                content = response.choices[0].message.content
                result = self._parse_response(content, market)

                logger.info(f"DeepSeek analyzed {market}: {result['signal']} ({result['confidence']}%)")
                return result

            except Exception as e:
                logger.warning(f"DeepSeek deneme {attempt + 1}/{max_retries} başarısız: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Üstel geri çekilme
                else:
                    logger.error(f"DeepSeek {max_retries} denemeden sonra {market} için başarısız oldu")
                    return None

    def _build_prompt(
        self,
        market: str,
        price: float,
        indicators: Dict,
        news_sentiment: Optional[str]
    ) -> str:
        """Analiz prompt'u oluştur"""
        prompt = f"""{market} için matematiksel ve istatistiksel analiz yap.

Mevcut Fiyat: ${price:,.2f}

Teknik Göstergeler (Quantitative Analiz):
- RSI: {indicators.get('rsi', 'Yok')} [Aşırı alım/satım seviyelerini hesapla]
- MACD: {indicators.get('macd', 'Yok')}
- MACD Sinyali: {indicators.get('macd_signal', 'Yok')}
- MACD Histogram: {indicators.get('macd_histogram', 'Yok')} [Momentum yönünü hesapla]
- Bollinger Bantları: Üst={indicators.get('bb_upper', 'Yok')}, Orta={indicators.get('bb_middle', 'Yok')}, Alt={indicators.get('bb_lower', 'Yok')}
- EMA 9: {indicators.get('ema_9', 'Yok')}
- EMA 21: {indicators.get('ema_21', 'Yok')}
- EMA 50: {indicators.get('ema_50', 'Yok')}
- EMA 200: {indicators.get('ema_200', 'Yok')} [EMA cross stratejisi uygula]
- Destek: {indicators.get('support_levels', ['Yok'])[0] if indicators.get('support_levels') else 'Yok'}
- Direnç: {indicators.get('resistance_levels', ['Yok'])[0] if indicators.get('resistance_levels') else 'Yok'}
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
**Quant Analiz Yap (SMC dahil):**
1. Göstergelerin istatistiksel anlamlılığını değerlendir
2. Trend gücünü matematiksel olarak hesapla
3. Risk/ödül oranını hesapla
4. Olasılık bazlı karar ver

Analizini tam olarak şu formatta ver:
SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [Matematiksel gerekçe ile 2-3 cümle - TÜRKÇE yaz, istatistiksel kanıtları belirt]
"""
        return prompt

    def _parse_response(self, content: str, market: str) -> Dict:
        """DeepSeek yanıtını yapılandırılmış formata dönüştür"""
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
            "ai_model": "DeepSeek-V3"
        }


def get_deepseek_signal(market: str, price: float, indicators: Dict, news_sentiment: Optional[str] = None) -> Optional[Dict]:
    """
    Convenience function to get DeepSeek trading signal

    Args:
        market: Market symbol
        price: Current price
        indicators: Technical indicators
        news_sentiment: Optional news sentiment

    Returns:
        Signal dict or None
    """
    try:
        client = DeepSeekClient()
        return client.analyze_market(market, price, indicators, news_sentiment)
    except Exception as e:
        logger.error(f"DeepSeek wrapper failed: {e}")
        return None
