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
