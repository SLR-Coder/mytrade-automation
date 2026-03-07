# engines/__init__.py
"""
MyTrade V2.0 - AI Engine Modules
================================
Deterministic scoring and AI motor integration layer.

Architecture:
- pre_score: Calculate base quantitative scores for all assets
- shortlist: Select top candidates for deeper analysis
- grok_scout: X/news narrative scanning
- gemini_parser: Normalize raw text to structured JSON
- deterministic_scorer: Weighted unified score calculation
- macro_overlay: Event-driven FX/metals/indices overlay
- commander: Final synthesis and message generation
"""

from .coinglass_client import CoinGlassClient, get_coinglass_client
from .pre_score import PreScoreEngine
from .shortlist import ShortlistEngine
from .grok_scout import GrokScout
from .gemini_parser import GeminiParser
from .deterministic_scorer import DeterministicScorer
from .macro_overlay import MacroOverlay
from .commander import Commander
from .pipeline import AnalysisPipeline, get_pipeline

__all__ = [
    'CoinGlassClient',
    'get_coinglass_client',
    'PreScoreEngine',
    'ShortlistEngine',
    'GrokScout',
    'GeminiParser',
    'DeterministicScorer',
    'MacroOverlay',
    'Commander',
    'AnalysisPipeline',
    'get_pipeline',
]
