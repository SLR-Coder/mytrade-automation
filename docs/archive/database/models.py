# -*- coding: utf-8 -*-
"""
Pydantic models for type-safe data handling
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class TechnicalIndicators(BaseModel):
    """Technical indicators model"""
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    support_levels: List[float] = Field(default_factory=list)
    resistance_levels: List[float] = Field(default_factory=list)
    trend: Optional[str] = None  # "bullish", "bearish", "sideways"

    class Config:
        json_encoders = {
            float: lambda v: round(v, 8) if v else None
        }


class NewsItem(BaseModel):
    """News item model"""
    title: str
    summary: Optional[str] = None
    turkish_summary: Optional[str] = None  # Turkish translation/summary
    source: str
    published_at: datetime
    url: Optional[str] = None
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    sentiment_label: Optional[str] = None  # "positive", "negative", "neutral"
    impact: Optional[str] = None  # "HIGH", "MEDIUM", "LOW"
    related_markets: List[str] = Field(default_factory=list)


class AISignal(BaseModel):
    """Individual AI model signal"""
    model: str  # "gpt4", "claude", "gemini"
    signal: str  # "BUY", "SELL", "HOLD"
    confidence: int = Field(..., ge=0, le=100)
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RiskReward(BaseModel):
    """Risk/reward calculation"""
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    risk_amount: float
    reward_amount_1: float
    reward_amount_2: Optional[float] = None
    risk_reward_ratio_1: float
    risk_reward_ratio_2: Optional[float] = None
    position_size_percent: float = Field(..., ge=0.1, le=5.0)  # % of portfolio

    @validator('stop_loss')
    def validate_stop_loss(cls, v, values):
        if 'entry_price' in values and 'signal' in values:
            entry = values['entry_price']
            if values['signal'] == 'BUY' and v >= entry:
                raise ValueError("Stop loss must be below entry for BUY")
            if values['signal'] == 'SELL' and v <= entry:
                raise ValueError("Stop loss must be above entry for SELL")
        return v


class EnsembleSignal(BaseModel):
    """Ensemble signal from multiple AI models"""
    market: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    current_price: float

    # Individual AI signals
    ai_signals: List[AISignal]

    # Ensemble result
    final_signal: str  # "BUY", "SELL", "HOLD"
    confidence: int = Field(..., ge=0, le=100)
    consensus_ratio: float = Field(..., ge=0.0, le=1.0)  # e.g., 0.66 = 2/3
    reasoning: str

    # Technical context
    indicators: Optional[TechnicalIndicators] = None

    # Risk management
    risk_reward: Optional[RiskReward] = None

    # News context
    relevant_news: List[NewsItem] = Field(default_factory=list)
    news_sentiment: Optional[float] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MarketData(BaseModel):
    """Market data snapshot"""
    market: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    change_percent: Optional[float] = None


class PerformanceMetrics(BaseModel):
    """Performance tracking metrics"""
    period: str  # "daily", "weekly", "monthly"
    start_date: datetime
    end_date: datetime

    total_signals: int
    successful_signals: int
    failed_signals: int
    pending_signals: int

    win_rate: float = Field(..., ge=0.0, le=100.0)
    avg_profit_percent: float
    avg_loss_percent: float
    profit_factor: float

    max_consecutive_wins: int
    max_consecutive_losses: int

    best_trade_percent: float
    worst_trade_percent: float

    # Simulated portfolio value
    initial_portfolio: float
    current_portfolio: float
    total_return_percent: float

    sharpe_ratio: Optional[float] = None
    max_drawdown_percent: Optional[float] = None


class TelegramMessage(BaseModel):
    """Telegram message model"""
    message_type: str  # "price_update", "signal", "news", "performance"
    market: Optional[str] = None
    content: str
    has_chart: bool = False
    chart_path: Optional[str] = None
    parse_mode: str = "Markdown"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }