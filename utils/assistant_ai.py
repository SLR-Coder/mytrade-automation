# utils/assistant_ai.py
# -*- coding: utf-8 -*-
"""
Assistant AI - Kullanıcının kişisel trading asistanı
Kullanıcının risk profili, stratejisi ve tercihlerine göre AI sinyallerini filtreler
"""

import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AssistantAI")


class TradingAssistant:
    """
    Kişisel trading asistanı

    Kullanıcı profiline göre AI sinyallerini değerlendirir ve öneride bulunur
    """

    def __init__(self, user_profile: Optional[Dict] = None):
        """
        Initialize trading assistant

        Args:
            user_profile: Kullanıcı profili (risk toleransı, strateji, veto listesi vs.)
                         {
                             "risk_tolerance": "low/medium/high",
                             "min_confidence": 60,  # Minimum güven puanı
                             "strategy": "conservative/balanced/aggressive",
                             "veto_markets": ["GÜMÜŞ"],  # Asla trade etme
                             "preferred_signals": ["BUY", "SELL"],  # HOLD'u görmezden gel
                             "max_daily_trades": 10,
                             "custom_rules": []
                         }
        """
        self.profile = user_profile or self._default_profile()
        logger.info(f"Trading Assistant initialized with profile: {self.profile['strategy']}")

    def _default_profile(self) -> Dict:
        """Varsayılan kullanıcı profili"""
        return {
            "risk_tolerance": "medium",
            "min_confidence": 60,
            "strategy": "balanced",
            "veto_markets": [],
            "preferred_signals": ["BUY", "SELL", "HOLD"],
            "max_daily_trades": 20,
            "custom_rules": []
        }

    def evaluate_signals(
        self,
        market: str,
        ai_signals: List[Dict]
    ) -> Dict:
        """
        AI sinyallerini kullanıcı profiline göre değerlendir

        Args:
            market: Piyasa adı
            ai_signals: Tüm AI'lardan gelen sinyaller listesi
                       [{"signal": "BUY", "confidence": 75, "ai_model": "Claude"}, ...]

        Returns:
            Asistan önerisi: {"approved": True/False, "recommendation": str, "reasoning": str}
        """
        # Veto kontrolü
        if market in self.profile["veto_markets"]:
            return {
                "approved": False,
                "recommendation": "VETO",
                "reasoning": f"{market} kullanıcının veto listesinde - işlem yapılmaz"
            }

        # Consensus hesapla
        buy_count = sum(1 for s in ai_signals if s["signal"] == "BUY")
        sell_count = sum(1 for s in ai_signals if s["signal"] == "SELL")
        hold_count = sum(1 for s in ai_signals if s["signal"] == "HOLD")
        total = len(ai_signals)

        # Ortalama güven puanı
        avg_confidence = sum(s["confidence"] for s in ai_signals) / total if total > 0 else 0

        # Çoğunluk sinyali
        if buy_count > sell_count and buy_count > hold_count:
            majority_signal = "BUY"
        elif sell_count > buy_count and sell_count > hold_count:
            majority_signal = "SELL"
        else:
            majority_signal = "HOLD"

        # Risk toleransına göre minimum confidence ayarla
        min_conf = self.profile["min_confidence"]
        if self.profile["risk_tolerance"] == "low":
            min_conf = max(min_conf, 70)  # Düşük risk: En az %70
        elif self.profile["risk_tolerance"] == "high":
            min_conf = max(min_conf, 50)  # Yüksek risk: %50 bile kabul

        # Karar ver
        approved = True
        reasoning = []

        # Güven puanı kontrolü
        if avg_confidence < min_conf:
            approved = False
            reasoning.append(f"Ortalama güven %{avg_confidence:.0f} < minimum %{min_conf}")

        # Preferred signals kontrolü
        if majority_signal not in self.profile["preferred_signals"]:
            approved = False
            reasoning.append(f"{majority_signal} sinyali tercih edilen listede değil")

        # Stratejiye göre özel kurallar
        if self.profile["strategy"] == "conservative":
            # Muhafazakar: Sadece güçlü consensus kabul et
            consensus_ratio = max(buy_count, sell_count, hold_count) / total
            if consensus_ratio < 0.6:  # %60'dan az consensus
                approved = False
                reasoning.append(f"Consensus zayıf (%{consensus_ratio*100:.0f}), muhafazakar strateji reddetti")

        elif self.profile["strategy"] == "aggressive":
            # Agresif: Düşük confidence'da bile kabul et
            if avg_confidence >= 45:  # %45 bile yeterli
                approved = True
                reasoning.append("Agresif strateji: Düşük confidence kabul edildi")

        # Sonuç
        if approved:
            recommendation = majority_signal
            final_reasoning = f"Asistan onayladı: {majority_signal} (%{avg_confidence:.0f} güven, {buy_count}B/{sell_count}S/{hold_count}H)"
        else:
            recommendation = "REJECT"
            final_reasoning = f"Asistan reddetti: {' | '.join(reasoning)}"

        return {
            "approved": approved,
            "recommendation": recommendation,
            "reasoning": final_reasoning,
            "consensus_ratio": max(buy_count, sell_count, hold_count) / total if total > 0 else 0,
            "avg_confidence": avg_confidence
        }


