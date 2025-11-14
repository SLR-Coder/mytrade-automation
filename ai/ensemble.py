# -*- coding: utf-8 -*-
"""
AI Ensemble Signal Generator
Parallel async calls to GPT-4, Claude, Gemini with majority voting
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter

from core.models import AISignal, TechnicalIndicators, EnsembleSignal, NewsItem
from utils.openai_wrapper import get_openai_signal_async
from utils.claude_wrapper import get_claude_signal_async
from utils.gemini_wrapper import get_gemini_signal_async
from utils.secrets import get_secret

logger = logging.getLogger("AIEnsemble")


class EnsembleSignalGenerator:
    """
    Multi-model AI ensemble for trading signals

    Features:
    - Parallel AI calls (GPT-4, Claude, Gemini)
    - Majority voting consensus
    - Confidence aggregation
    - Timeout and retry handling
    - Fallback mechanisms
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 2
    ):
        """
        Initialize ensemble generator

        Args:
            timeout: Timeout per AI call (seconds)
            max_retries: Max retries per AI model
        """
        self.timeout = timeout
        self.max_retries = max_retries

        # Load API keys (all optional)
        # 🧪 TEST MODE: Only provide GEMINI_API_KEY for minimal cost
        # 🚀 LIVE MODE: Provide all 3 keys for best accuracy
        self.openai_key = get_secret("OPENAI_API_KEY", required=False)
        self.anthropic_key = get_secret("ANTHROPIC_API_KEY", required=False)
        self.google_key = get_secret("GEMINI_API_KEY", required=False)

        # Check at least one AI is available
        if not (self.openai_key or self.anthropic_key or self.google_key):
            raise ValueError(
                "❌ At least one AI API key must be configured!\n"
                "TEST: Add GEMINI_API_KEY to Secret Manager\n"
                "LIVE: Add OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY"
            )

        logger.info(
            f"Initialized ensemble with: "
            f"GPT-4={'✓' if self.openai_key else '✗'}, "
            f"Claude={'✓' if self.anthropic_key else '✗'}, "
            f"Gemini={'✓' if self.google_key else '✗'}"
        )

    async def generate_signal(
        self,
        market: str,
        current_price: float,
        indicators: TechnicalIndicators,
        news_items: Optional[List[NewsItem]] = None
    ) -> EnsembleSignal:
        """
        Generate ensemble trading signal

        Args:
            market: Market symbol (e.g., "BTC/USDT")
            current_price: Current market price
            indicators: Technical indicators
            news_items: Recent news items (optional)

        Returns:
            EnsembleSignal with consensus and individual AI votes
        """
        logger.info(f"🤖 Generating ensemble signal for {market}...")

        # Prepare context
        news_context = self._prepare_news_context(news_items) if news_items else None

        # Call all AI models in parallel
        tasks = []
        model_names = []

        if self.openai_key:
            tasks.append(self._call_ai_with_retry("gpt4", market, current_price, indicators, news_context))
            model_names.append("gpt4")

        if self.anthropic_key:
            tasks.append(self._call_ai_with_retry("claude", market, current_price, indicators, news_context))
            model_names.append("claude")

        if self.google_key:
            tasks.append(self._call_ai_with_retry("gemini", market, current_price, indicators, news_context))
            model_names.append("gemini")

        # Wait for all results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        ai_signals: List[AISignal] = []
        for name, result in zip(model_names, results):
            if isinstance(result, Exception):
                logger.error(f"❌ {name.upper()} failed: {result}")
            elif result:
                ai_signals.append(AISignal(
                    model=name,
                    signal=result['signal'],
                    confidence=result['confidence'],
                    reasoning=result['reasoning']
                ))
                logger.info(f"  ✓ {name.upper()}: {result['signal']} ({result['confidence']}%)")

        # Calculate consensus
        consensus = self._calculate_consensus(ai_signals)

        # Calculate news sentiment
        news_sentiment = None
        if news_items:
            sentiments = [n.sentiment_score for n in news_items if n.sentiment_score is not None]
            if sentiments:
                news_sentiment = sum(sentiments) / len(sentiments)

        # Build ensemble signal
        ensemble_signal = EnsembleSignal(
            market=market,
            timestamp=datetime.utcnow(),
            current_price=current_price,
            ai_signals=ai_signals,
            final_signal=consensus['signal'],
            confidence=consensus['confidence'],
            consensus_ratio=consensus['consensus_ratio'],
            reasoning=consensus['reasoning'],
            indicators=indicators,
            relevant_news=news_items or [],
            news_sentiment=news_sentiment
        )

        logger.info(
            f"✅ Consensus: {consensus['signal']} "
            f"({consensus['confidence']}% confidence, "
            f"{consensus['consensus_ratio']*100:.0f}% agreement)"
        )

        return ensemble_signal

    async def _call_ai_with_retry(
        self,
        model: str,
        market: str,
        price: float,
        indicators: TechnicalIndicators,
        news_context: Optional[str]
    ) -> Optional[Dict]:
        """
        Call AI model with retry logic

        Args:
            model: Model name ("gpt4", "claude", "gemini")
            market: Market symbol
            price: Current price
            indicators: Technical indicators
            news_context: News context string

        Returns:
            Signal dict or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                # Call with timeout
                if model == "gpt4":
                    result = await asyncio.wait_for(
                        get_openai_signal_async(market, price, indicators, news_context),
                        timeout=self.timeout
                    )
                elif model == "claude":
                    result = await asyncio.wait_for(
                        get_claude_signal_async(market, price, indicators, news_context),
                        timeout=self.timeout
                    )
                elif model == "gemini":
                    result = await asyncio.wait_for(
                        get_gemini_signal_async(market, price, indicators, news_context),
                        timeout=self.timeout
                    )
                else:
                    raise ValueError(f"Unknown model: {model}")

                return result

            except asyncio.TimeoutError:
                logger.warning(f"⏱️  {model.upper()} timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"❌ {model.upper()} error: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return None

    def _calculate_consensus(self, ai_signals: List[AISignal]) -> Dict:
        """
        Calculate consensus from AI signals using majority voting

        Args:
            ai_signals: List of AI signals

        Returns:
            Dict with consensus signal, confidence, and reasoning
        """
        if not ai_signals:
            logger.error("❌ No AI signals available!")
            return {
                "signal": "HOLD",
                "confidence": 0,
                "consensus_ratio": 0.0,
                "reasoning": "All AI models failed to generate signals"
            }

        # Extract signals
        signals = [s.signal for s in ai_signals]

        # Majority voting
        signal_counts = Counter(signals)
        consensus_signal = signal_counts.most_common(1)[0][0]
        consensus_count = signal_counts[consensus_signal]

        # Calculate confidence
        # 1. Average confidence from models that voted for consensus
        consensus_confidences = [
            s.confidence for s in ai_signals
            if s.signal == consensus_signal
        ]
        avg_confidence = sum(consensus_confidences) / len(consensus_confidences)

        # 2. Apply consensus bonus (more agreement = higher confidence)
        consensus_ratio = consensus_count / len(ai_signals)
        consensus_bonus = consensus_ratio * 15  # Up to +15 confidence

        # 3. Final confidence
        final_confidence = min(100, int(avg_confidence + consensus_bonus))

        # Build reasoning
        reasoning_parts = []
        for signal in ai_signals:
            if signal.signal == consensus_signal:
                short_reason = signal.reasoning[:80] + "..." if len(signal.reasoning) > 80 else signal.reasoning
                reasoning_parts.append(f"{signal.model.upper()}: {short_reason}")

        combined_reasoning = " | ".join(reasoning_parts)

        return {
            "signal": consensus_signal,
            "confidence": final_confidence,
            "consensus_ratio": consensus_ratio,
            "reasoning": combined_reasoning,
            "vote_counts": dict(signal_counts)
        }

    def _prepare_news_context(self, news_items: List[NewsItem]) -> str:
        """
        Prepare news context string for AI

        Args:
            news_items: List of news items

        Returns:
            Formatted news context string
        """
        if not news_items:
            return ""

        context_parts = ["Recent Market News:"]
        for i, news in enumerate(news_items[:3], 1):  # Top 3 news
            sentiment_emoji = "📈" if news.sentiment_score and news.sentiment_score > 0.3 else "📉" if news.sentiment_score and news.sentiment_score < -0.3 else "➡️"
            context_parts.append(
                f"{i}. {sentiment_emoji} {news.title} "
                f"(Impact: {news.impact or 'MEDIUM'}, Sentiment: {news.sentiment_label or 'neutral'})"
            )

        return "\n".join(context_parts)