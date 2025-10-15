"""Database repository for CRUD operations."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from src.database.models import Base, SentimentAnalysis, SocialMediaPost, SystemLog, Trade
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseRepository:
    """Repository for database operations."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database repository.

        Args:
            database_url: Optional database URL override
        """
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        logger.info(f"Database repository initialized: {self.database_url}")

    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created successfully")

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    # Social Media Posts
    def create_post(
        self,
        content_hash: str,
        platform: str,
        content: str,
        posted_at: datetime,
        post_id: Optional[str] = None,
        engagement_metrics: Optional[str] = None,
    ) -> SocialMediaPost:
        """Create a new social media post record."""
        with self.get_session() as session:
            post = SocialMediaPost(
                content_hash=content_hash,
                platform=platform,
                content=content,
                post_id=post_id,
                posted_at=posted_at,
                fetched_at=datetime.now(timezone.utc),
                engagement_metrics=engagement_metrics,
            )
            session.add(post)
            session.commit()
            session.refresh(post)
            logger.info(f"Created post record: {post.id} from {platform}")
            return post

    def get_post_by_hash(self, content_hash: str) -> Optional[SocialMediaPost]:
        """Get post by content hash."""
        with self.get_session() as session:
            return session.query(SocialMediaPost).filter_by(content_hash=content_hash).first()

    def post_exists(self, content_hash: str) -> bool:
        """Check if post already exists."""
        return self.get_post_by_hash(content_hash) is not None

    def get_recent_posts(self, limit: int = 10) -> List[SocialMediaPost]:
        """Get recent posts ordered by fetch time."""
        with self.get_session() as session:
            return (
                session.query(SocialMediaPost)
                .order_by(SocialMediaPost.fetched_at.desc())
                .limit(limit)
                .all()
            )

    # Sentiment Analysis
    def create_sentiment(
        self,
        post_id: int,
        score: int,
        reasoning: str,
        model_version: str,
    ) -> SentimentAnalysis:
        """Create a new sentiment analysis record."""
        with self.get_session() as session:
            sentiment = SentimentAnalysis(
                post_id=post_id,
                score=score,
                reasoning=reasoning,
                analyzed_at=datetime.now(timezone.utc),
                model_version=model_version,
            )
            session.add(sentiment)
            session.commit()
            session.refresh(sentiment)
            logger.info(f"Created sentiment analysis: {sentiment.id} with score {score}")
            return sentiment

    def get_sentiment_analysis_by_post_id(self, post_id: int) -> Optional[SentimentAnalysis]:
        """Get sentiment analysis by post ID."""
        with self.get_session() as session:
            return session.query(SentimentAnalysis).filter_by(post_id=post_id).first()

    # Trades
    def create_trade(
        self,
        sentiment_id: int,
        symbol: str,
        side: str,
        leverage: int,
        entry_price: float,
        quantity: float,
        notional_value: float,
        fixed_stop_loss_price: float,
        trailing_callback_rate: float,
        entry_order_id: Optional[str] = None,
        stop_loss_order_id: Optional[str] = None,
        trailing_stop_order_id: Optional[str] = None,
    ) -> Trade:
        """Create a new trade record."""
        with self.get_session() as session:
            trade = Trade(
                sentiment_id=sentiment_id,
                symbol=symbol,
                side=side,
                leverage=leverage,
                entry_price=entry_price,
                quantity=quantity,
                notional_value=notional_value,
                fixed_stop_loss_price=fixed_stop_loss_price,
                trailing_callback_rate=trailing_callback_rate,
                entry_order_id=entry_order_id,
                stop_loss_order_id=stop_loss_order_id,
                trailing_stop_order_id=trailing_stop_order_id,
                is_open=True,
                opened_at=datetime.now(timezone.utc),
            )
            session.add(trade)
            session.commit()
            session.refresh(trade)
            logger.info(f"Created trade record: {trade.id} - {side} {leverage}x")
            return trade

    def get_open_trade(self, symbol: str = "BTCUSDT") -> Optional[Trade]:
        """Get currently open trade for symbol."""
        with self.get_session() as session:
            return session.query(Trade).filter_by(symbol=symbol, is_open=True).first()

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        pnl_usd: float,
        pnl_percentage: float,
        close_reason: str,
        exit_order_id: Optional[str] = None,
    ) -> Trade:
        """Close an open trade."""
        with self.get_session() as session:
            trade = session.query(Trade).filter_by(id=trade_id).first()
            if trade:
                trade.is_open = False
                trade.exit_price = exit_price
                trade.pnl_usd = pnl_usd
                trade.pnl_percentage = pnl_percentage
                trade.close_reason = close_reason
                trade.exit_order_id = exit_order_id
                trade.closed_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(trade)
                logger.info(f"Closed trade {trade_id}: PnL {pnl_percentage:.2f}%")
            return trade

    def get_trade_by_id(self, trade_id: int) -> Optional[Trade]:
        """
        Get a specific trade by ID.
        
        Args:
            trade_id: The trade ID to retrieve
            
        Returns:
            Trade object or None if not found
        """
        with self.get_session() as session:
            return session.query(Trade).filter(Trade.id == trade_id).first()
    
    def get_recent_trades(self, limit: int = 10) -> List[Trade]:
        """Get recent trades ordered by opening time."""
        with self.get_session() as session:
            return (
                session.query(Trade)
                .order_by(desc(Trade.opened_at))
                .limit(limit)
                .all()
            )
    
    def get_trades_last_24h(self) -> List[Trade]:
        """
        Get all trades closed in the last 24 hours.
        
        Returns:
            List of Trade objects closed in the last 24 hours
        """
        from datetime import datetime, timedelta
        with self.get_session() as session:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            return (
                session.query(Trade)
                .filter(Trade.is_open == False)
                .filter(Trade.closed_at >= cutoff_time)
                .all()
            )

    # System Logs
    def get_total_trades_count(self) -> int:
        """Get total number of trades in the database."""
        with self.get_session() as session:
            return session.query(Trade).count()

    def create_log(
        self,
        level: str,
        module: str,
        message: str,
        exception: Optional[str] = None,
    ) -> SystemLog:
        """Create a system log entry."""
        with self.get_session() as session:
            log = SystemLog(
                level=level,
                module=module,
                message=message,
                exception=exception,
                timestamp=datetime.now(timezone.utc),
            )
            session.add(log)
            session.commit()
            return log

