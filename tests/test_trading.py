"""Tests for trading modules."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from src.trading.binance_client import BinanceClient
from src.trading.position_manager import PositionManager


class TestBinanceClient:
    """Test Binance client functionality."""

    @patch('src.trading.binance_client.Client')
    def test_init(self, mock_client_class):
        """Test Binance client initialization."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        client = BinanceClient()
        assert client.client is not None
        assert client.symbol == "BTCUSDT"

    @patch('src.trading.binance_client.Client')
    def test_test_connection_success(self, mock_client_class):
        """Test successful connection test."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock successful account info
        mock_client.futures_account.return_value = {
            "totalWalletBalance": "1000.0",
            "availableBalance": "800.0"
        }
        
        client = BinanceClient()
        result = client.test_connection()
        
        assert result is True
        mock_client.futures_account.assert_called_once()

    @patch('src.trading.binance_client.Client')
    def test_test_connection_failure(self, mock_client_class):
        """Test failed connection test."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock failed account info
        mock_client.futures_account.side_effect = Exception("API Error")
        
        client = BinanceClient()
        result = client.test_connection()
        
        assert result is False

    @patch('src.trading.binance_client.Client')
    def test_get_account_balance(self, mock_client_class):
        """Test getting account balance."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock account info
        mock_client.futures_account.return_value = {
            "totalWalletBalance": "1000.0",
            "availableBalance": "800.0",
            "totalMarginBalance": "1000.0",
            "totalUnrealizedProfit": "50.0"
        }
        
        client = BinanceClient()
        balance = client.get_account_balance()
        
        assert balance["total_balance"] == 1000.0
        assert balance["available_balance"] == 800.0
        assert balance["margin_balance"] == 1000.0
        assert balance["unrealized_pnl"] == 50.0

    @patch('src.trading.binance_client.Client')
    def test_get_current_price(self, mock_client_class):
        """Test getting current price."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock price ticker
        mock_client.futures_symbol_ticker.return_value = {"price": "50000.0"}
        
        client = BinanceClient()
        price = client.get_current_price()
        
        assert price == 50000.0

    @patch('src.trading.binance_client.Client')
    def test_get_open_positions(self, mock_client_class):
        """Test getting open positions."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock positions
        mock_client.futures_position_information.return_value = [
            {
                "symbol": "BTCUSDT",
                "positionAmt": "0.1",
                "entryPrice": "50000.0",
                "markPrice": "51000.0",
                "unRealizedProfit": "100.0",
                "leverage": "10"
            }
        ]
        
        client = BinanceClient()
        positions = client.get_open_positions()
        
        assert len(positions) == 1
        assert positions[0]["side"] == "LONG"
        assert positions[0]["size"] == 0.1
        assert positions[0]["entry_price"] == 50000.0

    @patch('src.trading.binance_client.Client')
    def test_close_all_positions(self, mock_client_class):
        """Test closing all positions."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock positions and orders
        mock_client.futures_position_information.return_value = [
            {
                "symbol": "BTCUSDT",
                "positionAmt": "0.1",
                "entryPrice": "50000.0",
                "markPrice": "51000.0",
                "unRealizedProfit": "100.0",
                "leverage": "10"
            }
        ]
        mock_client.futures_create_order.return_value = {"orderId": "123456"}
        
        client = BinanceClient()
        result = client.close_all_positions()
        
        assert result is True
        mock_client.futures_create_order.assert_called_once()

    @patch('src.trading.binance_client.Client')
    def test_cancel_all_orders(self, mock_client_class):
        """Test cancelling all orders."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock orders
        mock_client.futures_get_open_orders.return_value = [
            {"orderId": "123456", "symbol": "BTCUSDT"}
        ]
        mock_client.futures_cancel_order.return_value = {"orderId": "123456"}
        
        client = BinanceClient()
        result = client.cancel_all_orders()
        
        assert result is True
        mock_client.futures_cancel_order.assert_called_once()

    @patch('src.trading.binance_client.Client')
    def test_set_leverage(self, mock_client_class):
        """Test setting leverage."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.futures_change_leverage.return_value = {"leverage": 10}
        
        client = BinanceClient()
        result = client.set_leverage(10)
        
        assert result is True
        mock_client.futures_change_leverage.assert_called_once_with(
            symbol="BTCUSDT",
            leverage=10
        )

    @patch('src.trading.binance_client.Client')
    def test_calculate_position_size(self, mock_client_class):
        """Test calculating position size."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock account balance and price
        mock_client.futures_account.return_value = {
            "totalWalletBalance": "1000.0",
            "availableBalance": "800.0"
        }
        mock_client.futures_symbol_ticker.return_value = {"price": "50000.0"}
        
        client = BinanceClient()
        position_size = client.calculate_position_size(leverage=10, risk_percent=1.0)
        
        # Should calculate based on 95% of available balance (leaving 5% buffer) and leverage
        # Expected: (800.0 * 0.95 * 10) / 50000.0 = 0.152
        assert position_size > 0
        assert position_size == (800.0 * 0.95 * 10) / 50000.0

    @patch('src.trading.binance_client.Client')
    def test_place_market_order(self, mock_client_class):
        """Test placing market order."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock order creation
        mock_client.futures_create_order.return_value = {"orderId": "123456"}
        
        client = BinanceClient()
        order = client.place_market_order("BUY", 0.1)
        
        assert order is not None
        assert order["orderId"] == "123456"
        mock_client.futures_create_order.assert_called_once_with(
            symbol="BTCUSDT",
            side="BUY",
            type="MARKET",
            quantity=0.1
        )

    @patch('src.trading.binance_client.Client')
    def test_place_stop_loss_order(self, mock_client_class):
        """Test placing stop-loss order."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock order creation
        mock_client.futures_create_order.return_value = {"orderId": "123456"}
        
        client = BinanceClient()
        order = client.place_stop_loss_order("SELL", 0.1, 49000.0)
        
        assert order is not None
        assert order["orderId"] == "123456"
        mock_client.futures_create_order.assert_called_once_with(
            symbol="BTCUSDT",
            side="SELL",
            type="STOP_MARKET",
            quantity=0.1,
            stopPrice=49000.0,
            reduceOnly=True
        )

    @patch('src.trading.binance_client.Client')
    def test_place_trailing_stop_order(self, mock_client_class):
        """Test placing trailing stop order."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock order creation
        mock_client.futures_create_order.return_value = {"orderId": "123456"}
        
        client = BinanceClient()
        order = client.place_trailing_stop_order("SELL", 0.1, 2.0)
        
        assert order is not None
        assert order["orderId"] == "123456"
        mock_client.futures_create_order.assert_called_once_with(
            symbol="BTCUSDT",
            side="SELL",
            type="TRAILING_STOP_MARKET",
            quantity=0.1,
            callbackRate=2.0,
            reduceOnly=True
        )


