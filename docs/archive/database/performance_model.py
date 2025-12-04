# -*- coding: utf-8 -*-
"""
Performance tracking database model
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, Index, JSON
from core.database import Base


class PerformanceModel(Base):
    """Performance metrics tracking"""

    __tablename__ = "performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Period
    period = Column(String(20), nullable=False)  # daily, weekly, monthly
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)

    # Signal counts
    total_signals = Column(Integer, nullable=False, default=0)
    successful_signals = Column(Integer, nullable=False, default=0)
    failed_signals = Column(Integer, nullable=False, default=0)
    pending_signals = Column(Integer, nullable=False, default=0)

    # Metrics
    win_rate = Column(Float, nullable=False, default=0.0)
    avg_profit_percent = Column(Float)
    avg_loss_percent = Column(Float)
    profit_factor = Column(Float)

    max_consecutive_wins = Column(Integer)
    max_consecutive_losses = Column(Integer)

    best_trade_percent = Column(Float)
    worst_trade_percent = Column(Float)

    # Portfolio tracking
    initial_portfolio = Column(Float)
    current_portfolio = Column(Float)
    total_return_percent = Column(Float)

    # Advanced metrics
    sharpe_ratio = Column(Float)
    max_drawdown_percent = Column(Float)

    # Metadata (using JSON for compatibility with both PostgreSQL and SQLite)
    perf_metadata = Column(JSON, default={})

    __table_args__ = (
        Index('idx_performance_period', 'period', 'start_date'),
    )

    def __repr__(self):
        return f"<Performance {self.period} win_rate={self.win_rate:.1f}%>"