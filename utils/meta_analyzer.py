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
                max_tokens=2000,  # Increased for detailed reasoning
                temperature=0.1,  # Çok düşük = tutarlı kararlar
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            content = response.content[0].text

            # DEBUG: Log raw response
            logger.info(f"\n{'='*60}\nCLAUDE RAW RESPONSE:\n{content}\n{'='*60}\n")

            result = self._parse_meta_response(content, stats)

            logger.info(f"Command Center decision for {market}: {result['final_signal']} ({result['final_confidence']}%)")
            return result

        except Exception as e:
            logger.error(f"Command Center failed: {e}", exc_info=True)
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
            reasoning = sig.get('reasoning', 'Açıklama yok')
            if reasoning and len(reasoning) > 200:
                signals_text += f"   Gerekçe: {reasoning[:200]}...\n\n"
            else:
                signals_text += f"   Gerekçe: {reasoning}\n\n"

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

        prompt = f"""Sen dünya çapında deneyimli bir **Head Trader** ve **AI Komuta Merkezi** liderisin. 15+ yıl forex, crypto ve commodities piyasalarında trading yaptın. Görevin: 6 farklı AI'dan gelen analizleri profesyonelce değerlendirip institutinal-grade nihai karar vermek.

**📊 PİYASA:** {market}
**💵 MEVCUT FİYAT:** ${price:,.2f}

{signals_text}

{stats_text}

{assistant_text}

**🎯 SENIN GÖREVIN (PROFESSIONAL META-ANALİZ):**

**1. AI Consensus Evaluation (Konsensüs Analizi)**
   - Her AI'ın signal + confidence + reasoning'ini değerlendir
   - Hangi AI'ların analizleri daha güçlü? (teknik analiz, momentum, risk-reward açısından)
   - Conflict varsa: Neden farklı düşünüyorlar? Hangisi daha mantıklı?

**2. Strength Weighting (Güç Ağırlıklandırması)**
   - Yüksek confidence'lı AI'lara daha fazla ağırlık ver
   - Reasoning quality: Hangi AI daha detaylı ve mantıklı analiz yapmış?
   - Consensus ratio: %60+ consensus = güçlü sinyal, <%60 = zayıf/dikkatli ol

**3. Assistant AI Override Check (Asistan Kontrolü)**
   - Eğer Asistan AI reddettiyse (`approved: False`) → Bu ÇOK ÖNEMLİ!
   - Asistan kullanıcının risk profili, strateji ve veto listesini temsil eder
   - Asistan ret → HOLD de (çok çok güçlü sebep olmadıkça)

**4. Risk Assessment (Risk Değerlendirmesi)**
   - **LOW RISK:** %80+ consensus, assistant approved, low volatility, clear trend
   - **MEDIUM RISK:** %60-79 consensus, minor conflicts, moderate volatility
   - **HIGH RISK:** <%60 consensus, major conflicts, assistant rejected, high volatility, choppy market

**5. Actionable Decision (İşlem Önerisi)**
   - **ENTER NOW:** Güçlü consensus (%75+), assistant approved, clear setup
   - **WAIT FOR PULLBACK:** Good signal but price extended, wait for better entry
   - **SET ALERT:** Potential setup forming, monitor closely
   - **AVOID:** Weak consensus, conflicts, assistant rejected, choppy/ranging

**🚨 KRITIK KURALLAR:**
✓ Asistan AI reddettiyse (`approved: False`) → 90% durumda HOLD de
✓ Consensus %60 altı → HOLD veya dikkatli MEDIUM RISK
✓ BUY vs SELL conflict → HOLD (çok güçlü sebep olmadıkça)
✓ Confidence weighting: %85+ AI > %70 AI > %50 AI
✓ Quality over quantity: 2 güçlü AI > 4 zayıf AI
✓ Institutional mindset: Capital preservation > Profit hunting

**📋 CEVAP FORMATI (TAM OLARAK ŞU FORMATTA VER):**
SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
CONSENSUS: [0-100]
RISK: [LOW/MEDIUM/HIGH]
ACTION: [ENTER NOW/WAIT FOR PULLBACK/SET ALERT/AVOID]
REASONING: [Profesyonel meta-analiz - Hangi AI'lara neden ağırlık verdin? Çelişkiler nasıl çözüldü? Asistan önerisi neden önemli? Risk neden bu seviyede? Önerilen aksiyon neden bu? - TÜRKÇE, 4-6 cümle, institutional trader dili]

**ÖNEMLİ:** Reasoning çok detaylı olsun çünkü bu analiz ileride kullanılacak ve trade kararları bu rapora göre alınacak!
"""
        return prompt

    def _parse_meta_response(self, content: str, stats: Dict) -> Dict:
        """Komuta merkezi yanıtını parse et - ROBUST version"""
        import re

        final_signal = stats["majority_signal"]  # Default: majority
        final_confidence = int(stats["avg_confidence"])
        consensus_score = int(stats["consensus_ratio"] * 100)
        risk_level = "MEDIUM"  # Default
        suggested_action = "SET ALERT"  # Default
        reasoning = ""

        # Method 1: Try regex-based extraction (more flexible)
        signal_match = re.search(r'SIGNAL:\s*([A-Z]+)', content, re.IGNORECASE)
        if signal_match:
            final_signal = signal_match.group(1).upper()

        confidence_match = re.search(r'CONFIDENCE:\s*(\d+)', content, re.IGNORECASE)
        if confidence_match:
            final_confidence = int(confidence_match.group(1))

        consensus_match = re.search(r'CONSENSUS:\s*(\d+)', content, re.IGNORECASE)
        if consensus_match:
            consensus_score = int(consensus_match.group(1))

        risk_match = re.search(r'RISK:\s*([A-Z]+)', content, re.IGNORECASE)
        if risk_match:
            risk_level = risk_match.group(1).upper()

        action_match = re.search(r'ACTION:\s*([A-Z\s]+?)(?:\n|$)', content, re.IGNORECASE)
        if action_match:
            suggested_action = action_match.group(1).strip().upper()

        # Method 2: Extract reasoning (everything after REASONING: until end or next field)
        reasoning_match = re.search(r'REASONING:\s*(.+?)(?:\n\n|\Z)', content, re.IGNORECASE | re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()
            # Clean up reasoning - remove extra whitespace
            reasoning = ' '.join(reasoning.split())

        # Fallback: If still no reasoning, try line-by-line
        if not reasoning:
            lines = content.strip().split('\n')
            reasoning_started = False
            reasoning_lines = []

            for line in lines:
                line = line.strip()
                if line.startswith("REASONING:"):
                    reasoning_started = True
                    rest = line.split(":", 1)[1].strip()
                    if rest:
                        reasoning_lines.append(rest)
                elif reasoning_started and line:
                    # Stop if we hit another field
                    if line.startswith(("SIGNAL:", "CONFIDENCE:", "CONSENSUS:", "RISK:", "ACTION:")):
                        break
                    reasoning_lines.append(line)

            if reasoning_lines:
                reasoning = " ".join(reasoning_lines)

        # Final fallback
        if not reasoning or reasoning == "":
            reasoning = "Meta-analiz tamamlandı ancak detaylı açıklama parse edilemedi. Karar: " + \
                       f"{final_signal} (%{final_confidence} güven, %{consensus_score} consensus)"
            logger.warning(f"⚠️  REASONING parse failed, using fallback")

        # Log parsed values
        logger.info(f"✓ Parsed - Signal: {final_signal}, Conf: {final_confidence}%, " +
                   f"Consensus: {consensus_score}%, Risk: {risk_level}, Action: {suggested_action}")
        logger.info(f"✓ Reasoning length: {len(reasoning)} chars")

        # Override detection
        command_center_override = (final_signal != stats["majority_signal"])

        return {
            "final_signal": final_signal,
            "final_confidence": final_confidence,
            "reasoning": reasoning,
            "consensus_score": consensus_score,
            "risk_level": risk_level,
            "suggested_action": suggested_action,
            "conflicts": stats["conflicts"],
            "command_center_override": command_center_override,
            "ai_model": "Command-Center-Claude-Sonnet-4.5"
        }

    def _fallback_decision(self, ai_signals: List[Dict], stats: Dict) -> Dict:
        """Fallback: Basit majority voting"""
        logger.warning("Using fallback decision (majority voting)")

        # Auto-calculate risk based on consensus
        if stats["consensus_ratio"] >= 0.8:
            risk_level = "LOW"
        elif stats["consensus_ratio"] >= 0.6:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        # Auto-calculate action
        if stats["majority_signal"] == "HOLD" or risk_level == "HIGH":
            suggested_action = "AVOID"
        elif risk_level == "LOW":
            suggested_action = "ENTER NOW"
        else:
            suggested_action = "SET ALERT"

        return {
            "final_signal": stats["majority_signal"],
            "final_confidence": int(stats["avg_confidence"]),
            "reasoning": f"Fallback: Majority voting kullanıldı. {stats['buy_count']}B/{stats['sell_count']}S/{stats['hold_count']}H. Consensus %{stats['consensus_ratio']*100:.0f}",
            "consensus_score": int(stats["consensus_ratio"] * 100),
            "risk_level": risk_level,
            "suggested_action": suggested_action,
            "conflicts": stats["conflicts"],
            "command_center_override": False,
            "ai_model": "Fallback-MajorityVoting"
        }


def create_command_center() -> CommandCenter:
    """Factory function to create command center"""
    return CommandCenter()
