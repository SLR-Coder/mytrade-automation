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

    FIXED: Sadece Gemini 2.5 Pro kullanır
    Kullanıcının özel Jirad-style intraday trading prompt'una göre analiz yapar
    """

    def __init__(
        self,
        ai_model: str = "gemini",  # FIXED: Always Gemini
        custom_prompt: Optional[str] = None
    ):
        """
        Initialize Personal AI Analyst

        Args:
            ai_model: FIXED to "gemini" (Gemini 2.5 Pro)
            custom_prompt: Kullanıcının özel prompt'u (Jirad-style trading strategy)
        """
        self.ai_model = "gemini"  # FIXED: Always Gemini, ignore parameter
        self.custom_prompt = custom_prompt or self._get_default_jirad_prompt()

        logger.info(f"Personal AI Analyst (Robot 8) başlatıldı: GEMINI 2.5 PRO")

    def _get_default_jirad_prompt(self) -> str:
        """Jirad-style liquidity + SMC intraday trading strategy"""

        return """You are an intraday strategy engine implementing a *Jirad-style liquidity + SMC setup*.

You ONLY trade these symbols: EURUSD, GBPUSD, XAUUSD, USDJPY, BTCUSD

CORE IDEA:
- Trade ONLY in the first 1-2 hours of major sessions (Asia/London/New York)
- Main timeframe: M15, Refinement: M5, Higher TF bias: H1 and D1

SETUP:
1. Identify previous session high/low as liquidity pools
2. Wait for liquidity sweep of that high/low
3. Confirm failed breakout (FBO) and CHoCH/BOS in opposite direction
4. Trade in direction of H1/D1 trend, targeting 1:4 R:R
5. Risk: 0.5% per trade, Max: 4 trades/day/symbol

MUST-HAVE CONDITIONS:
1. Inside first 1-2h of active session
2. Clear prior liquidity (previous session high/low)
3. Liquidity sweep (meaningful spike beyond level)
4. First FBO after sweep (closes back through level)
5. Structure shift (CHoCH/BOS with displacement)
6. H1/D1 trend alignment
7. Risk 0.5%, TP at 1:4 R:R
8. Max 4 trades/day/symbol

AVOID: Major news, choppy/range days, ultra-low volatility, daily limit reached

OUTPUT FORMAT - IF VALID SETUP:
SIGNAL: BUY/SELL
CONFIDENCE: 0-100
REASONING: [Turkish] Hangi session, hangi liquidity sweep, FBO kaniti, CHoCH/BOS, H1/D1 trend alignment, R:R detaylari

OUTPUT FORMAT - IF NO SETUP:
SIGNAL: HOLD
CONFIDENCE: 0
REASONING: [Turkish] Neden trade yok: session disinda, sweep yok, FBO yok, trend uyumsuz, choppy, news, limit, vs.

IMPORTANT: Prefer NO_TRADE (HOLD) when conditions not clearly met. Always respond in TURKISH."""

    def analyze(self, market: str, price: float, indicators: Dict) -> Optional[Dict]:
        """
        Piyasayı analiz et ve sinyal üret (SADECE GEMINI 2.5 PRO)

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

            # FIXED: Always call Gemini
            result = self._call_gemini(full_prompt)

            if result:
                logger.info(f"Personal AI (Gemini 2.5 Pro): {result['signal']} ({result['confidence']}%)")

            return result

        except Exception as e:
            logger.error(f"Personal AI Analyst (Gemini) hatası: {e}")
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

    def _call_gemini(self, prompt: str) -> Optional[Dict]:
        """Gemini 2.0 Flash Thinking ile analiz yap"""
        try:
            import google.generativeai as genai
            from utils.secrets import get_secret

            api_key = get_secret("GEMINI_API_KEY", required=False)
            if not api_key:
                logger.warning("Gemini API key bulunamadı")
                return None

            genai.configure(api_key=api_key)
            # Use Gemini 2.0 Flash Thinking for better intraday analysis
            model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")

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
    ai_model: str = "gemini",  # FIXED: Always Gemini (ignored)
    custom_prompt: Optional[str] = None
) -> PersonalAIAnalyst:
    """
    Kişisel AI analist oluştur (Robot 8)

    FIXED: Sadece Gemini 2.0 Flash Thinking kullanır

    Args:
        ai_model: IGNORED - Always uses Gemini
        custom_prompt: Kullanıcının özel Jirad-style trading prompt'u

    Returns:
        PersonalAIAnalyst instance (Gemini 2.0 Flash Thinking)
    """
    return PersonalAIAnalyst(ai_model="gemini", custom_prompt=custom_prompt)
