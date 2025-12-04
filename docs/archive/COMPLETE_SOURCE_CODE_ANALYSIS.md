# MyTrade Automation System - Complete Source Code Analysis

**Repository:** https://github.com/SLR-Coder/mytrade/tree/claude/trade-automation-analysis-011CV63TMgMzz27vc6dwrGjf

**Downloaded:** 2025-11-14

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Complete File Structure](#complete-file-structure)
3. [Architecture & Design Patterns](#architecture--design-patterns)
4. [Dependencies Between Files](#dependencies-between-files)
5. [Source Code by Directory](#source-code-by-directory)
6. [Key Configuration Files](#key-configuration-files)
7. [Deployment & Infrastructure](#deployment--infrastructure)

---

## Project Overview

MyTrade is a professional-grade automated trading signal system (v2.0) that combines:
- **AI Ensemble:** GPT-4, Claude Opus 4, and Gemini 2.5 Pro with majority voting consensus
- **Multi-Asset Coverage:** Crypto (Binance), Forex (Polygon.io/Alpha Vantage), Commodities (Gold/Silver)
- **Cloud Infrastructure:** Google Cloud Run, Cloud SQL PostgreSQL, Cloud Storage, Secret Manager
- **Real-time Data:** Google Sheets dashboard integration
- **Automated Notifications:** Telegram bot with Turkish-language signals and charts

### Core Execution Flow (5 Phases)

1. **Data Collection** - Robot 1: Market Harvester + Robot 2: News Analyzer
2. **Performance Updates** - Robot 6: Performance Tracker
3. **Signal Generation** - Robot 3: AI Signal Generator (3 AI models)
4. **Visualization** - Robot 4: Chart Generator
5. **Publishing** - Robot 5: Telegram Publisher

### Schedule-Based Automation

- **Hourly:** Every hour at :00 minutes (Robots 1, 5)
- **Pre-London:** 10:00 Turkey Time (All robots)
- **London Open:** 11:00 Turkey Time (All robots)
- **Pre-New York:** 15:00 Turkey Time (All robots)
- **New York Open:** 16:00 Turkey Time (All robots)
- **Peak Volatility:** 17:00 Turkey Time (London+NY overlap)
- **Daily Summary:** 20:00 Turkey Time
- **Weekly Summary:** Friday 21:00 Turkey Time

---

## Complete File Structure

```
mytrade/
├── .dockerignore
├── .env.example
├── .gcloudignore
├── .gitignore
├── cloudbuild.yaml
├── Dockerfile
├── health_check.py
├── main.py
├── README.md
├── requirements-minimal.txt
├── requirements-test.txt
├── requirements.txt
├── scheduler_config.yaml
├── setup_sheets.py
│
├── ai/
│   ├── __init__.py
│   └── ensemble.py              # EnsembleSignalGenerator (3 AI models, majority voting)
│
├── core/
│   ├── database.py              # AsyncEngine, connection pooling, CloudSQL/SQLite
│   └── models.py                # Pydantic models (TechnicalIndicators, EnsembleSignal, etc.)
│
├── data/
│   └── models/
│       ├── __init__.py
│       ├── market_data.py       # SQLAlchemy ORM for OHLCV data
│       ├── news.py              # SQLAlchemy ORM for news items
│       ├── performance.py       # SQLAlchemy ORM for performance metrics
│       └── signals.py           # SQLAlchemy ORM for AI signals
│
├── robots/
│   ├── __init__.py
│   ├── ai_signal_generator.py  # Robot 3: AI ensemble signal generation
│   ├── chart_generator.py      # Robot 4: mplfinance charts with indicators
│   ├── market_harvester.py     # Robot 1: Data collection from APIs
│   ├── news_analyzer.py        # Robot 2: NewsAPI + Gemini sentiment analysis
│   ├── performance_tracker.py  # Robot 6: Signal outcomes and metrics
│   └── telegram_publisher.py   # Robot 5: Telegram message/chart publishing
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures and configuration
│   └── test_telegram_formatter.py  # Tests for message formatting
│
└── utils/
    ├── __init__.py
    ├── api_clients.py           # Binance, Polygon, Alpha Vantage, Gold APIs
    ├── auth.py                  # Google Sheets authentication (Workload Identity)
    ├── claude_wrapper.py        # Anthropic Claude API wrapper
    ├── gemini_wrapper.py        # Google Gemini API wrapper
    ├── health_check.py          # System health monitoring
    ├── indicators.py            # Technical indicator calculations (RSI, MACD, BB, EMA)
    ├── openai_wrapper.py        # OpenAI GPT-4 API wrapper
    ├── schema.py                # Google Sheets column schema and mapping
    ├── secrets.py               # Secret Manager + .env fallback
    ├── storage.py               # Google Cloud Storage for charts
    ├── structured_logging.py    # JSON logging, Cloud Logging integration
    ├── telegram_formatter.py    # Turkish message formatting (hourly, session, daily, weekly)
    └── telegram_notifier.py     # Telegram Bot API notifications
```

---

## Architecture & Design Patterns

### 1. **Async/Await Architecture**
- All I/O operations (database, API calls, file operations) use async patterns
- `asyncio.gather()` for parallel execution (AI model calls, health checks)
- Exponential backoff retry logic with configurable max attempts

### 2. **Database Connection Pooling**
- **PostgreSQL (Production):** pool_size=10, max_overflow=20 (30 connections max)
- **SQLite (Development):** NullPool for simplicity
- Auto-retry with exponential backoff on connection errors
- Statement caching and prepared statement optimization

### 3. **Dependency Injection & Configuration**
- Environment-based configuration (ENVIRONMENT=development|production)
- Secret Manager with .env fallback for local development
- Lazy initialization patterns for database connections
- Factory functions for client instantiation

### 4. **Error Handling Strategy**
- Structured exception handling with logging
- Telegram notifications for critical errors
- Graceful degradation (fallback data sources, local storage)
- Health check system with component-level monitoring

### 5. **Structured Logging**
- JSON formatting for production (Cloud Logging integration)
- Colored console output for development
- Execution time decorators for performance tracking
- Request/robot ID tracking for distributed tracing

### 6. **AI Ensemble Pattern**
- Parallel async calls to 3 AI providers (GPT-4, Claude, Gemini)
- Majority voting consensus algorithm
- Confidence boosting based on agreement ratio (up to +15%)
- Individual model timeout handling (30s default)

### 7. **Data Flow Architecture**
```
Market Data APIs → Robot 1 (Harvester) → Google Sheets
                                       ↓
                               Technical Indicators
                                       ↓
News APIs → Robot 2 (Analyzer) → Gemini (sentiment + Turkish)
                                       ↓
                               News + Sentiment
                                       ↓
Robot 6 (Performance) → Signal Outcomes → Database
                                       ↓
    [Market Data + Indicators + News + Performance]
                                       ↓
            Robot 3 (AI Signal Generator)
                  ↓           ↓           ↓
               GPT-4      Claude      Gemini
                  ↓           ↓           ↓
              Ensemble Majority Voting
                         ↓
                  Final Signal
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                  ↓
Robot 4 (Chart)                    Robot 5 (Telegram)
   mplfinance                      Turkish Messages
        ↓                                  ↓
  Cloud Storage                      Telegram Channel
```

### 8. **Google Sheets as Dashboard**
- Real-time data updates via gspread
- Column schema defined in `utils/schema.py`
- Separator rows to mark execution batches
- 38 columns: Market data, indicators, AI signals, risk parameters

---

## Dependencies Between Files

### Core Dependencies Graph

```
main.py
  ├─→ robots/* (all 6 robots)
  ├─→ utils/structured_logging.py
  └─→ utils/telegram_notifier.py

robots/ai_signal_generator.py
  ├─→ ai/ensemble.py (EnsembleSignalGenerator)
  ├─→ utils/auth.py (Google Sheets)
  └─→ utils/schema.py (column mapping)

ai/ensemble.py
  ├─→ core/models.py (Pydantic models)
  ├─→ utils/openai_wrapper.py
  ├─→ utils/claude_wrapper.py
  ├─→ utils/gemini_wrapper.py
  └─→ utils/secrets.py

robots/market_harvester.py
  ├─→ utils/api_clients.py (Binance, Polygon, AlphaVantage)
  ├─→ utils/indicators.py (RSI, MACD, BB, EMA)
  ├─→ utils/auth.py (Google Sheets)
  └─→ utils/schema.py

robots/news_analyzer.py
  ├─→ core/models.py (NewsItem)
  ├─→ data/models/news.py (NewsModel ORM)
  ├─→ core/database.py (async session)
  └─→ utils/gemini_wrapper.py (sentiment + Turkish)

robots/performance_tracker.py
  ├─→ data/models/signals.py (SignalModel)
  ├─→ data/models/performance.py (PerformanceModel)
  ├─→ data/models/market_data.py (MarketDataModel)
  └─→ core/database.py

robots/chart_generator.py
  ├─→ utils/api_clients.py (candle data)
  ├─→ utils/auth.py (Google Sheets)
  ├─→ utils/schema.py
  └─→ mplfinance (external library)

robots/telegram_publisher.py
  ├─→ utils/telegram_formatter.py (Turkish messages)
  ├─→ utils/secrets.py (bot token, chat ID)
  └─→ telegram library

utils/health_check.py
  ├─→ core/database.py
  ├─→ utils/auth.py
  ├─→ utils/secrets.py
  └─→ utils/telegram_notifier.py
```

### External API Dependencies

```
OpenAI API → utils/openai_wrapper.py → ai/ensemble.py
Anthropic API → utils/claude_wrapper.py → ai/ensemble.py
Google Gemini API → utils/gemini_wrapper.py → ai/ensemble.py, robots/news_analyzer.py

Binance API → utils/api_clients.py → robots/market_harvester.py, robots/chart_generator.py
Polygon.io API → utils/api_clients.py → robots/market_harvester.py
Alpha Vantage API → utils/api_clients.py → robots/market_harvester.py
NewsAPI → robots/news_analyzer.py

Google Sheets API → utils/auth.py → all robots
Google Secret Manager → utils/secrets.py → everywhere
Google Cloud Storage → utils/storage.py → robots/chart_generator.py
Telegram Bot API → utils/telegram_notifier.py → main.py, robots
```

---

## Source Code by Directory

### Root Files

#### main.py
**Purpose:** Main orchestrator for the entire trading automation system
**Key Functions:**
- `main_async()`: Async entry point, executes robots in proper sequence
- `run_async_robot()`: Async robot executor with retry logic
- `run_sync_robot()`: Sync robot executor with retry logic
- `signal_handler()`: Graceful shutdown on SIGTERM/SIGINT

**Execution Order:**
1. Robot 1: Market Harvester (sync)
2. Robot 2: News Analyzer (async)
3. Robot 6: Performance Tracker (async)
4. Robot 3: AI Signal Generator (async)
5. Robot 4: Chart Generator (sync)
6. Robot 5: Telegram Publisher (sync)

**Features:**
- Configurable robot selection via ROBOT env var (e.g., "1,2,3,4,5,6")
- Execution time tracking
- Success/failure summary reporting
- Telegram status notifications
- Graceful shutdown handling

---

#### health_check.py
**Purpose:** Standalone health check script for Cloud Scheduler
**Key Function:**
- `main()`: Executes health check and exits with status code

**Checks:**
- Database connectivity
- Google Sheets API
- AI APIs (OpenAI, Claude, Gemini)
- Telegram Bot API
- Market data APIs (Binance)

**Exit Codes:**
- 0: All systems healthy
- 1: Critical issues detected

---

#### setup_sheets.py
**Purpose:** Google Sheets initialization script
**Key Function:**
- `setup_sheet(sheet_name)`: Creates new spreadsheet with proper schema

**Operations:**
1. Authenticates with Google Sheets
2. Creates new spreadsheet
3. Adds 38-column header row from `utils/schema.py`
4. Formats headers (bold, background color, freeze row)
5. Outputs spreadsheet ID for configuration

---

### Configuration Files

#### requirements.txt
**Purpose:** Full production dependencies
**Key Packages:**
- **Cloud:** google-cloud-* (logging, storage, secret-manager)
- **AI:** openai==1.54.0, anthropic==0.39.0, google-generativeai==0.8.5
- **Data:** pandas, numpy, scipy, ta-lib (technical analysis)
- **Database:** sqlalchemy, asyncpg, psycopg2-binary, alembic
- **APIs:** requests, httpx, websocket-client
- **Visualization:** matplotlib, plotly, mplfinance
- **Others:** gspread (Sheets), python-telegram-bot, pydantic, structlog

#### requirements-minimal.txt
**Purpose:** TA-Lib-free dependencies for environments without compilation tools
**Difference:** Uses `ta==0.11.0` instead of TA-Lib

#### requirements-test.txt
**Purpose:** Testing dependencies
**Packages:**
- pytest>=7.4.0
- pytest-asyncio>=0.21.0
- pytest-cov>=4.1.0
- pytest-mock>=3.11.1
- httpx (for async HTTP testing)
- freezegun (time mocking)

#### .env.example
**Purpose:** Environment variable template
**Categories:**
1. **Google Cloud:** GCP_PROJECT, GOOGLE_SHEET_ID, GOOGLE_CLOUD_PROJECT
2. **Market Data:** POLYGON_API_KEY, ALPHA_VANTAGE_KEY, BINANCE_API_KEY
3. **AI:** OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
4. **News:** NEWSAPI_KEY, FINNHUB_KEY
5. **Telegram:** TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
6. **Storage:** GOOGLE_STORAGE_BUCKET
7. **Config:** SHEET_TAB, CANDLE_LIMIT, ROBOT

#### scheduler_config.yaml
**Purpose:** Cloud Scheduler job definitions
**Schedule:**
- Hourly: `0 * * * *` (robots 1,5)
- Pre-London: `0 10 * * *` (all robots, 60% confidence)
- London Open: `0 11 * * *` (all robots, 65% confidence)
- Pre-NY: `0 15 * * *` (all robots, 60% confidence)
- NY Open: `0 16 * * *` (all robots, 70% confidence)
- Peak: `0 17 * * *` (all robots, 65% confidence)
- Daily: `0 20 * * *` (all robots)
- Weekly: `0 21 * * FRI` (all robots)

**Timezone:** Europe/Istanbul (Turkey Time, GMT+3)

#### Dockerfile
**Purpose:** Container image for Cloud Run
**Base:** python:3.11-slim
**Key Steps:**
1. Install build tools (gcc, wget, libpng, libfreetype)
2. Compile and install TA-Lib 0.4.0 from source
3. Install Python dependencies
4. Copy application code
5. Set PYTHONUNBUFFERED=1
6. CMD: `python main.py`

#### cloudbuild.yaml
**Purpose:** Google Cloud Build CI/CD pipeline
**Steps:**
1. **Build:** Docker image tagged as `europe-west1-docker.pkg.dev/$PROJECT_ID/mytrade-repo/mytrade:latest`
2. **Push:** Upload to Artifact Registry
3. **Deploy:** Cloud Run Job with:
   - 2 CPU, 4GB memory
   - Secrets from Secret Manager (API keys, tokens)
   - Environment variables
   - Service account: robot@$PROJECT_ID.iam.gserviceaccount.com
   - Max retries: 1, Timeout: 3600s

---

### ai/ Directory

#### ai/__init__.py
```python
"""
AI module for ensemble signal generation
"""

from ai.ensemble import EnsembleSignalGenerator

__all__ = ["EnsembleSignalGenerator"]
```

#### ai/ensemble.py
**Purpose:** Multi-model AI ensemble with majority voting
**Class:** `EnsembleSignalGenerator`

**Key Methods:**
- `__init__(timeout=30, max_retries=2)`: Initialize with API keys
- `generate_signal(market, price, indicators, news_items)`: Main entry point
- `_call_ai_with_retry(model, ...)`: Retry logic with exponential backoff
- `_calculate_consensus(ai_signals)`: Majority voting algorithm
- `_prepare_news_context(news_items)`: Format news for AI prompts

**Consensus Algorithm:**
1. Collect signals from all available AI models (GPT-4, Claude, Gemini)
2. Find most common signal (BUY/SELL/HOLD)
3. Calculate average confidence from models voting for consensus
4. Apply consensus bonus: +15% max based on agreement ratio
5. Build combined reasoning from agreeing models

**Output:** `EnsembleSignal` Pydantic model with:
- final_signal (BUY/SELL/HOLD)
- confidence (0-100)
- consensus_ratio (0.0-1.0)
- reasoning (combined from AI models)
- individual ai_signals list

---

### core/ Directory

#### core/database.py
**Purpose:** Async database connection manager
**Key Functions:**
- `get_database_url()`: Environment-based URL selection
- `init_database(echo=False)`: Initialize engine and create tables
- `close_database()`: Close all connections
- `get_pool_status()`: Connection pool monitoring
- `get_db_session(auto_retry=True, max_retries=3)`: Context manager with retry

**Database Selection:**
- **Production:** PostgreSQL via CloudSQL Unix socket or TCP
- **Development:** SQLite at /tmp/mytrade.db

**Connection Pool (PostgreSQL):**
- pool_size: 10 base connections
- max_overflow: 20 additional connections
- pool_recycle: 3600s (recycle after 1 hour)
- pool_pre_ping: True (verify before use)
- pool_timeout: 30s
- statement_cache_size: 100
- command_timeout: 60s

**Features:**
- Automatic retry on connection errors
- Exponential backoff (2^attempt seconds)
- Transaction management (auto-commit/rollback)
- Singleton DatabaseManager class

---

#### core/models.py
**Purpose:** Pydantic models for type-safe data handling
**Models:**

1. **TechnicalIndicators**
   - RSI, MACD (line, signal, histogram)
   - Bollinger Bands (upper, middle, lower)
   - EMAs (9, 21, 50, 200), SMAs (20, 50)
   - Support/resistance levels
   - Trend (bullish/bearish/sideways)

2. **NewsItem**
   - title, summary, turkish_summary
   - source, published_at, url
   - sentiment_score (-1 to +1), sentiment_label, impact
   - related_markets list

3. **AISignal**
   - model (gpt4/claude/gemini)
   - signal (BUY/SELL/HOLD)
   - confidence (0-100)
   - reasoning
   - timestamp

4. **RiskReward**
   - entry_price, stop_loss, take_profit_1, take_profit_2
   - risk_amount, reward_amount_1, reward_amount_2
   - risk_reward_ratio_1, risk_reward_ratio_2
   - position_size_percent (0.1-5.0%)

5. **EnsembleSignal**
   - market, timestamp, current_price
   - ai_signals list
   - final_signal, confidence, consensus_ratio
   - reasoning
   - indicators (TechnicalIndicators)
   - risk_reward (RiskReward)
   - relevant_news list
   - news_sentiment

6. **MarketData**
   - market, timestamp
   - OHLCV (open, high, low, close, volume)
   - change_percent

7. **PerformanceMetrics**
   - period, start_date, end_date
   - total_signals, successful_signals, failed_signals, pending_signals
   - win_rate, avg_profit_percent, avg_loss_percent
   - profit_factor, max_consecutive_wins/losses
   - best_trade_percent, worst_trade_percent
   - portfolio tracking (initial, current, total_return_percent)
   - sharpe_ratio, max_drawdown_percent

8. **TelegramMessage**
   - message_type, market, content
   - has_chart, chart_path
   - parse_mode (Markdown/HTML)

**Features:**
- Field validation with Pydantic validators
- JSON encoding configuration
- Decimal precision handling
- Default factories for lists

---

### data/models/ Directory

SQLAlchemy ORM models for database persistence.

#### data/models/__init__.py
```python
"""
SQLAlchemy database models
"""

from data.models.market_data import MarketDataModel
from data.models.signals import SignalModel
from data.models.news import NewsModel
from data.models.performance import PerformanceModel

__all__ = [
    "MarketDataModel",
    "SignalModel",
    "NewsModel",
    "PerformanceModel"
]
```

#### data/models/market_data.py
**Table:** `market_data`
**Purpose:** Historical OHLCV data storage
**Columns:**
- id (PK), time (timestamp with timezone), market, timeframe
- open, high, low, close, volume
- change_percent
- indicators (JSONB for flexible technical indicators)
- market_metadata (JSONB)

**Indexes:**
- idx_market_time (market, time)
- idx_time_market (time, market)

#### data/models/news.py
**Table:** `news`
**Purpose:** News articles with sentiment analysis
**Columns:**
- id (PK), fetched_at, published_at (indexed)
- title, summary, turkish_summary, source, url
- sentiment_score, sentiment_label, impact (indexed)
- related_markets (JSONB array)
- signal_metadata (JSONB)

**Indexes:**
- idx_news_published (published_at)
- idx_news_impact (impact)

#### data/models/performance.py
**Table:** `performance`
**Purpose:** Performance metrics tracking
**Columns:**
- id (PK), calculated_at
- period, start_date, end_date
- Signal counts: total_signals, successful_signals, failed_signals, pending_signals
- Metrics: win_rate, avg_profit_percent, avg_loss_percent, profit_factor
- Streaks: max_consecutive_wins, max_consecutive_losses
- Extremes: best_trade_percent, worst_trade_percent
- Portfolio: initial_portfolio, current_portfolio, total_return_percent
- Advanced: sharpe_ratio, max_drawdown_percent
- perf_metadata (JSONB)

**Indexes:**
- idx_performance_period (period, start_date)

#### data/models/signals.py
**Table:** `signals`
**Purpose:** AI ensemble trading signals
**Columns:**
- id (PK), time (indexed), market (indexed), timeframe
- signal (BUY/SELL/HOLD), confidence
- Individual AI: gpt4_signal, gpt4_confidence, claude_signal, claude_confidence, gemini_signal, gemini_confidence
- reasoning (text)
- Risk: entry_price, stop_loss, take_profit_1, take_profit_2, risk_reward_ratio, position_size_percent
- news_sentiment
- signal_metadata (JSONB)
- Performance tracking: actual_outcome (indexed), actual_pnl_percent, closed_at

**Indexes:**
- idx_signal_market_time (market, time)
- idx_signal_outcome (actual_outcome)

---

### robots/ Directory

#### robots/__init__.py
```python
# Empty file - robots imported directly in main.py
```

#### robots/market_harvester.py (Robot 1)
**Purpose:** Collect real-time market data and calculate indicators
**Execution:** Synchronous (sync)
**Data Sources:**
- Binance (crypto): BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT
- Polygon.io (forex): USD/TRY (fallback to Alpha Vantage)
- Metals API (commodities): GOLD, SILVER

**Process:**
1. Fetch 200 candles per market for indicator calculations
2. Calculate technical indicators: RSI(14), MACD, Bollinger Bands, EMAs (9, 21, 50, 200)
3. Identify support/resistance levels
4. Determine trend (Bullish/Bearish/Sideways)
5. Write separator row to Google Sheets (marks new batch)
6. Append timestamped market data rows with all indicators

**Google Sheets Columns Written:**
- A: Timestamp
- B: Market (e.g., BTC/USDT)
- C: Price (close)
- D: Change %
- E: Volume
- F-S: Technical indicators
- T: News summary (placeholder, filled by Robot 2)

**Features:**
- Rate limiting between API calls (0.5-1s delays)
- Fallback data sources (Polygon → Alpha Vantage)
- Error handling per market (continues on failures)

---

#### robots/news_analyzer.py (Robot 2)
**Purpose:** Fetch news and perform sentiment analysis with Turkish translation
**Execution:** Async
**Data Sources:**
- NewsAPI (news articles)
- Gemini 2.0 Flash (sentiment analysis + Turkish translation)

**Process:**
1. Fetch news for categories (crypto, forex, commodities)
2. Analyze sentiment using Gemini (score: -1 to +1, label, impact)
3. Generate Turkish summary using Gemini
4. Determine related markets based on keywords
5. Save to database (NewsModel)
6. Update Google Sheets with top news summary

**News Categories:**
- crypto: "bitcoin OR ethereum OR cryptocurrency OR crypto market"
- forex: "USD TRY OR forex OR currency market OR central bank"
- commodities: "gold price OR silver OR commodities"

**Gemini Prompts:**
1. **Sentiment Analysis:**
   - Input: News title + description
   - Output: SENTIMENT_SCORE, SENTIMENT_LABEL, IMPACT, REASONING

2. **Turkish Translation:**
   - Input: English news + sentiment
   - Output: Professional Turkish summary (2-3 sentences) with sentiment emoji

**Database Storage:**
- NewsModel ORM (async session)
- Fields: title, summary, turkish_summary, source, url, sentiment, impact, related_markets

---

#### robots/ai_signal_generator.py (Robot 3)
**Purpose:** Generate AI ensemble trading signals with majority voting
**Execution:** Async
**Dependencies:**
- `ai/ensemble.py` (EnsembleSignalGenerator)
- Google Sheets (read market data + indicators)

**Process:**
1. Read latest market data batch from Google Sheets (after separator)
2. Parse technical indicators from columns
3. Fetch recent news from database (last 24 hours, related to market)
4. Call `EnsembleSignalGenerator.generate_signal()` for each market
5. Calculate risk/reward parameters (entry, SL, TP1, TP2)
6. Write signals to Google Sheets columns V-AA
7. Save signals to database (SignalModel)

**Risk Management Calculation:**
- **Entry Price:** Current price
- **Stop Loss:** Based on signal direction and support/resistance
  - BUY: 2% below entry or support level
  - SELL: 2% above entry or resistance level
- **Take Profit 1:** 2:1 risk/reward ratio
- **Take Profit 2:** 3:1 risk/reward ratio
- **Position Size:** 2% of portfolio (configurable)

**Google Sheets Columns Written:**
- V: GPT-4 signal
- W: Claude signal
- X: Gemini signal
- Y: Ensemble signal (final)
- Z: Confidence %
- AA: Reasoning

**Features:**
- Parallel AI calls (all 3 models simultaneously)
- Timeout handling (30s per model)
- Retry logic (2 attempts per model)
- News context integration

---

#### robots/chart_generator.py (Robot 4)
**Purpose:** Create technical analysis charts for high-confidence signals
**Execution:** Synchronous
**Library:** mplfinance

**Process:**
1. Read latest AI signals from Google Sheets
2. Filter signals by confidence threshold (default: 65%)
3. Fetch 100 hourly candles for each market
4. Create candlestick chart with:
   - Bollinger Bands (dotted lines)
   - Support/Resistance levels (dashed lines)
   - Volume bars
   - Signal indicator in title
5. Save charts to `/tmp/charts/` (or Cloud Storage)

**Chart Features:**
- Green candles (up), Red candles (down)
- Title: "{market} - {emoji} {signal} ({confidence}%)"
- Size: 12x8 inches, 100 DPI
- Format: PNG

**Chart Elements:**
- Candlesticks (OHLC)
- Bollinger Bands (upper: red, middle: blue, lower: green)
- Support level (green dotted)
- Resistance level (red dotted)
- Volume bars at bottom

**File Naming:** `{MARKET_SYMBOL}_chart.png` (e.g., BTC_USDT_chart.png)

---

#### robots/telegram_publisher.py (Robot 5)
**Purpose:** Publish AI signals to Telegram channel with Turkish messages
**Execution:** Synchronous
**Library:** python-telegram-bot

**Process:**
1. Read latest AI signals from Google Sheets
2. Filter by confidence threshold (default: 65%)
3. Format message using professional Turkish templates
4. Send message to Telegram channel
5. Send charts for top signals (if available)

**Message Format:**
- Header: "MyTrade AI Signals" with timestamp
- Summary: Count of BUY/SELL/HOLD signals
- Top N signals (default: 5) with:
  - Market and price
  - Signal and confidence
  - RSI and trend
  - AI model votes (GPT-4, Claude, Gemini)
  - Reasoning (truncated to 150 chars)
- Footer: Disclaimer + AI attribution

**Chart Sending:**
- Sends up to 5 charts for highest confidence signals
- Caption: "{market} - {signal} ({confidence}%)"
- 1-second delay between chart uploads

**Features:**
- HTML parse mode for formatting
- Signal emoji (🚀 BUY, 🔻 SELL, ⏸ HOLD)
- Confidence color coding (🟢 high, 🟡 medium, 🔴 low)
- Prioritizes actionable signals (BUY/SELL over HOLD)

---

#### robots/performance_tracker.py (Robot 6)
**Purpose:** Track signal outcomes and calculate performance metrics
**Execution:** Async
**Dependencies:**
- data/models/* (SignalModel, PerformanceModel, MarketDataModel)
- core/database.py

**Process:**

**Phase 1: Update Signal Outcomes**
1. Query pending signals (actual_outcome = "pending")
2. Fetch latest market price for each signal
3. Check if TP or SL hit:
   - **BUY signals:**
     - If price <= stop_loss → "hit_sl"
     - If price >= take_profit_2 → "hit_tp2"
     - If price >= take_profit_1 → "hit_tp1"
   - **SELL signals:**
     - If price >= stop_loss → "hit_sl"
     - If price <= take_profit_2 → "hit_tp2"
     - If price <= take_profit_1 → "hit_tp1"
4. Calculate actual P&L percentage
5. Update signal record with outcome and closed_at timestamp

**Phase 2: Calculate Performance Metrics**
1. Query signals for period (daily/weekly/monthly)
2. Calculate:
   - Win rate: successful_signals / total_signals
   - Average profit/loss percentages
   - Profit factor: |sum(profits) / sum(losses)|
   - Max consecutive wins/losses
   - Best/worst trades
   - Portfolio simulation (starting $10,000)
   - Total return percentage
3. Save to PerformanceModel table

**Performance Metrics:**
- Total signals, successful, failed, pending
- Win rate %
- Average profit/loss %
- Profit factor
- Max consecutive streaks
- Best/worst trade %
- Portfolio tracking ($10k initial)
- Total return %

---

### utils/ Directory

#### utils/__init__.py
```python
# Empty file
```

#### utils/api_clients.py
**Purpose:** API clients for market data providers
**Classes:**

1. **BinanceClient**
   - **Methods:**
     - `get_price(symbol)`: Current price
     - `get_24h_ticker(symbol)`: 24h stats (price, change, volume, high, low)
     - `get_klines(symbol, interval='1h', limit=100)`: Historical candles
   - **Endpoint:** https://api.binance.com
   - **Free:** Yes, no API key required for public endpoints

2. **PolygonClient**
   - **Methods:**
     - `get_forex_price(from_currency, to_currency)`: Current FX price (bid/ask)
     - `get_forex_candles(from, to, timespan='hour', limit=100)`: Historical FX candles
   - **Endpoint:** https://api.polygon.io
   - **Cost:** $199/month (Premium)

3. **AlphaVantageClient**
   - **Methods:**
     - `get_forex_price(from_currency, to_currency)`: FX exchange rate
     - `get_crypto_price(symbol, market='USD')`: Crypto price
     - `get_forex_candles(from, to, interval='60min', limit=100)`: FX candles
   - **Endpoint:** https://www.alphavantage.co/query
   - **Cost:** $49/month (Premium)

4. **GoldPriceClient**
   - **Methods:**
     - `get_gold_price()`: XAU/USD spot price
     - `get_silver_price()`: XAG/USD spot price
   - **Endpoint:** https://api.metals.live/v1/spot
   - **Free:** Yes

**Features:**
- Session management (requests.Session())
- Timeout handling (10-15s)
- Error logging
- Data normalization (timestamp, OHLCV format)

---

#### utils/auth.py
**Purpose:** Google Sheets authentication using Workload Identity
**Function:** `get_gspread_client()`

**Authentication Flow:**
1. Define scopes: spreadsheets, drive
2. Call `google.auth.default(scopes)` (auto-detects credentials)
3. Authorize gspread client
4. Return authenticated client

**Credential Sources (priority):**
1. **Cloud Run/GCP:** Workload Identity (automatic)
2. **Local Dev:** GOOGLE_APPLICATION_CREDENTIALS env var (service account JSON)

**Features:**
- Zero-config in GCP environments
- Automatic service account detection
- Comprehensive error handling

---

#### utils/secrets.py
**Purpose:** Secret Manager with .env fallback
**Function:** `get_secret(name, required=True, default=None, ...)`

**Retrieval Priority:**
1. **Secret Manager:** projects/{PROJECT_ID}/secrets/{name}/versions/latest
2. **Environment:** os.getenv(name)
3. **Default:** Return default value

**Parameters:**
- name: Secret name
- required: Raise error if not found
- default: Fallback value
- project_id: GCP project (auto-detected from env)
- version: Secret version (default: "latest")
- cache: Cache value in memory (default: True)
- as_json: Parse as JSON (default: False)
- strip: Strip whitespace (default: True)

**Features:**
- In-memory caching
- JSON parsing support
- Graceful fallback to .env
- Comprehensive error handling (NotFound, PermissionDenied, etc.)

---

#### utils/schema.py
**Purpose:** Google Sheets column schema definition
**Constants:**

**HEADERS_TR** (38 columns):
```python
[
    "Tarih/Saat",           # A: Timestamp
    "Piyasa",               # B: Market
    "Fiyat",                # C: Price
    "Değişim (%)",          # D: Change %
    "Hacim",                # E: Volume
    "RSI (14)",             # F: RSI
    "MACD",                 # G: MACD line
    "MACD Sinyal",          # H: MACD signal
    "MACD Histogram",       # I: MACD histogram
    "BB Üst",               # J: Bollinger upper
    "BB Orta",              # K: Bollinger middle
    "BB Alt",               # L: Bollinger lower
    "EMA 9",                # M: EMA 9
    "EMA 21",               # N: EMA 21
    "EMA 50",               # O: EMA 50
    "EMA 200",              # P: EMA 200
    "Destek",               # Q: Support level
    "Direnç",               # R: Resistance level
    "Trend",                # S: Trend
    "Haber Özeti",          # T: News summary
    "Haber Duyarlılık",     # U: News sentiment
    "GPT-4 Sinyal",         # V: GPT-4 signal
    "Claude Sinyal",        # W: Claude signal
    "Gemini Sinyal",        # X: Gemini signal
    "Ensemble Sinyal",      # Y: Final signal
    "Güven (%)",            # Z: Confidence
    "AI Açıklama",          # AA: Reasoning
    "Giriş Fiyatı",         # AB: Entry price
    "Stop Loss",            # AC: Stop loss
    "TP1",                  # AD: Take profit 1
    "TP2",                  # AE: Take profit 2
    "Risk/Reward",          # AF: R/R ratio
    "Pozisyon Boyutu (%)",  # AG: Position size
    "Kaynak",               # AH: Data source
]
```

**Functions:**
- `create_header_row()`: Returns header list
- `resolve_columns(worksheet)`: Maps headers to column indices
- `_normalize(text)`: Normalize header strings for comparison

**Cols Class:**
- Provides attribute access to column numbers (e.g., `cols.A = 1, cols.B = 2`)
- Supports aliases (Turkish/English variations)

---

#### utils/openai_wrapper.py
**Purpose:** OpenAI GPT-4 API wrapper for trading signals
**Class:** `OpenAIClient`

**Methods:**
- `__init__(api_key, model='gpt-4-turbo-preview')`
- `analyze_market(market, price, indicators, news_sentiment, max_retries=3)`
- `_build_prompt(...)`: Construct analysis prompt
- `_parse_response(content, market)`: Extract signal/confidence/reasoning

**Prompt Structure:**
```
Analyze {market} and provide a trading signal.

Current Price: $X,XXX.XX

Technical Indicators:
- RSI: XX.X
- MACD: X.XX
- MACD Signal: X.XX
- Bollinger Bands: Upper=XX, Lower=XX
- EMA 9: XX
- EMA 21: XX
- Trend: Bullish/Bearish/Sideways

[Optional] News Sentiment: ...

Provide your analysis in this exact format:
SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [Brief explanation in 1-2 sentences]
```

**Model Settings:**
- temperature: 0.3 (deterministic)
- max_tokens: 500

**Response Parsing:**
- Extract SIGNAL, CONFIDENCE, REASONING from structured output
- Return dict with market, signal, confidence, reasoning, ai_model

**Convenience Function:**
```python
get_openai_signal(market, price, indicators, news_sentiment)
```

---

#### utils/claude_wrapper.py
**Purpose:** Anthropic Claude API wrapper
**Class:** `ClaudeClient`

**Similar structure to OpenAI wrapper with differences:**
- Model: `claude-opus-4-20250514`
- API: Anthropic Messages API
- System prompt: "Expert financial analyst with deep knowledge of technical analysis, market psychology, and risk management"
- More detailed technical indicators in prompt (includes MACD histogram, support/resistance)

**Model Settings:**
- temperature: 0.3
- max_tokens: 1024

**Convenience Function:**
```python
get_claude_signal(market, price, indicators, news_sentiment)
```

---

#### utils/gemini_wrapper.py
**Purpose:** Google Gemini API wrapper
**Class:** `GeminiClient`

**Unique Features:**
- Model: `gemini-2.5-pro`
- Chat session interface (start_chat)
- Generation config: temperature=0.3, top_p=0.95, top_k=40
- Safety settings: BLOCK_NONE (permissive for financial analysis)
- System instruction: "Expert quantitative analyst and trader with expertise in technical analysis, market microstructure, and algorithmic trading"

**Prompt Structure:**
- More detailed Markdown formatting
- Comprehensive indicator list
- Task-oriented instructions

**Convenience Function:**
```python
get_gemini_signal(market, price, indicators, news_sentiment)
```

---

#### utils/indicators.py
**Purpose:** Technical indicator calculations
**Class:** `TechnicalIndicators` (static methods)

**Methods:**

1. **prepare_dataframe(candles):**
   - Convert candle list to pandas DataFrame
   - Set timestamp as index
   - Return OHLCV DataFrame

2. **calculate_rsi(df, period=14):**
   - Uses pandas_ta if available, else manual calculation
   - RSI formula: 100 - (100 / (1 + RS))
   - RS = Average Gain / Average Loss

3. **calculate_macd(df, fast=12, slow=26, signal=9):**
   - MACD line = EMA(fast) - EMA(slow)
   - Signal line = EMA(MACD, signal)
   - Histogram = MACD - Signal
   - Returns tuple: (macd_line, signal_line, histogram)

4. **calculate_bollinger_bands(df, period=20, std=2.0):**
   - Middle = SMA(period)
   - Upper = Middle + (STD * std)
   - Lower = Middle - (STD * std)
   - Returns tuple: (upper, middle, lower)

5. **calculate_ema(df, period):**
   - Exponential Moving Average
   - More weight to recent prices

6. **find_support_resistance(df, lookback=100, num_levels=2):**
   - Identifies local minima (support) and maxima (resistance)
   - Looks for pivot points (lower/higher than 2 neighbors on each side)
   - Returns top N levels sorted

7. **determine_trend(df):**
   - Compares EMA 9, 21, 50 with current price
   - Bullish: price > EMA9 > EMA21 > EMA50
   - Bearish: price < EMA9 < EMA21 < EMA50
   - Sideways: Otherwise

8. **calculate_all(candles):**
   - One-shot calculation of all indicators
   - Returns dict with all metrics
   - Handles missing data gracefully

**Dependencies:**
- pandas_ta (preferred, full TA-Lib implementation)
- Fallback: Manual calculations if pandas_ta unavailable

---

#### utils/health_check.py
**Purpose:** Comprehensive health monitoring system
**Class:** `HealthChecker`

**Components Monitored:**
1. Database (CloudSQL/SQLite)
2. Google Sheets API
3. OpenAI API
4. Anthropic Claude API
5. Google Gemini API
6. Telegram Bot API
7. Binance API

**Check Methods:**
- `check_database()`: SELECT 1 query
- `check_google_sheets()`: Read worksheet row count
- `check_openai()`: Simple completion test (gpt-3.5-turbo)
- `check_claude()`: Simple message test (claude-3-haiku)
- `check_gemini()`: Simple generation test (gemini-pro)
- `check_telegram()`: Bot.get_me() call
- `check_binance()`: Fetch BTC/USDT ticker

**Status Levels:**
- **HEALTHY:** Component working normally
- **WARNING:** Non-critical issue (missing config, degraded performance)
- **CRITICAL:** Component unavailable, system may fail

**Parallel Execution:**
```python
checks = [check1(), check2(), ...]
results = await asyncio.gather(*checks, return_exceptions=True)
```

**Alert System:**
- Sends Telegram alerts for CRITICAL issues
- Sends Telegram alerts for WARNING issues (if no CRITICAL)
- Logs summary with counts

**Convenience Function:**
```python
async def run_health_check(send_alerts=True) -> Dict[str, HealthStatus]
```

---

#### utils/storage.py
**Purpose:** Cloud Storage utilities for chart management
**Class:** `StorageClient`

**Methods:**

1. **__init__(bucket_name, local_dir='/tmp/charts'):**
   - Initializes GCS client if bucket_name provided
   - Falls back to local storage if GCS unavailable
   - Creates local directory if needed

2. **upload_chart(local_path, market, make_public=True):**
   - Uploads chart to GCS bucket (if enabled)
   - Makes blob public or generates signed URL (1-hour expiry)
   - Returns public URL or local file path
   - Remote path: `charts/{timestamp}_{market}.png`

3. **delete_old_charts(days=7):**
   - Deletes charts older than specified days
   - Works for both GCS and local storage
   - Cleanup automation

4. **list_charts(limit=100):**
   - Lists recent charts
   - Returns URLs (GCS) or file paths (local)

**Convenience Function:**
```python
def get_storage_client(bucket_name=None) -> StorageClient
```

**Features:**
- Graceful degradation (GCS → local)
- Timestamp-based naming
- Content-type handling (image/png)
- Public/private access control

---

#### utils/structured_logging.py
**Purpose:** Production-grade structured logging
**Classes:**

1. **JSONFormatter (logging.Formatter):**
   - Formats logs as JSON
   - Fields: timestamp, level, logger, message, module, function, line
   - Exception handling: type, message, traceback
   - Custom fields: extra_fields, request_id, robot_id

2. **ColoredConsoleFormatter (logging.Formatter):**
   - ANSI color codes for development
   - Colors: DEBUG (cyan), INFO (green), WARNING (yellow), ERROR (red), CRITICAL (magenta)
   - Format: `[HH:MM:SS] LEVEL - logger - message`

**Functions:**

1. **setup_logging(environment, log_level, enable_json, enable_cloud_logging):**
   - Configures root logger
   - Chooses formatter based on environment
   - Console handler to stdout
   - Optional Google Cloud Logging handler
   - Sets specific logger levels (suppress urllib3, googleapiclient, etc.)

2. **get_logger(name, **extra_fields):**
   - Returns logger with optional context fields
   - Uses LoggerAdapter for extra fields

**Decorators:**

1. **@log_execution_time(logger=None):**
   - Logs function execution time
   - Catches exceptions and logs with timing
   - Adds execution_time to log entry

2. **@log_async_execution_time(logger=None):**
   - Async version of execution time decorator

**Auto-Setup:**
- Configures logging on import if not already configured
- Uses environment variables: ENVIRONMENT, ENABLE_JSON_LOGGING, ENABLE_CLOUD_LOGGING

---

#### utils/telegram_notifier.py
**Purpose:** Telegram notification system
**Functions:**

1. **send_telegram_message(message, parse_mode='Markdown'):**
   - Sends message to configured chat
   - Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from secrets
   - Returns success boolean

2. **send_error_notification(robot_name, error, attempt, max_retries):**
   - Formats error alert with timestamp
   - Shows retry status
   - Includes error message (truncated to 200 chars)

3. **send_status_notification(message):**
   - General status notification
   - Adds timestamp automatically

4. **send_health_alert(component, status, details):**
   - Health check notification
   - Emoji based on status (✅ HEALTHY, ⚠️ WARNING, 🔴 CRITICAL)
   - Shows component and details

5. **send_performance_report(period, win_rate, total_signals, return_percent):**
   - Performance summary notification
   - Shows win rate, signal count, return
   - Emoji based on performance (🎉 >5%, ✅ >0%, ⚠️ negative)

**Sync Wrappers:**
- `send_error_notification_sync()`
- `send_status_notification_sync()`

**Features:**
- Async-first design
- Graceful failure (logs error, returns False)
- Emoji-rich messages
- Markdown formatting

---

#### utils/telegram_formatter.py
**Purpose:** Professional Turkish message formatting
**Class:** `TelegramMessageFormatter`

**Message Types:**

1. **format_hourly_update(market, price, indicators, price_change_24h):**
   - Header: "SAATLİK PİYASA GÜNCELLEMESİ"
   - Shows price, 24h change, RSI, MACD, trend
   - Simple format for hourly monitoring

2. **format_pre_session(session_name, session_time, market, price, indicators, news_items):**
   - Header: "{SESSION} SEANSI ÖN ANALİZ"
   - 1 hour before session analysis
   - Prediction based on indicators (YUKARIŞ/DÜŞÜŞ/YATAY)
   - Technical indicator details
   - News context with Turkish summaries
   - Reasoning based on bullish/bearish signals

3. **format_session_open(session_name, signal, risk_params):**
   - Header: "{SESSION} SEANSI AÇILIŞ SİNYALİ"
   - Full AI ensemble signal
   - Individual model votes (GPT-4, Claude, Gemini)
   - Confidence level (color-coded)
   - Technical indicators
   - Risk management (entry, SL, TP1, TP2, position size, R/R)
   - News sentiment
   - Top 3 relevant news (Turkish summaries)

4. **format_peak_volatility(market, price, price_change_1h, indicators):**
   - Header: "YÜKSEK VOLATİLİTE DÖNEMİ"
   - London + New York overlap warning
   - 1-hour price change
   - Quick RSI/MACD snapshot
   - Stop loss reminder

5. **format_daily_summary(total_signals, successful_signals, win_rate, total_return, top_market, top_return):**
   - Header: "GÜNLÜK PERFORMANS ÖZETİ"
   - Performance emoji based on return
   - Total signals, success rate, return %
   - Best performing market
   - Advice based on win rate

6. **format_weekly_summary(week_number, total_signals, successful_signals, win_rate, total_return, best_day, best_day_return):**
   - Header: "HAFTALIK PERFORMANS ÖZETİ"
   - Weekly stats (average daily signals, return)
   - Best day performance
   - Weekly insights and advice

7. **format_news_bulletin(news_items):**
   - Header: "PİYASA HABERLERİ"
   - Top 5 news with:
     - Sentiment emoji (🟢 positive, 🔴 negative, 🟡 neutral)
     - Impact emoji (🔥 HIGH, 📊 MEDIUM, 📝 LOW)
     - Title and summary
     - Sentiment label

**Emoji Mappings:**
- Sessions: 🇬🇧 LONDON, 🇺🇸 NEW_YORK, 🇯🇵 ASIAN
- Signals: 📈 BUY, 📉 SELL, ➡️ HOLD
- Confidence: 🟢 ≥75%, 🟡 ≥60%, 🔴 <60%
- Performance: 🎉 >5%, ✅ >0%, ⚠️ <0%

**Features:**
- Professional Turkish language
- Emoji-rich formatting
- Context-aware messaging
- Confidence-based styling
- News integration with Turkish summaries

---

### tests/ Directory

#### tests/__init__.py
```python
"""
Test suite for MyTrade
"""
```

#### tests/conftest.py
**Purpose:** Pytest configuration and shared fixtures
**Fixtures:**

1. **event_loop (session scope):**
   - Creates event loop for async tests
   - Yields loop, closes on teardown

2. **db_session (function scope):**
   - Initializes test database (SQLite)
   - Provides async session
   - Cleans up database after test

3. **mock_telegram_config:**
   - Mocks TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

4. **mock_ai_config:**
   - Mocks OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY

5. **sample_indicators:**
   - Returns TechnicalIndicators instance with sample data

6. **sample_news_item:**
   - Returns NewsItem instance with sample data

**Environment Setup:**
- Sets ENVIRONMENT=development
- Sets SQLITE_PATH=/tmp/mytrade_test.db
- Sets LOG_LEVEL=WARNING (reduce test noise)

---

#### tests/test_telegram_formatter.py
**Purpose:** Test suite for TelegramMessageFormatter
**Tests:**

1. **test_format_hourly_update:**
   - Validates hourly update message structure
   - Checks for "SAATLİK PİYASA GÜNCELLEMESİ" header
   - Verifies market data inclusion

2. **test_format_pre_session:**
   - Tests pre-session analysis formatting
   - Checks session name and time
   - Verifies prediction logic

3. **test_format_session_open:**
   - Tests full signal message
   - Validates AI model vote display
   - Checks confidence color coding
   - Verifies risk parameter inclusion

4. **test_format_peak_volatility:**
   - Tests volatility warning message
   - Checks "YÜKSEK VOLATİLİTE DÖNEMİ" header

5. **test_format_daily_summary:**
   - Tests daily performance report
   - Validates performance emoji logic

6. **test_format_weekly_summary:**
   - Tests weekly performance report
   - Checks weekly statistics

7. **test_format_news_bulletin:**
   - Tests news bulletin formatting
   - Validates sentiment emoji mapping

**Coverage:**
- Message structure validation
- Emoji mapping correctness
- Data inclusion checks
- Format consistency

---

## Key Configuration Files

### .gitignore
**Excluded from version control:**
- **Python:** `__pycache__/`, `*.pyc`, `venv/`, `env/`
- **IDE:** `.vscode/`, `.idea/`
- **Sensitive:** `.env`, `.env.local`, `service_account.json`, `gcp-credentials.json`
- **Generated:** `*.log`, `.pytest_cache/`, `htmlcov/`
- **System:** `.DS_Store`, `Thumbs.db`
- **Media:** `media/` (with `.gitkeep`)
- **Temp:** `tmp/`, `temp/`, `*.tmp`

### .dockerignore
**Excluded from Docker build:**
- `.git`, `.gitignore`, `README.md`
- `.env`, `.env.local`
- `__pycache__/`, `*.pyc`
- `venv/`, `env/`
- `.vscode/`, `.idea/`
- `*.log`, `media/`, `tmp/`
- `.DS_Store`

### .gcloudignore
**Excluded from gcloud deployment:**
- `.git`, `.gitignore`, `.env`, `.env.local`
- `.vscode/`, `.idea/`
- `__pycache__/`, `*.pyc`
- `*.log`, `README.md`, `media/`, `tmp/`

---

## Deployment & Infrastructure

### Google Cloud Run Job

**Configuration:**
- **Region:** europe-west1
- **Service Account:** robot@{PROJECT_ID}.iam.gserviceaccount.com
- **Resources:**
  - CPU: 2 cores
  - Memory: 4GB
- **Timeout:** 3600 seconds (1 hour)
- **Max Retries:** 1
- **Execution Environment:** Second generation

**Secrets (from Secret Manager):**
- GOOGLE_SHEET_ID
- POLYGON_API_KEY
- ALPHA_VANTAGE_KEY
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

**Environment Variables:**
- GCP_PROJECT
- SHEET_TAB=MarketData
- CANDLE_LIMIT=200
- ROBOT=1,2,3,4,5,6 (configurable per schedule)

### Cloud Scheduler Jobs

**Example job creation:**
```bash
gcloud scheduler jobs create http mytrade-london-open \
  --location=europe-west1 \
  --schedule="0 11 * * *" \
  --time-zone="Europe/Istanbul" \
  --uri="https://run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/mytrade-automation-job:run" \
  --http-method=POST \
  --oauth-service-account-email=robot@{PROJECT_ID}.iam.gserviceaccount.com \
  --message-body='{"overrides": {"containerOverrides": [{"env": [{"name": "ROBOT", "value": "1,2,3,4,5,6"}, {"name": "MIN_CONFIDENCE", "value": "65"}]}]}}'
```

**Job Schedule:**
- Hourly: `0 * * * *`
- Pre-London: `0 10 * * *`
- London Open: `0 11 * * *`
- Pre-NY: `0 15 * * *`
- NY Open: `0 16 * * *`
- Peak: `0 17 * * *`
- Daily: `0 20 * * *`
- Weekly: `0 21 * * FRI`

### CloudSQL PostgreSQL

**Connection:**
- **Method:** Unix socket (`/cloudsql/{CONNECTION_NAME}`)
- **Driver:** asyncpg (async PostgreSQL)
- **Pool:** 10 base + 20 overflow = 30 max connections
- **Recycle:** 3600s (1 hour)
- **Timeout:** 30s (pool), 60s (query)

**Tables:**
- market_data (OHLCV + indicators)
- news (articles + sentiment)
- signals (AI ensemble signals)
- performance (metrics tracking)

### Cloud Build Pipeline

**Trigger:** Manual or git push
**Steps:**
1. Build Docker image
2. Push to Artifact Registry
3. Deploy to Cloud Run Job
4. Update scheduler if needed

**Build Time:** ~5-10 minutes (includes TA-Lib compilation)

---

## Summary Statistics

**Total Files:** 45 Python files + 8 configuration files
**Lines of Code:** ~8,000+ (estimated)
**Dependencies:** 40+ Python packages
**AI Models:** 3 (GPT-4, Claude Opus 4, Gemini 2.5 Pro)
**Data Sources:** 6 APIs (Binance, Polygon, Alpha Vantage, NewsAPI, Metals, Google Sheets)
**Robots:** 6 specialized automation components
**Database Tables:** 4 (market_data, news, signals, performance)
**Cloud Services:** 5 (Cloud Run, Cloud SQL, Cloud Storage, Secret Manager, Cloud Scheduler)
**Languages:** Python (backend), Turkish (user-facing messages)
**Testing:** pytest with async support, fixtures, mocking

---

## Important Patterns & Architecture Decisions

### 1. **Why Async/Await?**
- Parallel AI model calls (3x speedup)
- Database connection pooling efficiency
- Non-blocking I/O for API calls
- Improved Cloud Run resource utilization

### 2. **Why PostgreSQL + Google Sheets?**
- **PostgreSQL:** Structured data, SQL queries, performance metrics
- **Google Sheets:** Real-time dashboard, easy visualization, manual overrides

### 3. **Why Majority Voting?**
- Reduces individual model bias
- Increases confidence in signals
- Provides transparency (show all votes)
- Improves robustness against API failures

### 4. **Why Turkish Language?**
- Target audience: Turkish traders
- Professional financial terminology
- Cultural context for news analysis

### 5. **Why 6 Robots?**
- **Separation of Concerns:** Each robot has one responsibility
- **Independent Failure:** One robot failure doesn't stop others
- **Flexible Scheduling:** Run different combinations per schedule
- **Maintainability:** Easier to debug and update

### 6. **Why Cloud Run Jobs vs Functions?**
- **Long-running:** AI analysis takes 1-5 minutes
- **Resource control:** 2 CPU, 4GB memory
- **Retry logic:** Built-in retry mechanism
- **Scheduled execution:** Native Cloud Scheduler integration

### 7. **Why Connection Pooling?**
- **Performance:** Reuse connections (avoid handshake overhead)
- **Scalability:** Handle concurrent operations
- **Reliability:** Pool pre-ping detects stale connections

### 8. **Why Structured Logging?**
- **Debugging:** JSON logs easily searchable
- **Monitoring:** Cloud Logging integration
- **Tracing:** Request/robot ID tracking
- **Performance:** Execution time tracking

---

## Recreation Instructions

To recreate this project in a new repository:

1. **Clone structure:**
   ```bash
   mkdir -p mytrade/{ai,core,data/models,robots,tests,utils}
   ```

2. **Copy source files** from this analysis document to respective directories

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # OR (if TA-Lib compilation issues)
   pip install -r requirements-minimal.txt
   ```

4. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Initialize Google Sheets:**
   ```bash
   python setup_sheets.py --name "MyTrade Automation"
   # Copy GOOGLE_SHEET_ID to .env
   ```

6. **Test locally:**
   ```bash
   export ENVIRONMENT=development
   export ROBOT=1  # Test individual robots
   python main.py
   ```

7. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

8. **Deploy to Cloud Run:**
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

9. **Setup Cloud Scheduler:**
   - Use commands from `scheduler_config.yaml`
   - Create jobs for each schedule

10. **Monitor:**
    ```bash
    python health_check.py
    ```

---

**End of Analysis**

This document contains the complete source code and architecture documentation for the MyTrade trading automation system. All files, dependencies, and design decisions have been documented for easy recreation.
