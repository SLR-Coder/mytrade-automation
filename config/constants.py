# config/constants.py
# -*- coding: utf-8 -*-
"""
Application Constants
Centralized configuration values to eliminate magic numbers
"""

# ============================================================================
# RETRY & BACKOFF SETTINGS
# ============================================================================
MAX_RETRIES = 2
"""Maximum retry attempts for failed operations"""

BACKOFF_BASE = 2
"""Base for exponential backoff (seconds = BACKOFF_BASE ** attempt)"""

RETRY_TIMEOUT_SECONDS = 30
"""Timeout for individual retry attempts"""


# ============================================================================
# GOOGLE SHEETS RATE LIMITING
# ============================================================================
SHEETS_RATE_LIMIT_SLEEP = 0.5
"""Sleep duration between Google Sheets API calls (seconds)"""

SHEETS_RATE_LIMIT_EXTENDED = 1.0
"""Extended sleep for complex operations (seconds)"""

SHEETS_MAX_CALLS_PER_MINUTE = 60
"""Maximum API calls per minute (Google Sheets quota)"""


# ============================================================================
# TEXT LENGTH LIMITS
# ============================================================================
MAX_REASONING_LENGTH = 500
"""Maximum characters for AI reasoning in Google Sheets cells"""

MAX_NEWS_PREVIEW_LENGTH = 200
"""Maximum characters for news preview"""

MAX_LOG_PREVIEW_LENGTH = 100
"""Maximum characters for log message previews"""


# ============================================================================
# AI MODEL SETTINGS
# ============================================================================
AI_TIMEOUT_SECONDS = 30
"""Timeout for AI API calls"""

AI_MAX_RETRIES = 2
"""Maximum retries for AI API calls"""


# ============================================================================
# CONSENSUS & CONFIDENCE SCORING
# ============================================================================
CONSENSUS_BONUS_MULTIPLIER = 15
"""Bonus confidence points for strong consensus (max +15%)"""

MIN_CONSENSUS_RATIO = 0.5
"""Minimum consensus ratio to avoid HOLD signal"""

CONFIDENCE_MIN = 0
"""Minimum confidence score"""

CONFIDENCE_MAX = 100
"""Maximum confidence score"""


# ============================================================================
# RISK MANAGEMENT
# ============================================================================
RISK_VOLATILITY_MULTIPLIER_TP1 = 1.5
"""Take profit 1 volatility multiplier"""

RISK_VOLATILITY_MULTIPLIER_TP2 = 3.0
"""Take profit 2 volatility multiplier"""

RISK_VOLATILITY_MULTIPLIER_SL = 1.0
"""Stop loss volatility multiplier"""

DEFAULT_VOLATILITY = 0.02
"""Default volatility if Bollinger Bands not available (2%)"""


# ============================================================================
# TRADING PROFILES
# ============================================================================
CONSERVATIVE_MIN_CONFIDENCE = 70
"""Minimum confidence for conservative trading"""

BALANCED_MIN_CONFIDENCE = 60
"""Minimum confidence for balanced trading"""

AGGRESSIVE_MIN_CONFIDENCE = 50
"""Minimum confidence for aggressive trading"""

CONSERVATIVE_CONSENSUS_THRESHOLD = 0.6
"""Minimum consensus for conservative strategy (60%)"""


# ============================================================================
# ROBOT SETTINGS
# ============================================================================
DEFAULT_SHEET_TAB = "MarketData"
"""Default Google Sheets tab name"""

SEPARATOR_TEXT = "Ayırıcı"
"""Separator row text in Google Sheets"""

TOP_NEWS_COUNT = 3
"""Number of top news items to include in analysis"""


# ============================================================================
# TEMPORAL TREND ANALYSIS
# ============================================================================
TEMPORAL_BATCH_COUNT = 6
"""Number of batches for temporal trend analysis"""

TEMPORAL_BATCH_MINUTES = 5
"""Minutes per batch"""

TEMPORAL_TOTAL_MINUTES = TEMPORAL_BATCH_COUNT * TEMPORAL_BATCH_MINUTES  # 30 minutes
"""Total minutes for temporal trend analysis"""

MOMENTUM_THRESHOLD_STRONG = 0.01
"""Threshold for strong momentum detection (1% change between halves)"""


# ============================================================================
# MARKET DETECTION
# ============================================================================
CRYPTO_SYMBOLS = frozenset(["BTC", "ETH", "SOL", "USDT", "USDC", "XRP", "BNB", "DOGE", "ADA", "DOT"])
"""Known cryptocurrency symbols for market type detection"""

TOTAL_MARKETS = 27
"""Total number of markets tracked (5 categories)"""

MARKETS_PER_CATEGORY = 5
"""Default markets per category (FOREX has 7)"""


# ============================================================================
# PERFORMANCE TRACKING
# ============================================================================
PERFORMANCE_LOOKBACK_DAYS = 30
"""Default days to look back for performance metrics"""

WIN_RATE_THRESHOLD_EXCELLENT = 70
"""Win rate threshold for 'Excellent' rating (70%+)"""

WIN_RATE_THRESHOLD_GOOD = 60
"""Win rate threshold for 'Good' rating (60%+)"""

WIN_RATE_THRESHOLD_FAIR = 50
"""Win rate threshold for 'Fair' rating (50%+)"""


# ============================================================================
# AI MODEL NAMES (Environment Overridable)
# ============================================================================
DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"
"""Default Gemini model for Personal AI Analyst"""

DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"
"""Default Claude model for Command Center"""

DEFAULT_GPT_MODEL = "gpt-4-turbo-preview"
"""Default GPT model"""

DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
"""Default DeepSeek model"""

DEFAULT_GROK_MODEL = "grok-beta"
"""Default Grok model"""


# ============================================================================
# EXIT CODES
# ============================================================================
EXIT_SUCCESS = 0
"""Successful execution"""

EXIT_ERROR = 1
"""General error"""

EXIT_INTERRUPT = 130
"""Interrupted by user (SIGINT)"""
