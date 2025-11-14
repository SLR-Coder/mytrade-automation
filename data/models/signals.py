# -*- coding: utf-8 -*-
"""
AI signals database model
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from core.database import Base


class SignalModel(Base):
    """AI ensemble signals"""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True, default=datetime.utcnow)
    market = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, default="1h")

    # Signal
    signal = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Integer, nullable=False)  # 0-100

    # Individual AI signals
    gpt4_signal = Column(String(10))
    gpt4_confidence = Column(Integer)
    claude_signal = Column(String(10))
    claude_confidence = Column(Integer)
    gemini_signal = Column(String(10))
    gemini_confidence = Column(Integer)

    # Reasoning
    reasoning = Column(Text)

    # Risk/Reward
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)
    risk_reward_ratio = Column(Float)
    position_size_percent = Column(Float)

    # News sentiment
    news_sentiment = Column(Float)  # -1 to +1

    # Metadata
    signal_metadata = Column(JSONB, default={})

    # Performance tracking (updated after signal closes)
    actual_outcome = Column(String(20))  # "hit_tp1", "hit_tp2", "hit_sl", "pending"
    actual_pnl_percent = Column(Float)
    closed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('idx_signal_market_time', 'market', 'time'),
        Index('idx_signal_outcome', 'actual_outcome'),
    )

    def __repr__(self):
        return f"<Signal {self.market} {self.signal} confidence={self.confidence}%>"