"""Tests for the main trading bot."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.bot.trading_bot import TradingBot


class TestTradingBot:
    """Test trading bot functionality."""

    @patch('src.trading.binance_client.Client')
    def test_init(self, mock_binance_client):
        """Test bot initialization."""
        # Mock Binance client to avoid geo-restriction errors
        mock_client = Mock()
        mock_binance_client.return_value = mock_client
        
        bot = TradingBot()
        assert bot.db is not None
        assert bot.sentiment_analyzer is not None
        assert bot.position_manager is not None
        assert bot.telegram is not None
        assert bot.twitter_monitor is not None
        assert bot.truthsocial_monitor is not None
        assert bot.is_running is False
        assert bot.monitoring_threads == []

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_test_all_connections_success(self, mock_db_class, mock_telegram_class, 
                                        mock_position_class, mock_sentiment_class,
                                        mock_twitter_class):
        """Test successful connection test for all services."""
        # Mock all services to return True
        mock_twitter = Mock()
        mock_twitter.test_connection.return_value = True
        mock_twitter_class.return_value = mock_twitter
        
        mock_sentiment = Mock()
        mock_sentiment.test_connection.return_value = True
        mock_sentiment_class.return_value = mock_sentiment
        
        mock_position = Mock()
        mock_position.binance.test_connection.return_value = True
        mock_position_class.return_value = mock_position
        
        mock_telegram = Mock()
        mock_telegram.test_connection.return_value = True
        mock_telegram_class.return_value = mock_telegram
        
        bot = TradingBot()
        results = bot.test_all_connections()
        
        assert results["twitter"] is True
        assert results["claude"] is True
        assert results["binance"] is True
        assert results["telegram"] is True

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_test_all_connections_failure(self, mock_db_class, mock_telegram_class, 
                                        mock_position_class, mock_sentiment_class,
                                        mock_twitter_class):
        """Test failed connection test for all services."""
        # Mock all services to return False
        mock_twitter = Mock()
        mock_twitter.test_connection.return_value = False
        mock_twitter_class.return_value = mock_twitter
        
        mock_sentiment = Mock()
        mock_sentiment.test_connection.return_value = False
        mock_sentiment_class.return_value = mock_sentiment
        
        mock_position = Mock()
        mock_position.binance.test_connection.return_value = False
        mock_position_class.return_value = mock_position
        
        mock_telegram = Mock()
        mock_telegram.test_connection.return_value = False
        mock_telegram_class.return_value = mock_telegram
        
        bot = TradingBot()
        results = bot.test_all_connections()
        
        assert results["twitter"] is False
        assert results["claude"] is False
        assert results["binance"] is False
        assert results["telegram"] is False

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_on_new_post_success(self, mock_db_class, mock_telegram_class, 
                                mock_position_class, mock_sentiment_class,
                                mock_twitter_class):
        """Test successful new post handling."""
        # Mock database
        mock_db = Mock()
        mock_db.get_open_trade.return_value = None
        mock_db_class.return_value = mock_db
        
        # Mock sentiment analyzer
        mock_sentiment = Mock()
        mock_sentiment.process_post.return_value = {
            "score": 8,
            "reasoning": "Very bullish",
            "sentiment_id": 1
        }
        mock_sentiment_class.return_value = mock_sentiment
        
        # Mock position manager
        mock_position = Mock()
        mock_position.should_trade.return_value = (True, "Bullish sentiment")
        mock_position.prepare_trade.return_value = {
            "side": "LONG",
            "leverage": 10,
            "quantity": 0.1,
            "entry_price": 50000.0
        }
        mock_position.execute_trade.return_value = True
        mock_position_class.return_value = mock_position
        
        # Mock telegram
        mock_telegram = Mock()
        mock_telegram_class.return_value = mock_telegram
        
        bot = TradingBot()
        bot.db = mock_db
        bot.sentiment_analyzer = mock_sentiment
        bot.position_manager = mock_position
        bot.telegram = mock_telegram
        
        post_data = {
            "post_id": 1,
            "platform": "TWITTER",
            "content": "Test post",
            "external_id": "123",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        bot._on_new_post(post_data)
        
        # Verify calls
        mock_telegram.notify_post_with_sentiment.assert_called_once()
        mock_sentiment.process_post.assert_called_once_with(post_data)
        mock_position.should_trade.assert_called_once_with(8)
        mock_position.prepare_trade.assert_called_once_with(8)
        mock_position.execute_trade.assert_called_once()

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_on_new_post_no_trade(self, mock_db_class, mock_telegram_class, 
                                 mock_position_class, mock_sentiment_class,
                                 mock_twitter_class):
        """Test new post handling when no trade should be made."""
        # Mock database
        mock_db = Mock()
        mock_db.get_open_trade.return_value = None
        mock_db_class.return_value = mock_db
        
        # Mock sentiment analyzer
        mock_sentiment = Mock()
        mock_sentiment.process_post.return_value = {
            "score": 5,
            "reasoning": "Neutral",
            "sentiment_id": 1
        }
        mock_sentiment_class.return_value = mock_sentiment
        
        # Mock position manager - should not trade
        mock_position = Mock()
        mock_position.should_trade.return_value = (False, "Neutral sentiment")
        mock_position_class.return_value = mock_position
        
        # Mock telegram
        mock_telegram = Mock()
        mock_telegram_class.return_value = mock_telegram
        
        bot = TradingBot()
        bot.db = mock_db
        bot.sentiment_analyzer = mock_sentiment
        bot.position_manager = mock_position
        bot.telegram = mock_telegram
        
        post_data = {
            "post_id": 1,
            "platform": "TWITTER",
            "content": "Test post",
            "external_id": "123",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        bot._on_new_post(post_data)
        
        # Verify calls
        mock_telegram.notify_post_with_sentiment.assert_called_once()
        mock_sentiment.process_post.assert_called_once_with(post_data)
        mock_position.should_trade.assert_called_once_with(5)
        # Should not prepare or execute trade
        mock_position.prepare_trade.assert_not_called()
        mock_position.execute_trade.assert_not_called()

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_on_new_post_existing_position(self, mock_db_class, mock_telegram_class, 
                                          mock_position_class, mock_sentiment_class,
                                          mock_twitter_class):
        """Test new post handling when position already exists."""
        # Mock database - existing position
        mock_db = Mock()
        mock_db.get_open_trade.return_value = Mock()  # Existing position
        mock_db_class.return_value = mock_db
        
        # Mock sentiment analyzer
        mock_sentiment = Mock()
        mock_sentiment.process_post.return_value = {
            "score": 8,
            "reasoning": "Very bullish",
            "sentiment_id": 1
        }
        mock_sentiment_class.return_value = mock_sentiment
        
        # Mock position manager
        mock_position = Mock()
        mock_position_class.return_value = mock_position
        
        # Mock telegram
        mock_telegram = Mock()
        mock_telegram_class.return_value = mock_telegram
        
        bot = TradingBot()
        bot.db = mock_db
        bot.sentiment_analyzer = mock_sentiment
        bot.position_manager = mock_position
        bot.telegram = mock_telegram
        
        post_data = {
            "post_id": 1,
            "platform": "TWITTER",
            "content": "Test post",
            "external_id": "123",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        bot._on_new_post(post_data)
        
        # Verify calls
        mock_telegram.notify_post_with_sentiment.assert_called_once()
        mock_sentiment.process_post.assert_called_once_with(post_data)
        # Should check should_trade but not prepare/execute trade due to existing position
        mock_position.should_trade.assert_called_once_with(8)
        mock_position.prepare_trade.assert_not_called()
        mock_position.execute_trade.assert_not_called()

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_on_new_post_error(self, mock_db_class, mock_telegram_class, 
                              mock_position_class, mock_sentiment_class,
                              mock_twitter_class):
        """Test new post handling with error."""
        # Mock database
        mock_db = Mock()
        mock_db.get_open_trade.side_effect = Exception("Database error")
        mock_db_class.return_value = mock_db
        
        # Mock sentiment analyzer
        mock_sentiment = Mock()
        mock_sentiment_class.return_value = mock_sentiment
        
        # Mock position manager
        mock_position = Mock()
        mock_position_class.return_value = mock_position
        
        # Mock telegram
        mock_telegram = Mock()
        mock_telegram_class.return_value = mock_telegram
        
        bot = TradingBot()
        bot.db = mock_db
        bot.sentiment_analyzer = mock_sentiment
        bot.position_manager = mock_position
        bot.telegram = mock_telegram
        
        post_data = {
            "post_id": 1,
            "platform": "TWITTER",
            "content": "Test post",
            "external_id": "123",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Should not raise exception
        bot._on_new_post(post_data)

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_start_monitoring_success(self, mock_db_class, mock_telegram_class, 
                                     mock_position_class, mock_sentiment_class,
                                     mock_twitter_class):
        """Test successful monitoring start."""
        # Mock all services to return True
        mock_twitter = Mock()
        mock_twitter.test_connection.return_value = True
        mock_twitter_class.return_value = mock_twitter
        
        mock_sentiment = Mock()
        mock_sentiment.test_connection.return_value = True
        mock_sentiment_class.return_value = mock_sentiment
        
        mock_position = Mock()
        mock_position.binance.test_connection.return_value = True
        mock_position_class.return_value = mock_position
        
        mock_telegram = Mock()
        mock_telegram.test_connection.return_value = True
        mock_telegram_class.return_value = mock_telegram
        
        bot = TradingBot()
        bot.start_monitoring()
        
        assert bot.is_running is True
        assert len(bot.monitoring_threads) == 2  # Twitter + Truth Social

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_start_monitoring_failed_connections(self, mock_db_class, mock_telegram_class, 
                                                mock_position_class, mock_sentiment_class,
                                                mock_twitter_class):
        """Test monitoring start with failed connections."""
        # Mock all services to return False
        mock_twitter = Mock()
        mock_twitter.test_connection.return_value = False
        mock_twitter_class.return_value = mock_twitter
        
        mock_sentiment = Mock()
        mock_sentiment.test_connection.return_value = False
        mock_sentiment_class.return_value = mock_sentiment
        
        mock_position = Mock()
        mock_position.binance.test_connection.return_value = False
        mock_position_class.return_value = mock_position
        
        mock_telegram = Mock()
        mock_telegram.test_connection.return_value = False
        mock_telegram_class.return_value = mock_telegram
        
        bot = TradingBot()
        bot.start_monitoring()
        
        assert bot.is_running is False
        assert len(bot.monitoring_threads) == 0

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_stop_monitoring(self, mock_db_class, mock_telegram_class, 
                            mock_position_class, mock_sentiment_class,
                            mock_twitter_class):
        """Test monitoring stop."""
        # Mock all services
        mock_twitter = Mock()
        mock_twitter_class.return_value = mock_twitter
        
        mock_sentiment = Mock()
        mock_sentiment_class.return_value = mock_sentiment
        
        mock_position = Mock()
        mock_position_class.return_value = mock_position
        
        mock_telegram = Mock()
        mock_telegram_class.return_value = mock_telegram
        
        bot = TradingBot()
        bot.is_running = True
        bot.monitoring_threads = [Mock()]
        
        bot.stop_monitoring()
        
        assert bot.is_running is False
        mock_twitter.stop_monitoring.assert_called_once()

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_get_status(self, mock_db_class, mock_telegram_class, 
                       mock_position_class, mock_sentiment_class,
                       mock_twitter_class):
        """Test getting bot status."""
        # Mock all services
        mock_twitter = Mock()
        mock_twitter.get_monitoring_status.return_value = {
            "monitoring": True,
            "method": "RapidAPI (30s)"
        }
        mock_twitter_class.return_value = mock_twitter
        
        mock_sentiment = Mock()
        mock_sentiment_class.return_value = mock_sentiment
        
        mock_position = Mock()
        mock_position.get_open_position.return_value = None
        mock_position.binance.get_account_balance.return_value = 1000.0
        mock_position.get_trading_status.return_value = {
            "binance": {"connected": True},
            "open_trade": None,
            "testnet_mode": True
        }
        mock_position_class.return_value = mock_position
        
        mock_telegram = Mock()
        mock_telegram_class.return_value = mock_telegram
        
        # Mock database
        mock_db = Mock()
        mock_db.get_sentiment_stats_24h.return_value = {
            "total_posts": 5,
            "average_score": 7.0,
            "bullish_count": 3,
            "bearish_count": 1,
            "neutral_count": 1
        }
        mock_db_class.return_value = mock_db
        
        bot = TradingBot()
        bot.db = mock_db
        bot.twitter_monitor = mock_twitter
        bot.position_manager = mock_position
        
        status = bot.get_status()
        
        assert status["bot_running"] is False
        # Truth Social removed - now only Twitter RapidAPI
        assert status["monitoring"]["twitter"]["monitoring"] is True
        assert status["monitoring"]["twitter"]["method"] == "RapidAPI (30s)"
        assert "truthsocial" not in status["monitoring"]  # Truth Social completely removed
        assert status["trading"]["open_trade"] is None

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_close_all_positions_success(self, mock_db_class, mock_telegram_class, 
                                        mock_position_class, mock_sentiment_class,
                                        mock_twitter_class):
        """Test closing all positions successfully."""
        # Mock position manager
        mock_position = Mock()
        mock_position.has_open_position.return_value = True
        mock_position.close_position.return_value = True
        mock_position_class.return_value = mock_position
        
        bot = TradingBot()
        bot.position_manager = mock_position
        
        success, error_msg = bot.close_all_positions()
        
        assert success is True
        assert error_msg == ""
        mock_position.close_position.assert_called_once()

    @patch('src.bot.trading_bot.TwitterMonitor')
    @patch('src.bot.trading_bot.SentimentAnalyzer')
    @patch('src.bot.trading_bot.PositionManager')
    @patch('src.bot.trading_bot.TelegramNotifier')
    @patch('src.bot.trading_bot.DatabaseRepository')
    def test_close_all_positions_no_open_trade(self, mock_db_class, mock_telegram_class, 
                                              mock_position_class, mock_sentiment_class,
                                              mock_twitter_class):
        """Test closing positions when none are open."""
        # Mock database
        mock_db = Mock()
        mock_db.get_open_trade.return_value = None
        mock_db_class.return_value = mock_db
        
        # Mock position manager
        mock_position = Mock()
        mock_position.has_open_position.return_value = False
        mock_position_class.return_value = mock_position
        
        bot = TradingBot()
        bot.db = mock_db
        bot.position_manager = mock_position
        
        success, error_msg = bot.close_all_positions()
        
        assert success is True
        assert error_msg == ""
        mock_position.close_position.assert_not_called()