def create_assistant(user_profile: Optional[Dict] = None) -> TradingAssistant:
    """
    Factory function to create trading assistant

    Args:
        user_profile: Kullanıcı profili

    Returns:
        TradingAssistant instance
    """
    return TradingAssistant(user_profile)


# Örnek kullanıcı profilleri
CONSERVATIVE_PROFILE = {
    "risk_tolerance": "low",
    "min_confidence": 70,
    "strategy": "conservative",
    "veto_markets": ["GÜMÜŞ"],  # Gümüş'e hiç girme
    "preferred_signals": ["BUY", "SELL"],  # HOLD görmezden gel
    "max_daily_trades": 5
}

BALANCED_PROFILE = {
    "risk_tolerance": "medium",
    "min_confidence": 60,
    "strategy": "balanced",
    "veto_markets": [],
    "preferred_signals": ["BUY", "SELL", "HOLD"],
    "max_daily_trades": 10
}

AGGRESSIVE_PROFILE = {
    "risk_tolerance": "high",
    "min_confidence": 50,
    "strategy": "aggressive",
    "veto_markets": [],
    "preferred_signals": ["BUY", "SELL"],  # Her şeye gir
    "max_daily_trades": 20
}


# ============================================================================
# ROBOT 8: PERSONAL AI ANALYST
# Kullanıcının kişisel AI analisti - özel prompt ile piyasa analizi yapar
# ============================================================================

