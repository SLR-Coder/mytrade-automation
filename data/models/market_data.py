# -*- coding: utf-8 -*-
"""
Market data database model
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, Index, JSON
from core.database import Base


class MarketDataModel(Base):
    """Market OHLCV data"""

    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    market = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, default="1h")

    # OHLCV
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    # Change
    change_percent = Column(Float)

    # Technical indicators (stored as JSON for compatibility with both PostgreSQL and SQLite)
    indicators = Column(JSON, default={})

    # Composite index for faster queries
    __table_args__ = (
        Index('idx_market_time', 'market', 'time'),
        Index('idx_time_market', 'time', 'market'),
    )

    def __repr__(self):
        return f"<MarketData {self.market} {self.time} close={self.close}>"