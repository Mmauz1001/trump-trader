"""Database models for storing posts, sentiment analysis, and trades."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SocialMediaPost(Base):
    """Model for storing social media posts from Twitter and Truth Social."""

    __tablename__ = "social_media_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    platform = Column(String(20), nullable=False)  # 'TWITTER' or 'TRUTHSOCIAL'
    content = Column(Text, nullable=False)
    post_id = Column(String(100), nullable=True)  # Platform-specific post ID
    posted_at = Column(DateTime, nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    engagement_metrics = Column(Text, nullable=True)  # JSON string

    # Relationship to sentiment analysis
    sentiment = relationship(
        "SentimentAnalysis", back_populates="post", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SocialMediaPost(id={self.id}, platform={self.platform}, posted_at={self.posted_at})>"


class SentimentAnalysis(Base):
    """Model for storing sentiment analysis results from Claude API."""

    __tablename__ = "sentiment_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(
        Integer, ForeignKey("social_media_posts.id", ondelete="CASCADE"), nullable=False
    )
    score = Column(Integer, nullable=False)  # 0-10
    reasoning = Column(Text, nullable=False)
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    model_version = Column(String(50), nullable=False)  # e.g., "claude-3-5-sonnet-20241022"

    # Relationship to post
    post = relationship("SocialMediaPost", back_populates="sentiment")

    # Relationship to trade
    trade = relationship("Trade", back_populates="sentiment", uselist=False)

    def __repr__(self) -> str:
        return f"<SentimentAnalysis(id={self.id}, score={self.score}, analyzed_at={self.analyzed_at})>"


class Trade(Base):
    """Model for storing trade execution details."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sentiment_id = Column(
        Integer, ForeignKey("sentiment_analysis.id"), nullable=False
    )
    
    # Trade details
    symbol = Column(String(20), nullable=False, default="BTCUSDT")
    side = Column(String(10), nullable=False)  # 'LONG' or 'SHORT'
    leverage = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    notional_value = Column(Float, nullable=False)
    
    # Stop-loss details
    fixed_stop_loss_price = Column(Float, nullable=False)
    trailing_callback_rate = Column(Float, nullable=False)
    
    # Execution details
    entry_order_id = Column(String(100), nullable=True)
    stop_loss_order_id = Column(String(100), nullable=True)
    trailing_stop_order_id = Column(String(100), nullable=True)
    
    # Position status
    is_open = Column(Boolean, nullable=False, default=True)
    exit_price = Column(Float, nullable=True)
    exit_order_id = Column(String(100), nullable=True)
    pnl_usd = Column(Float, nullable=True)
    pnl_percentage = Column(Float, nullable=True)
    
    # Timestamps
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    # Close reason
    close_reason = Column(String(100), nullable=True)  # e.g., "TRAILING_STOP", "NEW_SIGNAL", "MANUAL"
    
    # Relationship to sentiment
    sentiment = relationship("SentimentAnalysis", back_populates="trade")

    def __repr__(self) -> str:
        status = "OPEN" if self.is_open else "CLOSED"
        return f"<Trade(id={self.id}, side={self.side}, leverage={self.leverage}x, status={status})>"


class SystemLog(Base):
    """Model for storing system events and errors."""

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)  # 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    module = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    exception = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SystemLog(id={self.id}, level={self.level}, module={self.module})>"

