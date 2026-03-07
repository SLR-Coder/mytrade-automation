# engines/pipeline.py
# -*- coding: utf-8 -*-
"""
MyTrade V2.0 - Main Analysis Pipeline
=====================================
Orchestrates the complete analysis workflow.

Pipeline Steps:
1. Data Collection (Market data from CoinGecko)
2. Pre-Score (Quantitative scoring with CoinGlass)
3. Shortlist (Select top candidates)
4. Grok Scout (Narrative scanning - shortlist only)
5. Gemini Parser (Normalize narratives)
6. Deterministic Scoring (Unified bias calculation)
7. Commander (Final synthesis)
8. Publisher (Telegram + DB logging)
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import pytz

from .coinglass_client import get_coinglass_client
from .pre_score import PreScoreEngine
from .shortlist import ShortlistEngine
from .grok_scout import GrokScout
from .gemini_parser import GeminiParser
from .deterministic_scorer import DeterministicScorer
from .macro_overlay import MacroOverlay
from .commander import Commander

logger = logging.getLogger("Pipeline")

TURKEY_TZ = pytz.timezone('Europe/Istanbul')

# Default crypto universe
CRYPTO_UNIVERSE = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT",
    "BNB/USDT", "ADA/USDT", "SUI/USDT", "TON/USDT"
]


class AnalysisPipeline:
    """
    Main analysis pipeline orchestrator.
    Coordinates all engines for end-to-end analysis.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize pipeline with all engines

        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}

        # Initialize engines
        self.pre_score_engine = PreScoreEngine()
        self.shortlist_engine = ShortlistEngine()
        self.grok_scout = GrokScout()
        self.gemini_parser = GeminiParser()
        self.deterministic_scorer = DeterministicScorer()
        self.macro_overlay = MacroOverlay()
        self.commander = Commander()

        # Pipeline state
        self.last_run = None
        self.last_results = None

    def run_crypto_pipeline(
        self,
        market_data: List[Dict],
        skip_narrative: bool = False,
        macro_context: Dict = None
    ) -> Dict:
        """
        Run complete crypto analysis pipeline

        Args:
            market_data: List of market data dicts from data collection
            skip_narrative: Skip Grok/Gemini for faster runs
            macro_context: Optional macro overlay context

        Returns:
            Complete pipeline results
        """
        start_time = datetime.now(TURKEY_TZ)
        logger.info("=" * 60)
        logger.info("🚀 STARTING CRYPTO ANALYSIS PIPELINE")
        logger.info(f"   Assets: {len(market_data)}")
        logger.info(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        results = {
            "timestamp": start_time.isoformat(),
            "pipeline_version": "2.0",
            "steps": {}
        }

        try:
            # Step 1: Pre-Score all assets
            logger.info("\n📊 Step 1: PRE-SCORING...")
            pre_scores = []
            for data in market_data:
                symbol = data.get("symbol")
                indicators = data.get("indicators", {})

                try:
                    score = self.pre_score_engine.score_asset(
                        symbol=symbol,
                        market_data=data,
                        indicators=indicators
                    )
                    pre_scores.append(score)
                except Exception as e:
                    logger.error(f"Pre-score error for {symbol}: {e}")
                    pre_scores.append({
                        "symbol": symbol,
                        "pre_score_complete": False,
                        "error": str(e)
                    })

            results["steps"]["pre_score"] = {
                "completed": len([p for p in pre_scores if p.get("pre_score_complete")]),
                "total": len(market_data)
            }
            logger.info(f"   ✓ Pre-scored {results['steps']['pre_score']['completed']}/{len(market_data)} assets")

            # Step 2: Shortlist selection
            logger.info("\n🎯 Step 2: SHORTLIST SELECTION...")
            shortlist = self.shortlist_engine.select_shortlist(pre_scores)
            results["steps"]["shortlist"] = {
                "top_now": len(shortlist.get("top_now", [])),
                "next_candidates": len(shortlist.get("next_candidates", [])),
                "market_sentiment": shortlist.get("market_sentiment", {})
            }
            logger.info(f"   ✓ Selected {results['steps']['shortlist']['top_now']} TOP NOW + {results['steps']['shortlist']['next_candidates']} NEXT")

            # Step 3: Narrative scanning (optional)
            scout_results = {}
            parsed_narratives = {}

            if not skip_narrative:
                logger.info("\n🔍 Step 3: NARRATIVE SCANNING (Grok)...")
                shortlist_assets = shortlist.get("top_now", []) + shortlist.get("next_candidates", [])

                for asset in shortlist_assets:
                    symbol = asset.get("symbol")
                    try:
                        scout_results[symbol] = self.grok_scout.scout_asset(
                            symbol=symbol,
                            context={
                                "price": asset.get("price"),
                                "bias": asset.get("bias")
                            }
                        )
                    except Exception as e:
                        logger.error(f"Grok scout error for {symbol}: {e}")
                        scout_results[symbol] = {"scout_success": False, "error": str(e)}

                results["steps"]["grok_scout"] = {
                    "scanned": len(scout_results),
                    "successful": sum(1 for r in scout_results.values() if r.get("scout_success"))
                }
                logger.info(f"   ✓ Scanned {results['steps']['grok_scout']['successful']}/{len(scout_results)} narratives")

                # Step 4: Parse narratives (Gemini)
                logger.info("\n📝 Step 4: PARSING NARRATIVES (Gemini)...")
                parsed_narratives = self.gemini_parser.parse_batch_narratives(scout_results)
                results["steps"]["gemini_parse"] = {
                    "parsed": sum(1 for p in parsed_narratives.values() if p.get("parsed_success"))
                }
                logger.info(f"   ✓ Parsed {results['steps']['gemini_parse']['parsed']} narratives")
            else:
                logger.info("\n⏭️ Steps 3-4: SKIPPED (skip_narrative=True)")
                results["steps"]["grok_scout"] = {"skipped": True}
                results["steps"]["gemini_parse"] = {"skipped": True}

            # Step 5: Deterministic scoring
            logger.info("\n🧮 Step 5: DETERMINISTIC SCORING...")

            # Extract events from parsed narratives
            events_by_symbol = {}
            if parsed_narratives:
                all_events = self.gemini_parser.extract_events_from_parsed(parsed_narratives)
                for event in all_events:
                    source_symbol = event.get("source_symbol")
                    if source_symbol:
                        if source_symbol not in events_by_symbol:
                            events_by_symbol[source_symbol] = []
                        events_by_symbol[source_symbol].append(event)

            unified_scores = self.deterministic_scorer.score_batch(
                pre_scores=pre_scores,
                narratives=parsed_narratives,
                events_by_symbol=events_by_symbol,
                macro_context=macro_context
            )

            results["steps"]["deterministic"] = {
                "scored": len(unified_scores),
                "conflicts_found": sum(s.get("conflict_count", 0) for s in unified_scores)
            }
            logger.info(f"   ✓ Scored {len(unified_scores)} assets")

            # Step 6: Commander synthesis
            logger.info("\n🎖️ Step 6: COMMANDER SYNTHESIS...")
            syntheses = []
            for score in unified_scores[:6]:  # Top 6 only
                synthesis = self.commander.synthesize(score)
                syntheses.append(synthesis)

            top_summary = self.commander.generate_top_summary(unified_scores)

            results["steps"]["commander"] = {
                "synthesized": len(syntheses),
                "top_summary_generated": True
            }
            logger.info(f"   ✓ Synthesized {len(syntheses)} signals")

            # Final results
            results["unified_scores"] = unified_scores
            results["syntheses"] = syntheses
            results["top_summary"] = top_summary
            results["shortlist"] = shortlist
            results["success"] = True

            # Timing
            end_time = datetime.now(TURKEY_TZ)
            results["duration_seconds"] = (end_time - start_time).total_seconds()

            logger.info("\n" + "=" * 60)
            logger.info("✅ PIPELINE COMPLETED")
            logger.info(f"   Duration: {results['duration_seconds']:.1f}s")
            logger.info(f"   Market Tone: {top_summary.get('market_tone', 'N/A')}")
            logger.info("=" * 60)

            self.last_run = end_time
            self.last_results = results

            return results

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            results["success"] = False
            results["error"] = str(e)
            return results

    def run_macro_pipeline(self, date: datetime = None) -> Dict:
        """
        Run macro event overlay pipeline

        Args:
            date: Date to analyze (defaults to today)

        Returns:
            Macro pipeline results
        """
        if date is None:
            date = datetime.now(TURKEY_TZ)

        logger.info("=" * 60)
        logger.info("🌍 STARTING MACRO OVERLAY PIPELINE")
        logger.info(f"   Date: {date.strftime('%Y-%m-%d')}")
        logger.info("=" * 60)

        results = {
            "timestamp": datetime.now(TURKEY_TZ).isoformat(),
            "date": date.strftime('%Y-%m-%d'),
            "pipeline_type": "macro"
        }

        # Check if event day
        is_event_day = self.macro_overlay.is_event_day(date)

        if not is_event_day:
            logger.info("📅 Not an event day - no macro analysis needed")
            results["is_event_day"] = False
            results["message"] = "No significant macro events scheduled"
            return results

        # Generate event day summary
        summary = self.macro_overlay.generate_event_day_summary(date)
        results["is_event_day"] = True
        results["event_summary"] = summary

        logger.info(f"📊 Event day: {summary.get('event_count', 0)} events scheduled")
        logger.info(f"   Highest: {summary.get('highest_importance', 'N/A')}")
        logger.info(f"   Affected: {', '.join(summary.get('affected_instruments', [])[:5])}")

        return results

    def get_telegram_messages(self, results: Dict) -> List[str]:
        """
        Generate Telegram messages from pipeline results

        Args:
            results: Pipeline results

        Returns:
            List of formatted messages
        """
        messages = []

        if not results.get("success"):
            return [f"❌ Pipeline error: {results.get('error', 'Unknown error')}"]

        # Top summary message
        top_summary = results.get("top_summary", {})
        if top_summary:
            messages.append(self.commander.format_top_summary_message(top_summary))

        # Individual synthesis messages
        for synthesis in results.get("syntheses", [])[:4]:
            messages.append(self.commander.format_telegram_message(synthesis))

        return messages


# Singleton instance
_pipeline_instance = None


def get_pipeline() -> AnalysisPipeline:
    """Get or create pipeline singleton"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = AnalysisPipeline()
    return _pipeline_instance
