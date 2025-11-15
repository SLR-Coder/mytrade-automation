# utils/meta_analyzer.py
# -*- coding: utf-8 -*-
"""
Meta Analyzer - AI Komuta Merkezi
Claude Sonnet 4.5 ile tüm AI analizlerini birleştirip nihai kararı verir
"""

import logging
from typing import Dict, List, Optional
from anthropic import Anthropic

from utils.secrets import get_secret

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MetaAnalyzer")


class CommandCenter:
    """
    AI Komuta Merkezi

    Tüm AI'lardan gelen sinyalleri analiz edip nihai kararı verir
    Claude Sonnet 4.5 kullanarak:
    - Conflict detection (AI'lar çelişiyor mu?)
    - Consensus scoring (Kaç AI aynı fikirde?)
    - Confidence weighting (Güven puanı bazlı ağırlıklandırma)
    - Final decision (Nihai karar)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize command center

        Args:
            api_key: Anthropic API key (if None, fetches from secrets)
        """
        if api_key is None:
            api_key = get_secret("ANTHROPIC_API_KEY")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"  # En güçlü Claude
        logger.info("AI Command Center initialized with Claude Sonnet 4.5")

    def make_decision(
        self,
        market: str,
        price: float,
        ai_signals: List[Dict],
        assistant_recommendation: Dict
    ) -> Dict:
        """
        Tüm AI sinyallerini analiz edip nihai kararı ver

        Args:
            market: Piyasa adı
            price: Mevcut fiyat
            ai_signals: Tüm AI'lardan gelen sinyaller
                       [{"signal": "BUY", "confidence": 75, "reasoning": "...", "ai_model": "GPT-4"}, ...]
            assistant_recommendation: Asistan AI'dan gelen öneri

        Returns:
            Nihai karar: {
                "final_signal": "BUY/SELL/HOLD",
                "final_confidence": 85,
                "reasoning": "Detaylı açıklama",
                "consensus_score": 0.8,
                "conflicts": ["GPT-4 vs Gemini"],
                "command_center_override": False
            }
        """
        # İstatistikler hesapla
        stats = self._calculate_statistics(ai_signals)

        # Prompt oluştur
        prompt = self._build_meta_analysis_prompt(
            market, price, ai_signals, assistant_recommendation, stats
        )

        try:
            # Claude'dan nihai karar al
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,  # Çok düşük = tutarlı kararlar
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            content = response.content[0].text
            result = self._parse_meta_response(content, stats)

            logger.info(f"Command Center decision for {market}: {result['final_signal']} ({result['final_confidence']}%)")
            return result

        except Exception as e:
            logger.error(f"Command Center failed: {e}")
            # Fallback: Majority voting
            return self._fallback_decision(ai_signals, stats)

    def _calculate_statistics(self, ai_signals: List[Dict]) -> Dict:
        """AI sinyallerinden istatistikler çıkar"""
        total = len(ai_signals)
        if total == 0:
            return {"buy_count": 0, "sell_count": 0, "hold_count": 0, "avg_confidence": 0}

        buy_count = sum(1 for s in ai_signals if s["signal"] == "BUY")
        sell_count = sum(1 for s in ai_signals if s["signal"] == "SELL")
        hold_count = sum(1 for s in ai_signals if s["signal"] == "HOLD")
        avg_confidence = sum(s["confidence"] for s in ai_signals) / total

        # Çoğunluk sinyali
        if buy_count > sell_count and buy_count > hold_count:
            majority = "BUY"
            consensus = buy_count / total
        elif sell_count > buy_count and sell_count > hold_count:
            majority = "SELL"
            consensus = sell_count / total
        else:
            majority = "HOLD"
            consensus = hold_count / total

        # Conflict detection
        conflicts = []
        if buy_count > 0 and sell_count > 0:
            conflicts.append("BUY vs SELL çelişkisi")
        if consensus < 0.5:
            conflicts.append("Consensus %50'nin altında")

        return {
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "total": total,
            "avg_confidence": avg_confidence,
            "majority_signal": majority,
            "consensus_ratio": consensus,
            "conflicts": conflicts
        }

    def _build_meta_analysis_prompt(
        self,
        market: str,
        price: float,
        ai_signals: List[Dict],
        assistant_rec: Dict,
        stats: Dict
    ) -> str:
        """Komuta merkezi için prompt oluştur"""

        # AI sinyallerini formatla
        signals_text = f"\n**{market} için AI Analizleri:**\n\n"
        for i, sig in enumerate(ai_signals, 1):
            signals_text += f"{i}. **{sig['ai_model']}**: {sig['signal']} (%{sig['confidence']} güven)\n"
            signals_text += f"   Gerekçe: {sig['reasoning'][:200]}...\n\n"

        # İstatistikler
        stats_text = f"""
**İstatistikler:**
- Toplam AI: {stats['total']}
- BUY: {stats['buy_count']}, SELL: {stats['sell_count']}, HOLD: {stats['hold_count']}
- Ortalama Güven: %{stats['avg_confidence']:.1f}
- Çoğunluk: {stats['majority_signal']} (consensus: %{stats['consensus_ratio']*100:.0f})
- Çelişkiler: {', '.join(stats['conflicts']) if stats['conflicts'] else 'Yok'}
"""

        # Asistan önerisi
        assistant_text = f"""
**Asistan AI Önerisi:**
- Onay: {'Evet' if assistant_rec['approved'] else 'Hayır'}
- Öneri: {assistant_rec['recommendation']}
- Gerekçe: {assistant_rec['reasoning']}
"""

        prompt = f"""Sen AI Komuta Merkezi'sin. Görevin: Tüm AI analizlerini değerlendirip nihai karar vermek.

**Piyasa:** {market}
**Mevcut Fiyat:** ${price:,.2f}

{signals_text}

{stats_text}

{assistant_text}

**Senin Görevin (Meta-Analiz):**

1. **Conflict Analysis:** AI'lar arasında çelişki var mı? Neden farklı düşünüyorlar?
2. **Strength Evaluation:** Hangi AI'ın analizi daha güçlü? Matematiksel mi, fundamental mı, sentiment mi?
3. **Consensus Weighting:** Çoğunluğa mı uyalım yoksa azınlıktaki güçlü argümana mı?
4. **Assistant Override:** Asistan AI'ın reddini dikkate al (önemli!)
5. **Final Decision:** Tüm bunları birleştirip nihai kararı ver

**KRITIK KURALLAR:**
- Eğer Asistan AI reddettiyse (`approved: False`), çok güçlü bir sebep olmadıkça HOLD de
- Consensus %60'ın altındaysa dikkatli ol
- Çelişki varsa neden olduğunu açıkla
- Confidence weighting: Yüksek confidence'a daha fazla ağırlık ver

Kararını TAM OLARAK şu formatta ver:
SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
CONSENSUS: [0-100]
REASONING: [Detaylı meta-analiz - hangi AI'lara neden ağırlık verdin, çelişkileri nasıl çözdün, asistan önerisini neden dikkate aldın/almadın - TÜRKÇE, 3-5 cümle]
"""
        return prompt

    def _parse_meta_response(self, content: str, stats: Dict) -> Dict:
        """Komuta merkezi yanıtını parse et"""
        lines = content.strip().split('\n')

        final_signal = stats["majority_signal"]  # Default: majority
        final_confidence = int(stats["avg_confidence"])
        consensus_score = int(stats["consensus_ratio"] * 100)
        reasoning = "Meta-analiz yanıtı ayrıştırılamadı"

        for line in lines:
            line = line.strip()
            if line.startswith("SIGNAL:"):
                final_signal = line.split(":", 1)[1].strip().upper()
            elif line.startswith("CONFIDENCE:"):
                try:
                    final_confidence = int(line.split(":", 1)[1].strip().split()[0])
                except:
                    pass
            elif line.startswith("CONSENSUS:"):
                try:
                    consensus_score = int(line.split(":", 1)[1].strip().split()[0])
                except:
                    pass
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        # Override detection
        command_center_override = (final_signal != stats["majority_signal"])

        return {
            "final_signal": final_signal,
            "final_confidence": final_confidence,
            "reasoning": reasoning,
            "consensus_score": consensus_score,
            "conflicts": stats["conflicts"],
            "command_center_override": command_center_override,
            "ai_model": "Command-Center-Claude-4.5"
        }

    def _fallback_decision(self, ai_signals: List[Dict], stats: Dict) -> Dict:
        """Fallback: Basit majority voting"""
        logger.warning("Using fallback decision (majority voting)")

        return {
            "final_signal": stats["majority_signal"],
            "final_confidence": int(stats["avg_confidence"]),
            "reasoning": f"Fallback: Majority voting kullanıldı. {stats['buy_count']}B/{stats['sell_count']}S/{stats['hold_count']}H",
            "consensus_score": int(stats["consensus_ratio"] * 100),
            "conflicts": stats["conflicts"],
            "command_center_override": False,
            "ai_model": "Fallback-MajorityVoting"
        }


def create_command_center() -> CommandCenter:
    """Factory function to create command center"""
    return CommandCenter()
