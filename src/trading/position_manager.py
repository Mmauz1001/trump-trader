"""Position management for trading operations."""

import time
from typing import Dict, List, Optional, Tuple

from config.settings import settings
from src.database.repository import DatabaseRepository
from src.database.models import Trade
from src.trading.binance_client import BinanceClient
from src.utils import (
    get_leverage_for_score,
    get_callback_rate_for_leverage,
    get_position_side,
    should_open_position,
    calculate_pnl_percentage,
    setup_logger
)

logger = setup_logger(__name__)


class PositionManager:
    """Manages trading positions and order execution."""

    def __init__(self):
        """Initialize position manager."""
        self.binance = BinanceClient()
        self.db = DatabaseRepository()
        
        logger.info("Position manager initialized")

    def should_trade(self, sentiment_score: int) -> Tuple[bool, str]:
        """
        Determine if we should trade based on sentiment score.

        Args:
            sentiment_score: Sentiment score (0-10)

        Returns:
            Tuple of (should_trade, reason)
        """
        if not should_open_position(sentiment_score):
            return False, "Neutral sentiment (score 5) - no action"
        
        if sentiment_score > 5:
            return True, f"Bullish sentiment (score {sentiment_score}) - go LONG"
        elif sentiment_score < 5:
            return True, f"Bearish sentiment (score {sentiment_score}) - go SHORT"
        
        return False, "Invalid sentiment score"

    def prepare_trade(self, sentiment_score: int) -> Optional[Dict]:
        """
        Prepare trade parameters based on sentiment score.

        Args:
            sentiment_score: Sentiment score (0-10)

        Returns:
            Trade parameters or None if invalid
        """
        try:
            # Get leverage based on score
            leverage = get_leverage_for_score(sentiment_score)
            
            if leverage == 0:
                logger.info("Score 5 - no leverage, no trade")
                return None
            
            # Get position side
            side = get_position_side(sentiment_score)
            
            # Get callback rate for trailing stop
            callback_rate = get_callback_rate_for_leverage(leverage)
            
            # Calculate position size
            position_size = self.binance.calculate_position_size(leverage)
            
            if position_size <= 0:
                logger.error("Cannot calculate position size - insufficient balance")
                return None
            
            # Get current price
            current_price = self.binance.get_current_price()
            if not current_price:
                logger.error("Cannot get current price")
                return None
            
            # Calculate notional value
            notional_value = position_size * current_price
            
            # Calculate stop-loss price (1% max loss)
            if side == "LONG":
                stop_loss_price = current_price * 0.99  # 1% below entry
            else:
                stop_loss_price = current_price * 1.01  # 1% above entry
            
            trade_params = {
                "side": side,
                "leverage": leverage,
                "position_size": position_size,
                "current_price": current_price,
                "notional_value": notional_value,
                "stop_loss_price": stop_loss_price,
                "callback_rate": callback_rate,
                "sentiment_score": sentiment_score
            }
            
            logger.info(f"Trade prepared: {side} {leverage}x {position_size:.6f} BTC @ ${current_price:.2f}")
            return trade_params
            
        except Exception as e:
            logger.error(f"Error preparing trade: {e}")
            return None

    def execute_trade(self, trade_params: Dict, sentiment_id: int) -> Optional[Dict]:
        """
        Execute a trade with all safety measures.

        Args:
            trade_params: Trade parameters from prepare_trade
            sentiment_id: Sentiment analysis ID

        Returns:
            Trade execution result or None if failed
        """
        try:
            # Check if we're in dry run mode
            if settings.binance_testnet:
                logger.info("DRY RUN MODE - Simulating trade execution")
                return self._simulate_trade(trade_params, sentiment_id)
            
            # 1. Close any existing positions
            logger.info("Closing existing positions...")
            if not self.binance.close_all_positions():
                logger.error("Failed to close existing positions")
                return None
            
            # 2. Cancel all open orders
            logger.info("Cancelling open orders...")
            if not self.binance.cancel_all_orders():
                logger.error("Failed to cancel open orders")
                return None
            
            # 3. Set leverage
            logger.info(f"Setting leverage to {trade_params['leverage']}x...")
            if not self.binance.set_leverage(trade_params['leverage']):
                logger.error("Failed to set leverage")
                return None
            
            # 4. Place market order
            # Convert LONG/SHORT to BUY/SELL for Binance API
            binance_side = "BUY" if trade_params['side'] == "LONG" else "SELL"
            logger.info(f"Placing {trade_params['side']} market order...")
            market_order = self.binance.place_market_order(
                side=binance_side,
                quantity=trade_params['position_size']
            )
            
            if not market_order:
                logger.error("Failed to place market order")
                return None
            
            # 5. Place stop-loss order
            logger.info("Placing stop-loss order...")
            stop_loss_order = self.binance.place_stop_loss_order(
                side="SELL" if trade_params['side'] == "BUY" else "BUY",
                quantity=trade_params['position_size'],
                stop_price=trade_params['stop_loss_price']
            )
            
            # 6. Place trailing stop order
            logger.info("Placing trailing stop order...")
            trailing_stop_order = self.binance.place_trailing_stop_order(
                side="SELL" if trade_params['side'] == "BUY" else "BUY",
                quantity=trade_params['position_size'],
                callback_rate=trade_params['callback_rate']
            )
            
            # 7. Store trade in database
            trade = self.db.create_trade(
                sentiment_id=sentiment_id,
                symbol="BTCUSDT",
                side=trade_params['side'],
                leverage=trade_params['leverage'],
                entry_price=trade_params['current_price'],
                quantity=trade_params['position_size'],
                notional_value=trade_params['notional_value'],
                fixed_stop_loss_price=trade_params['stop_loss_price'],
                trailing_callback_rate=trade_params['callback_rate'],
                entry_order_id=str(market_order['orderId']),
                stop_loss_order_id=str(stop_loss_order['orderId']) if stop_loss_order else None,
                trailing_stop_order_id=str(trailing_stop_order['orderId']) if trailing_stop_order else None
            )
            
            logger.info(f"✅ Trade executed successfully: {trade.id}")
            
            return {
                "trade_id": trade.id,
                "side": trade_params['side'],
                "leverage": trade_params['leverage'],
                "entry_price": trade_params['current_price'],
                "position_size": trade_params['position_size'],
                "sentiment_score": trade_params['sentiment_score'],
                "orders": {
                    "market": market_order['orderId'],
                    "stop_loss": stop_loss_order['orderId'] if stop_loss_order else None,
                    "trailing_stop": trailing_stop_order['orderId'] if trailing_stop_order else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return None

    def _simulate_trade(self, trade_params: Dict, sentiment_id: int) -> Dict:
        """Simulate trade execution for dry run mode."""
        try:
            # Create simulated trade record
            trade = self.db.create_trade(
                sentiment_id=sentiment_id,
                symbol="BTCUSDT",
                side=trade_params['side'],
                leverage=trade_params['leverage'],
                entry_price=trade_params['current_price'],
                quantity=trade_params['position_size'],
                notional_value=trade_params['notional_value'],
                fixed_stop_loss_price=trade_params['stop_loss_price'],
                trailing_callback_rate=trade_params['callback_rate'],
                entry_order_id="SIMULATED_MARKET_ORDER",
                stop_loss_order_id="SIMULATED_STOP_LOSS",
                trailing_stop_order_id="SIMULATED_TRAILING_STOP"
            )
            
            logger.info(f"✅ DRY RUN: Trade simulated successfully: {trade.id}")
            
            return {
                "trade_id": trade.id,
                "side": trade_params['side'],
                "leverage": trade_params['leverage'],
                "entry_price": trade_params['current_price'],
                "position_size": trade_params['position_size'],
                "sentiment_score": trade_params['sentiment_score'],
                "simulated": True,
                "orders": {
                    "market": "SIMULATED_MARKET_ORDER",
                    "stop_loss": "SIMULATED_STOP_LOSS",
                    "trailing_stop": "SIMULATED_TRAILING_STOP"
                }
            }
            
        except Exception as e:
            logger.error(f"Error simulating trade: {e}")
            return None

    def close_position(self, trade_id: int, reason: str = "MANUAL") -> bool:
        """
        Close a specific position.

        Args:
            trade_id: Trade ID to close
            reason: Reason for closing

        Returns:
            True if successful
        """
        try:
            # Get trade from database
            with self.db.get_session() as session:
                trade = session.query(Trade).filter_by(id=trade_id).first()
                
                if not trade:
                    logger.error(f"Trade {trade_id} not found")
                    return False
                
                if not trade.is_open:
                    logger.info(f"Trade {trade_id} already closed")
                    return True
            
            if settings.binance_testnet:
                # Simulate closing
                logger.info(f"DRY RUN: Closing trade {trade_id}")
                self.db.close_trade(
                    trade_id=trade_id,
                    exit_price=trade.entry_price,  # Simulate no change
                    pnl_usd=0.0,
                    pnl_percentage=0.0,
                    close_reason=reason
                )
                return True
            
            # Get unrealized PnL and exit price BEFORE closing
            binance_pnl = self.binance.get_position_pnl()
            
            if binance_pnl:
                exit_price = binance_pnl["mark_price"]
            else:
                # Fallback: use current price
                exit_price = self.binance.get_current_price()
                if not exit_price:
                    exit_price = trade.entry_price
            
            # Cancel all open orders (including trailing stop) BEFORE closing position
            logger.info("Cancelling all open orders (trailing stop, etc.)...")
            if not self.binance.cancel_all_orders():
                logger.warning("Failed to cancel orders, but continuing with position close")
            
            # Close position on exchange
            if not self.binance.close_all_positions():
                logger.error("Failed to close position on exchange")
                return False
            
            # Get ACTUAL realized PnL from Binance income history (after closing)
            time.sleep(1)  # Wait 1 second for Binance to register the close
            
            realized_income = self.binance.get_realized_pnl_from_income()
            
            if realized_income:
                # Use ACTUAL realized PnL from Binance
                pnl_usd = realized_income["realized_pnl"]
                pnl_percentage = (pnl_usd / trade.notional_value * 100) if trade.notional_value > 0 else 0
                logger.info(f"✅ Actual realized PnL from Binance: ${pnl_usd:.2f} ({pnl_percentage:.2f}%)")
            else:
                # Fallback: calculate from exit price
                logger.warning("Could not fetch realized PnL from Binance, calculating from exit price")
                pnl_percentage = calculate_pnl_percentage(
                    trade.entry_price,
                    exit_price,
                    trade.side,
                    trade.leverage
                )
                pnl_usd = (pnl_percentage / 100) * trade.notional_value
            
            # Update database with actual exit data
            self.db.close_trade(
                trade_id=trade_id,
                exit_price=exit_price,
                pnl_usd=pnl_usd,
                pnl_percentage=pnl_percentage,
                close_reason=reason
            )
            
            logger.info(f"✅ Position closed: {trade_id} - PnL: {pnl_percentage:.2f}%")
            return True
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False

    def get_trading_status(self) -> Dict:
        """Get current trading status."""
        try:
            binance_status = self.binance.get_trading_status()
            open_trade = self.db.get_open_trade()
            
            return {
                "binance": binance_status,
                "open_trade": {
                    "id": open_trade.id if open_trade else None,
                    "side": open_trade.side if open_trade else None,
                    "leverage": open_trade.leverage if open_trade else None,
                    "entry_price": open_trade.entry_price if open_trade else None,
                    "opened_at": open_trade.opened_at.isoformat() if open_trade else None
                } if open_trade else None,
                "testnet_mode": settings.binance_testnet
            }
            
        except Exception as e:
            logger.error(f"Error getting trading status: {e}")
            return {"error": str(e)}