class TestPositionManager:
    """Test position manager functionality."""

    @patch('src.trading.position_manager.BinanceClient')
    def test_init(self, mock_binance_class):
        """Test position manager initialization."""
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        
        manager = PositionManager()
        assert manager.binance is not None
        assert manager.db is not None

    @patch('src.trading.position_manager.BinanceClient')
    def test_should_trade_bullish(self, mock_binance_class):
        """Test should trade with bullish sentiment."""
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        
        manager = PositionManager()
        should_trade, reason = manager.should_trade(8)
        
        assert should_trade is True
        assert "Bullish sentiment" in reason

    @patch('src.trading.position_manager.BinanceClient')
    def test_should_trade_bearish(self, mock_binance_class):
        """Test should trade with bearish sentiment."""
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        
        manager = PositionManager()
        should_trade, reason = manager.should_trade(2)
        
        assert should_trade is True
        assert "Bearish sentiment" in reason

    @patch('src.trading.position_manager.BinanceClient')
    def test_should_trade_neutral(self, mock_binance_class):
        """Test should not trade with neutral sentiment."""
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        
        manager = PositionManager()
        should_trade, reason = manager.should_trade(5)
        
        assert should_trade is False
        assert "Neutral sentiment" in reason

    @patch('src.trading.position_manager.BinanceClient')
    def test_prepare_trade_bullish(self, mock_binance_class):
        """Test preparing bullish trade."""
        # Mock Binance client
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        mock_binance.calculate_position_size.return_value = 0.1
        mock_binance.get_current_price.return_value = 50000.0
        
        manager = PositionManager()
        trade_params = manager.prepare_trade(8)
        
        assert trade_params is not None
        assert trade_params["side"] == "LONG"
        assert trade_params["leverage"] == 15
        assert trade_params["position_size"] == 0.1
        assert trade_params["current_price"] == 50000.0

    @patch('src.trading.position_manager.BinanceClient')
    def test_prepare_trade_bearish(self, mock_binance_class):
        """Test preparing bearish trade."""
        # Mock Binance client
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        mock_binance.calculate_position_size.return_value = 0.1
        mock_binance.get_current_price.return_value = 50000.0
        
        manager = PositionManager()
        trade_params = manager.prepare_trade(2)
        
        assert trade_params is not None
        assert trade_params["side"] == "SHORT"
        assert trade_params["leverage"] == 15
        assert trade_params["position_size"] == 0.1
        assert trade_params["current_price"] == 50000.0

    @patch('src.trading.position_manager.BinanceClient')
    def test_prepare_trade_neutral(self, mock_binance_class):
        """Test preparing neutral trade."""
        manager = PositionManager()
        trade_params = manager.prepare_trade(5)
        
        assert trade_params is None

    @patch('src.trading.position_manager.BinanceClient')
    def test_prepare_trade_insufficient_balance(self, mock_binance_class):
        """Test preparing trade with insufficient balance."""
        # Mock Binance client
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        mock_binance.calculate_position_size.return_value = 0.0
        mock_binance.get_current_price.return_value = 50000.0
        
        manager = PositionManager()
        trade_params = manager.prepare_trade(8)
        
        assert trade_params is None

    @patch('src.trading.position_manager.BinanceClient')
    def test_prepare_trade_no_price(self, mock_binance_class):
        """Test preparing trade with no current price."""
        # Mock Binance client
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        mock_binance.calculate_position_size.return_value = 0.1
        mock_binance.get_current_price.return_value = None
        
        manager = PositionManager()
        trade_params = manager.prepare_trade(8)
        
        assert trade_params is None

    @patch('src.trading.position_manager.BinanceClient')
    def test_execute_trade_dry_run(self, mock_binance_class):
        """Test executing trade in dry run mode."""
        # Mock Binance client
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        
        # Mock database
        mock_db = Mock()
        mock_trade = Mock()
        mock_trade.id = 1
        mock_db.create_trade.return_value = mock_trade
        
        manager = PositionManager()
        manager.db = mock_db
        
        # Mock settings for dry run
        with patch('src.trading.position_manager.settings') as mock_settings:
            mock_settings.binance_testnet = True
            
            trade_params = {
                "side": "BUY",
                "leverage": 10,
                "position_size": 0.1,
                "current_price": 50000.0,
                "notional_value": 5000.0,
                "stop_loss_price": 49500.0,
                "callback_rate": 2.0,
                "sentiment_score": 8
            }
            
            result = manager.execute_trade(trade_params, 1)
            
            assert result is not None
            assert result["simulated"] is True
            assert result["side"] == "BUY"
            assert result["leverage"] == 10
            mock_db.create_trade.assert_called_once()

    @patch('src.trading.position_manager.BinanceClient')
    def test_execute_trade_live(self, mock_binance_class):
        """Test executing trade in live mode."""
        # Mock Binance client
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        mock_binance.close_all_positions.return_value = True
        mock_binance.cancel_all_orders.return_value = True
        mock_binance.set_leverage.return_value = True
        mock_binance.place_market_order.return_value = {"orderId": "123456"}
        mock_binance.place_stop_loss_order.return_value = {"orderId": "789012"}
        mock_binance.place_trailing_stop_order.return_value = {"orderId": "345678"}
        
        # Mock database
        mock_db = Mock()
        mock_trade = Mock()
        mock_trade.id = 1
        mock_db.create_trade.return_value = mock_trade
        
        manager = PositionManager()
        manager.db = mock_db
        
        # Mock settings for live mode
        with patch('src.trading.position_manager.settings') as mock_settings:
            mock_settings.binance_testnet = False
            
            trade_params = {
                "side": "BUY",
                "leverage": 10,
                "position_size": 0.1,
                "current_price": 50000.0,
                "notional_value": 5000.0,
                "stop_loss_price": 49500.0,
                "callback_rate": 2.0,
                "sentiment_score": 8
            }
            
            result = manager.execute_trade(trade_params, 1)
            
            assert result is not None
            assert result["side"] == "BUY"
            assert result["leverage"] == 10
            assert result["orders"]["market"] == "123456"
            assert result["orders"]["stop_loss"] == "789012"
            assert result["orders"]["trailing_stop"] == "345678"
            mock_db.create_trade.assert_called_once()

    @patch('src.trading.position_manager.BinanceClient')
    def test_get_trading_status(self, mock_binance_class):
        """Test getting trading status."""
        # Mock Binance client
        mock_binance = Mock()
        mock_binance_class.return_value = mock_binance
        mock_binance.get_trading_status.return_value = {
            "account_balance": {"total_balance": 1000.0},
            "open_positions": [],
            "current_price": 50000.0
        }
        
        # Mock database
        mock_db = Mock()
        mock_db.get_open_trade.return_value = None
        
        manager = PositionManager()
        manager.db = mock_db
        
        status = manager.get_trading_status()
        
        assert "binance" in status
        assert "open_trade" in status
        assert "testnet_mode" in status
        assert status["open_trade"] is None
