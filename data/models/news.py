# -*- coding: utf-8 -*-
"""
News database model
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, Text, Index, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from core.database import Base


class NewsModel(Base):
    """News items with sentiment analysis"""

    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # News content
    title = Column(Text, nullable=False)
    summary = Column(Text)
    turkish_summary = Column(Text)  # Turkish translation/summary
    source = Column(String(100), nullable=False)
    url = Column(Text)

    # Sentiment analysis
    sentiment_score = Column(Float)  # -1 to +1
    sentiment_label = Column(String(20))  # positive, negative, neutral
    impact = Column(String(10))  # HIGH, MEDIUM, LOW

    # Related markets
    related_markets = Column(JSONB, default=[])

    # Metadata
    signal_metadata = Column(JSONB, default={})

    __table_args__ = (
        Index('idx_news_published', 'published_at'),
        Index('idx_news_impact', 'impact'),
    )

    def __repr__(self):
        return f"<News '{self.title[:50]}' sentiment={self.sentiment_score}>"