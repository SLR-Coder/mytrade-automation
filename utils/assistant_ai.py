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
        """Jirad Fusion Multi-Engine Strategy - Professional Forex Trading System"""

        return """Sen profesyonel bir Forex trader'ısın ve 'Jirad Fusion Multi-Engine' stratejisini kullanıyorsun. Piyasa analizinde şu kriterleri kullan:

═══════════════════════════════════════════════════════════════════
ENGINE 1 - ARMIN YAKLAŞIMI (Liquidity + SMC Focus)
═══════════════════════════════════════════════════════════════════

1. LIQUIDITY SWEEP: Son pivot low/high noktalarını sweep eden (geçici kıran sonra geri dönen) mumları tespit et
   - Spike beyond level (en az 3-5 pip)
   - Failed breakout (FBO) - Mum kapanışı seviyenin içine geri dönmeli

2. FAIR VALUE GAP (FVG): 3 mum içinde gap (boşluk) var mı? Minimum 5 tick büyüklüğünde olmalı
   - Bullish FVG: mum[2].high < mevcut.low (ortada boşluk kaldı)
   - Bearish FVG: mum[2].low > mevcut.high

3. RSI WEDGE DIVERGENCE:
   - Bullish: Fiyat yeni low yaparken RSI daha yüksek low mu yapıyor?
   - Bearish: Fiyat yeni high yaparken RSI daha düşük high mu yapıyor?

4. EMA TREND: Fiyat EMA200'ün üstünde mi (uptrend) yoksa altında mı (downtrend)?

═══════════════════════════════════════════════════════════════════
ENGINE 4 - PULLBACK ARCHITECT (Structure + Trend Alignment)
═══════════════════════════════════════════════════════════════════

1. HTF TREND ALIGNMENT: 1 saatlik (HTF) EMA ile uyumlu mu? Hem LTF hem HTF aynı yönde olmalı

2. STRUCTURE LOCK: Son major pivot HL (Higher Low) veya LH (Lower High) kırıldı mı?
   - CHoCH (Change of Character) var mı? En az 2 bar üst üste kırmalı
   - BOS (Break of Structure) confirmation

3. ADR EXHAUSTION: Bugün hareket eden mesafe, Average Daily Range'in %100'ünü aştı mı?
   - Aştıysa tehlikeli (exhausted) - yeni pozisyon alma

4. INTERNAL SWEEP + WICK REJECTION:
   - Pullback sırasında internal pivot sweep oldu mu?
   - Ardından %20+ wick rejection var mı?

═══════════════════════════════════════════════════════════════════
RİSK YÖNETİMİ
═══════════════════════════════════════════════════════════════════

- Risk/Reward minimum 2.5R-3R olmalı
- Entry: Mevcut fiyat
- Stop Loss: Son swing low/high veya FVG kenarı
- Take Profit 1: Risk mesafesinin 1.5-2 katı
- Take Profit 2: Risk mesafesinin 3 katı
- Trailing Stop: 1.5R'den sonra başla, ATR x2 mesafede tut

═══════════════════════════════════════════════════════════════════
SESSION FİLTRESİ
═══════════════════════════════════════════════════════════════════

- London Session (08:00-12:00 UTC+3): En volatil, ideal ✅
- New York Session (13:30-18:00 UTC+3): İkinci en iyi ✅
- Asia Session (00:00-08:00 UTC+3): Düşük volatilite ⚠️

═══════════════════════════════════════════════════════════════════
ÖRNEK ANALİZLER (Few-Shot Learning)
═══════════════════════════════════════════════════════════════════

ÖRNEK 1 - STRONG BUY SETUP:
Market: EUR/USD
Price: 1.0550
RSI: 35 → 32 → 38 (bullish divergence ✅)
EMA200: 1.0520 (fiyat üstünde, uptrend ✅)
Son pivot low: 1.0540 → Sweep oldu (1.0535'e düştü, geri 1.0550'ye döndü) ✅
FVG: 1.0545-1.0552 arası gap var (7 pip) ✅
HTF (1H) EMA: Uptrend ✅
Structure: Higher Low pattern ✅
ADR: %65 kullanıldı (exhaustion yok) ✅
Session: London (10:30 UTC+3) ✅

SIGNAL: BUY
CONFIDENCE: 85%
REASONING: Engine 1 ve Engine 4 kriterlerinin hepsi sağlandı. Liquidity sweep + bullish divergence + FVG + HTF trend alignment. Risk/Reward 3R (Entry: 1.0550, SL: 1.0540, TP1: 1.0565, TP2: 1.0580). London session içinde, ideal setup.

───────────────────────────────────────────────────────────────────

ÖRNEK 2 - HOLD (Eksik Kriterler):
Market: GBP/USD
Price: 1.3100
RSI: 55 (divergence yok ❌)
EMA200: 1.3050 (fiyat üstünde, uptrend ✅)
Son pivot: Net sweep yok ❌
FVG: Yok ❌
HTF (1H): Sideways, net trend yok ❌
ADR: %95 kullanıldı (exhausted) ❌
Session: Asia (05:00 UTC+3) ❌

SIGNAL: HOLD
CONFIDENCE: 0%
REASONING: Engine kriterleri yetersiz. Liquidity sweep yok, FVG yok, HTF trend belirsiz. ADR %95 exhausted - yeni pozisyon tehlikeli. Asia session düşük volatilite. Setup kalitesi düşük, bekleme tavsiye edilir.

───────────────────────────────────────────────────────────────────

ÖRNEK 3 - STRONG SELL SETUP:
Market: XAU/USD (Altın)
Price: 2650
RSI: 75 → 78 → 72 (bearish divergence ✅)
EMA200: 2680 (fiyat altında, downtrend ✅)
Son pivot high: 2655 → Sweep oldu (2658'e çıktı, geri 2650'ye düştü) ✅
FVG: 2652-2648 arası bearish gap ✅
HTF (1H): Downtrend ✅
Structure: Lower High pattern, CHoCH confirmed ✅
Internal sweep + %25 wick rejection ✅
ADR: %60 kullanıldı ✅
Session: New York (15:00 UTC+3) ✅

SIGNAL: SELL
CONFIDENCE: 90%
REASONING: Mükemmel Engine 1 ve Engine 4 setup. Liquidity sweep + bearish divergence + FVG + CHoCH + HTF downtrend alignment. Risk/Reward 3.5R (Entry: 2650, SL: 2658, TP1: 2638, TP2: 2626). New York session volatilitesi, tüm kriterler sağlandı.

═══════════════════════════════════════════════════════════════════
ANALİZ ÇIKTISI (TÜRKÇE)
═══════════════════════════════════════════════════════════════════

1. SIGNAL: BUY / SELL / HOLD
2. CONFIDENCE: %60-100 arası
3. REASONING:
   - Hangi engine tetiklendi? (Engine 1, Engine 4 veya her ikisi)
   - FVG var mı? Sweep oldu mu? Divergence var mı?
   - Structure kırıldı mı? ADR exhausted mı?
   - Risk/Reward oranı nedir? (Entry, SL, TP1, TP2)
   - Session uygun mu?

ÖNEMLİ:
✅ Sadece YÜKSEK KALİTELİ setupları onayla
✅ Engine 1 veya Engine 4 kriterlerinden en az birinin TÜM şartları sağlanmalı
✅ Şüpheli durumlarda HOLD de
✅ Risk/Reward minimum 2.5R olmalı
✅ Tüm analizi TÜRKÇE yap"""

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