class PersonalAIAnalyst:
    """
    Robot 8: Kullanıcının kişisel AI analisti

    Kullanıcının verdiği özel prompt ve tercihlerine göre piyasa analizi yapar.
    Robot 3'teki AI'lar gibi çalışır ama tamamen kişiselleştirilmiştir.
    """

    def __init__(
        self,
        ai_model: str = "claude",
        custom_prompt: Optional[str] = None,
        analysis_style: str = "balanced"
    ):
        """
        Initialize Personal AI Analyst

        Args:
            ai_model: Kullanılacak AI ("claude", "gpt4", "gemini")
            custom_prompt: Kullanıcının özel talimatları
            analysis_style: Analiz stili ("aggressive", "conservative", "balanced")
        """
        self.ai_model = ai_model.lower()
        self.custom_prompt = custom_prompt or self._get_default_prompt(analysis_style)
        self.analysis_style = analysis_style

        logger.info(f"Personal AI Analyst başlatıldı: model={ai_model}, style={analysis_style}")

    def _get_default_prompt(self, style: str) -> str:
        """Analiz stiline göre varsayılan prompt"""

        if style == "aggressive":
            return """Sen agresif bir yatırımcı için çalışan kişisel AI analistsin.
Kullanıcı yüksek risk-yüksek getiri arıyor. Volatilite fırsattır.
Kısa vadeli momentum, güçlü breakout'lar ve hızlı hareketleri tercih et.
Belirsizlik durumunda bile cesur al-sat önerileri yap."""

        elif style == "conservative":
            return """Sen muhafazakar bir yatırımcı için çalışan kişisel AI analistsin.
Kullanıcı sermaye koruma odaklı, düşük risk tercih ediyor.
Uzun vadeli güçlü trendler, sağlam destek seviyeleri ve düşük volatiliteyi tercih et.
Belirsizlik durumunda HOLD öner, sadece net fırsatlarda BUY/SELL ver."""

        else:  # balanced
            return """Sen dengeli bir yatırımcı için çalışan kişisel AI analistsin.
Kullanıcı risk-getiri dengesini önemsiyor.
Orta vadeli net trendler, güçlü teknik sinyaller ve makul risk-ödül oranlarını tercih et.
Belirsizlik varsa HOLD, net sinyal varsa BUY/SELL öner."""

    def analyze(self, market: str, price: float, indicators: Dict) -> Optional[Dict]:
        """
        Piyasayı analiz et ve sinyal üret

        Args:
            market: Piyasa adı
            price: Mevcut fiyat
            indicators: Teknik göstergeler

        Returns:
            {"signal": "BUY/SELL/HOLD", "confidence": 0-100, "reasoning": "..."}
        """
        try:
            # Build full analysis prompt
            full_prompt = self._build_analysis_prompt(market, price, indicators)

            # Call AI model
            if self.ai_model == "claude":
                result = self._call_claude(full_prompt)
            elif self.ai_model in ["gpt4", "openai"]:
                result = self._call_openai(full_prompt)
            elif self.ai_model == "gemini":
                result = self._call_gemini(full_prompt)
            else:
                logger.error(f"Bilinmeyen AI model: {self.ai_model}")
                return None

            if result:
                logger.info(f"Personal AI ({self.ai_model}): {result['signal']} ({result['confidence']}%)")

            return result

        except Exception as e:
            logger.error(f"Personal AI Analyst hatası: {e}")
            return None

    def _build_analysis_prompt(self, market: str, price: float, indicators: Dict) -> str:
        """Analiz prompt'u oluştur"""

        prompt = f"""{self.custom_prompt}

ŞİMDİ ANALİZ ET:

Piyasa: {market}
Mevcut Fiyat: ${price:,.2f}

Teknik Göstergeler:
"""

        # Add all indicators
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

        prompt += """

KİŞİSEL ANALİZ YAPARAK tam olarak şu formatta cevap ver:

SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [Kullanıcı profiline uygun, teknik göstergeleri detaylıca analiz eden, risk-ödül değerlendirmesi içeren 3-5 cümlelik TÜRKÇE açıklama]

ÖNEMLİ: Tüm analizi TÜRKÇE yaz ve kullanıcı profilini göz önünde bulundur!
"""

        return prompt

    def _call_claude(self, prompt: str) -> Optional[Dict]:
        """Claude ile analiz yap"""
        try:
            from anthropic import Anthropic
            from utils.secrets import get_secret

            api_key = get_secret("CLAUDE_API_KEY", required=False)
            if not api_key:
                logger.warning("Claude API key bulunamadı")
                return None

            client = Anthropic(api_key=api_key)

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text
            return self._parse_response(text)

        except Exception as e:
            logger.error(f"Claude hatası: {e}")
            return None

    def _call_openai(self, prompt: str) -> Optional[Dict]:
        """OpenAI ile analiz yap"""
        try:
            from openai import OpenAI
            from utils.secrets import get_secret

            api_key = get_secret("OPENAI_API_KEY", required=False)
            if not api_key:
                logger.warning("OpenAI API key bulunamadı")
                return None

            client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )

            text = response.choices[0].message.content
            return self._parse_response(text)

        except Exception as e:
            logger.error(f"OpenAI hatası: {e}")
            return None

    def _call_gemini(self, prompt: str) -> Optional[Dict]:
        """Gemini ile analiz yap"""
        try:
            import google.generativeai as genai
            from utils.secrets import get_secret

            api_key = get_secret("GEMINI_API_KEY", required=False)
            if not api_key:
                logger.warning("Gemini API key bulunamadı")
                return None

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash-exp")

            response = model.generate_content(prompt)
            text = response.text

            return self._parse_response(text)

        except Exception as e:
            logger.error(f"Gemini hatası: {e}")
            return None

    def _parse_response(self, text: str) -> Optional[Dict]:
        """AI yanıtını parse et"""
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
                logger.warning(f"Parse başarısız: {text[:200]}")
                return None

            return {
                "signal": signal,
                "confidence": min(100, max(0, confidence)),
                "reasoning": reasoning.strip()
            }

        except Exception as e:
            logger.error(f"Parse hatası: {e}")
            return None


def create_personal_analyst(
    ai_model: str = "claude",
    custom_prompt: Optional[str] = None,
    analysis_style: str = "balanced"
) -> PersonalAIAnalyst:
    """
    Kişisel AI analist oluştur (Robot 8)

    Args:
        ai_model: AI modeli ("claude", "gpt4", "gemini")
        custom_prompt: Kullanıcının özel prompt'u
        analysis_style: Analiz stili ("aggressive", "conservative", "balanced")

    Returns:
        PersonalAIAnalyst instance
    """
    return PersonalAIAnalyst(ai_model, custom_prompt, analysis_style)
