"""Tests for notification system."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.notifications.telegram_notifier import TelegramNotifier


class TestTelegramNotifier:
    """Test Telegram notifier functionality."""

    def test_init(self):
        """Test Telegram notifier initialization."""
        notifier = TelegramNotifier()
        assert notifier.bot_token is not None
        assert notifier.channel_id is not None
        assert notifier.base_url is not None

    @patch('src.notifications.telegram_notifier.requests.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection test."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {
                "username": "trump_trader_bot",
                "first_name": "Trump Trader Bot"
            }
        }
        mock_get.return_value = mock_response
        
        notifier = TelegramNotifier()
        result = notifier.test_connection()
        
        assert result is True
        mock_get.assert_called_once()

    @patch('src.notifications.telegram_notifier.requests.get')
    def test_test_connection_failure(self, mock_get):
        """Test failed connection test."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        notifier = TelegramNotifier()
        result = notifier.test_connection()
        
        assert result is False

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message sending."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        result = notifier.send_message("Test message")
        
        assert result is True
        mock_post.assert_called_once()

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_send_message_failure(self, mock_post):
        """Test failed message sending."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"ok": False, "description": "Bad Request"}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        result = notifier.send_message("Test message")
        
        assert result is False

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_new_post(self, mock_post):
        """Test notifying about new post."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        post_data = {
            "platform": "TWITTER",
            "content": "Test post content",
            "posted_at": datetime.now(timezone.utc)
        }
        
        result = notifier.notify_new_post(post_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        assert "NEW TWITTER POST" in message_data["text"]
        assert "Test post content" in message_data["text"]

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_sentiment_analysis_bullish(self, mock_post):
        """Test notifying about bullish sentiment analysis."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        sentiment_data = {
            "score": 8,
            "reasoning": "Very bullish sentiment",
            "platform": "TWITTER",
            "content": "Test post content"
        }
        
        result = notifier.notify_sentiment_analysis(sentiment_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        assert "SENTIMENT ANALYSIS COMPLETE" in message_data["text"]
        assert "BULLISH (8/10)" in message_data["text"]
        assert "Very bullish sentiment" in message_data["text"]

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_sentiment_analysis_bearish(self, mock_post):
        """Test notifying about bearish sentiment analysis."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        sentiment_data = {
            "score": 2,
            "reasoning": "Very bearish sentiment",
            "platform": "TWITTER",
            "content": "Test post content"
        }
        
        result = notifier.notify_sentiment_analysis(sentiment_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        assert "SENTIMENT ANALYSIS COMPLETE" in message_data["text"]
        assert "BEARISH (2/10)" in message_data["text"]
        assert "Very bearish sentiment" in message_data["text"]

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_sentiment_analysis_neutral(self, mock_post):
        """Test notifying about neutral sentiment analysis."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        sentiment_data = {
            "score": 5,
            "reasoning": "Neutral sentiment",
            "platform": "TWITTER",
            "content": "Test post content"
        }
        
        result = notifier.notify_sentiment_analysis(sentiment_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        assert "SENTIMENT ANALYSIS COMPLETE" in message_data["text"]
        assert "NEUTRAL (5/10)" in message_data["text"]
        assert "Neutral sentiment" in message_data["text"]

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_trade_execution_dry_run(self, mock_post):
        """Test notifying about trade execution in dry run mode."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        trade_data = {
            "side": "BUY",
            "leverage": 10,
            "entry_price": 50000.0,
            "position_size": 0.1,
            "sentiment_score": 8,
            "simulated": True
        }
        
        result = notifier.notify_trade_execution(trade_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        assert "DRY RUN: TRADE EXECUTED" in message_data["text"]
        assert "LONG 10x" in message_data["text"]
        assert "SIMULATED TRADE" in message_data["text"]

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_trade_execution_live(self, mock_post):
        """Test notifying about trade execution in live mode."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        trade_data = {
            "side": "SELL",
            "leverage": 30,
            "entry_price": 50000.0,
            "position_size": 0.1,
            "sentiment_score": 2,
            "simulated": False,
            "callback_rate": 2.0
        }
        
        result = notifier.notify_trade_execution(trade_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        assert "TRADE EXECUTED" in message_data["text"]
        assert "SHORT 30x" in message_data["text"]
        assert "RISK MANAGEMENT" in message_data["text"]

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_position_update_profit(self, mock_post):
        """Test notifying about position update with profit."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        update_data = {
            "trade_id": 1,
            "current_price": 51000.0,
            "pnl_percentage": 2.0,
            "pnl_usd": 100.0
        }
        
        result = notifier.notify_position_update(update_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        assert "POSITION UPDATE" in message_data["text"]
        assert "PnL:</b> +2.00%" in message_data["text"]

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_position_update_loss(self, mock_post):
        """Test notifying about position update with loss."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        update_data = {
            "trade_id": 1,
            "current_price": 49000.0,
            "pnl_percentage": -2.0,
            "pnl_usd": -100.0
        }
        
        result = notifier.notify_position_update(update_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        assert "POSITION UPDATE" in message_data["text"]
        assert "PnL:</b> -2.00%" in message_data["text"]

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_position_closed_profit(self, mock_post):
        """Test notifying about position closure with profit."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        close_data = {
            "trade_id": 1,
            "exit_price": 51000.0,
            "pnl_percentage": 2.0,
            "pnl_usd": 100.0,
            "close_reason": "MANUAL"
        }
        
        result = notifier.notify_position_closed(close_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        # Epic celebration messages no longer contain "POSITION CLOSED"
        # Instead they have creative victory messages
        assert ("+2.00%" in message_data["text"] or "LEGEND" in message_data["text"] or "BEAST" in message_data["text"])

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_position_closed_loss(self, mock_post):
        """Test notifying about position closure with loss."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        close_data = {
            "trade_id": 1,
            "exit_price": 49000.0,
            "pnl_percentage": -2.0,
            "pnl_usd": -100.0,
            "close_reason": "STOP_LOSS"
        }
        
        result = notifier.notify_position_closed(close_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        # Epic mockery messages no longer contain "POSITION CLOSED"
        # Instead they have brutal mockery messages
        assert ("-2.00%" in message_data["text"] or "CLOWN" in message_data["text"] or "HAHAHAHA" in message_data["text"])

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_notify_error(self, mock_post):
        """Test notifying about errors."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        error_data = {
            "type": "API Error",
            "message": "Connection failed",
            "component": "TwitterMonitor"
        }
        
        result = notifier.notify_error(error_data)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_data = call_args[1]["json"]
        assert "ERROR ALERT" in message_data["text"]
        assert "API Error" in message_data["text"]
        assert "Connection failed" in message_data["text"]

    @patch('src.notifications.telegram_notifier.requests.post')
    def test_send_test_message(self, mock_post):
        """Test sending test message."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier()
        
        # Mock settings for dry run mode
        with patch('src.notifications.telegram_notifier.settings') as mock_settings:
            mock_settings.binance_testnet = True
            
            result = notifier.send_test_message()
            
            assert result is True
            mock_post.assert_called_once()
            
            # Check message content
            call_args = mock_post.call_args
            message_data = call_args[1]["json"]
            assert "TRUMP TRADER BOT" in message_data["text"]
            assert "Status:</b> Online and ready" in message_data["text"]
            assert "Mode:</b> TESTNET" in message_data["text"]
