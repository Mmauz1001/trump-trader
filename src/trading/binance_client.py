"""Binance Futures API client for trading operations."""

import time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from binance.client import Client
from binance.exceptions import BinanceAPIException

from config.settings import settings
from src.utils import setup_logger

logger = setup_logger(__name__)


class BinanceClient:
    """Binance Futures API client."""

    def __init__(self):
        """Initialize Binance client."""
        self.client = Client(
            api_key=settings.binance_api_key,
            api_secret=settings.binance_api_secret,
            testnet=settings.binance_testnet
        )
        self.symbol = "BTCUSDT"
        # Binance BTCUSDT Futures precision requirements
        self.price_precision = 1  # Tick size: 0.1
        self.quantity_precision = 3  # Step size: 0.001
        
        logger.info(f"Binance client initialized (testnet: {settings.binance_testnet})")

    def _round_price(self, price: float) -> float:
        """
        Round price to correct precision for BTCUSDT.
        
        Args:
            price: Raw price value
            
        Returns:
            Rounded price (1 decimal place, e.g., 113456.7)
        """
        return round(price, self.price_precision)
    
    def _round_quantity(self, quantity: float) -> float:
        """
        Round quantity to correct precision for BTCUSDT.
        
        Args:
            quantity: Raw quantity value
            
        Returns:
            Rounded quantity (3 decimal places, e.g., 0.024)
        """
        return round(quantity, self.quantity_precision)

    def test_connection(self) -> bool:
        """Test Binance API connection."""
        try:
            # Test account info
            account_info = self.client.futures_account()
            
            if account_info:
                logger.info("✅ Binance API connected successfully")
                logger.info(f"Account balance: {account_info.get('totalWalletBalance', 'Unknown')} USDT")
                return True
            else:
                logger.error("❌ Binance API: No account info received")
                return False
                
        except Exception as e:
            logger.error(f"❌ Binance API connection failed: {e}")
            return False

    def get_account_balance(self) -> Dict:
        """Get account balance information."""
        try:
            account_info = self.client.futures_account()
            
            return {
                "total_balance": float(account_info.get("totalWalletBalance", 0)),
                "available_balance": float(account_info.get("availableBalance", 0)),
                "margin_balance": float(account_info.get("totalMarginBalance", 0)),
                "unrealized_pnl": float(account_info.get("totalUnrealizedProfit", 0))
            }
            
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return {"error": str(e)}

    def get_current_price(self) -> Optional[float]:
        """Get current BTC price."""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
            return float(ticker["price"])
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None

    def get_open_positions(self) -> List[Dict]:
        """Get all open positions with actual PnL from Binance."""
        try:
            positions = self.client.futures_position_information(symbol=self.symbol)
            
            open_positions = []
            for pos in positions:
                if float(pos["positionAmt"]) != 0:
                    unrealized_pnl = float(pos["unRealizedProfit"])
                    entry_price = float(pos["entryPrice"])
                    notional = abs(float(pos["positionAmt"]) * entry_price)
                    leverage = int(pos["leverage"])
                    
                    # Calculate margin and PnL percentage (ROI)
                    # ROI% = (PnL / Margin) * 100, where Margin = Notional / Leverage
                    margin = notional / leverage if leverage > 0 else notional
                    pnl_percentage = (unrealized_pnl / margin * 100) if margin > 0 else 0
                    
                    open_positions.append({
                        "symbol": pos["symbol"],
                        "side": "LONG" if float(pos["positionAmt"]) > 0 else "SHORT",
                        "size": abs(float(pos["positionAmt"])),
                        "entry_price": entry_price,
                        "mark_price": float(pos["markPrice"]),
                        "unrealized_pnl": unrealized_pnl,  # Actual PnL in USDT from Binance
                        "pnl_percentage": pnl_percentage,   # Calculated from actual PnL
                        "leverage": int(pos["leverage"]),
                        "notional": notional
                    })
            
            return open_positions
            
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            return []
    
    def get_position_pnl(self, symbol: str = None) -> Optional[Dict]:
        """Get comprehensive position data from Binance including all metrics."""
        try:
            if symbol is None:
                symbol = self.symbol
            
            # Get position data
            positions = self.client.futures_position_information(symbol=symbol)
            
            # Get account data for margin ratio
            account = self.client.futures_account()
            total_margin_balance = float(account.get('totalMarginBalance', 0))
            total_maint_margin = float(account.get('totalMaintMargin', 0))
            
            # Calculate account-level margin ratio
            if total_margin_balance > 0:
                margin_ratio = (total_maint_margin / total_margin_balance) * 100
            else:
                margin_ratio = 0
            
            for pos in positions:
                if float(pos["positionAmt"]) != 0:
                    unrealized_pnl = float(pos["unRealizedProfit"])
                    entry_price = float(pos["entryPrice"])
                    position_amt = float(pos["positionAmt"])
                    mark_price = float(pos["markPrice"])
                    liquidation_price = float(pos["liquidationPrice"]) if pos.get("liquidationPrice") else 0
                    notional = abs(position_amt * entry_price)
                    leverage = int(pos["leverage"])
                    
                    # Calculate margin (notional / leverage)
                    margin = notional / leverage if leverage > 0 else notional
                    
                    # Calculate PnL percentage (ROI) = (PnL / Margin) * 100
                    # This matches Binance's ROI% calculation
                    pnl_percentage = (unrealized_pnl / margin * 100) if margin > 0 else 0
                    
                    # Use Binance's calculated break-even price (includes fees and funding)
                    breakeven_price = float(pos.get("breakEvenPrice", entry_price))
                    
                    return {
                        "symbol": pos["symbol"],
                        "position_side": "LONG" if position_amt > 0 else "SHORT",
                        "position_amt": abs(position_amt),
                        "entry_price": entry_price,
                        "mark_price": mark_price,
                        "liquidation_price": liquidation_price,
                        "breakeven_price": breakeven_price,
                        "unrealized_pnl": unrealized_pnl,
                        "pnl_percentage": pnl_percentage,
                        "leverage": leverage,
                        "notional": notional,
                        "margin": margin,
                        "margin_ratio": margin_ratio,  # Already in percentage
                        "margin_type": pos.get("marginType", "cross").upper(),
                        "isolated_wallet": float(pos.get("isolatedWallet", 0))
                    }
            
            return None  # No open position
            
        except Exception as e:
            logger.error(f"Error getting position PnL: {e}")
            return None

    def get_realized_pnl_from_income(self, limit: int = 1) -> Optional[Dict]:
        """
        Get the most recent realized PnL from Binance income history.
        This should be called AFTER closing a position to get the actual realized PnL.
        
        Returns:
            Dictionary with realized_pnl, commission, and timestamp
        """
        try:
            # Get income history for REALIZED_PNL
            income = self.client.futures_income_history(
                symbol=self.symbol,
                incomeType="REALIZED_PNL",
                limit=limit
            )
            
            if not income:
                logger.warning("No realized PnL found in income history")
                return None
            
            # Get the most recent entry
            latest = income[0]
            
            # Also get commission for the same period
            commissions = self.client.futures_income_history(
                symbol=self.symbol,
                incomeType="COMMISSION",
                limit=5  # Get last 5 commissions (entry + exit)
            )
            
            # Sum commissions from the same timestamp (or very close)
            total_commission = 0
            latest_time = int(latest['time'])
            for comm in commissions:
                comm_time = int(comm['time'])
                # If within 1 minute of the close
                if abs(comm_time - latest_time) < 60000:
                    total_commission += abs(float(comm['income']))
            
            return {
                "realized_pnl": float(latest['income']),
                "commission": total_commission,
                "timestamp": latest_time,
                "asset": latest['asset']
            }
            
        except Exception as e:
            logger.error(f"Error getting realized PnL from income: {e}")
            return None

    def close_all_positions(self) -> bool:
        """Close all open positions."""
        try:
            positions = self.get_open_positions()
            
            if not positions:
                logger.info("No open positions to close")
                return True
            
            for pos in positions:
                side = "SELL" if pos["side"] == "LONG" else "BUY"
                
                order = self.client.futures_create_order(
                    symbol=self.symbol,
                    side=side,
                    type="MARKET",
                    quantity=pos["size"],
                    reduceOnly=True
                )
                
                logger.info(f"Closed {pos['side']} position: {order['orderId']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            return False

    def cancel_all_orders(self) -> bool:
        """Cancel all open orders."""
        try:
            orders = self.client.futures_get_open_orders(symbol=self.symbol)
            
            if not orders:
                logger.info("No open orders to cancel")
                return True
            
            for order in orders:
                self.client.futures_cancel_order(
                    symbol=self.symbol,
                    orderId=order["orderId"]
                )
                logger.info(f"Cancelled order: {order['orderId']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
            return False

    def set_leverage(self, leverage: int) -> bool:
        """Set leverage for the symbol."""
        try:
            self.client.futures_change_leverage(
                symbol=self.symbol,
                leverage=leverage
            )
            logger.info(f"Set leverage to {leverage}x")
            return True
            
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            return False

    def calculate_position_size(self, leverage: int, risk_percent: float = 1.0) -> float:
        """
        Calculate position size based on available balance and leverage.

        Args:
            leverage: Leverage multiplier
            risk_percent: Maximum risk percentage (default 1%)

        Returns:
            Position size in BTC
        """
        try:
            balance_info = self.get_account_balance()
            available_balance = balance_info.get("available_balance", 0)
            
            if available_balance <= 0:
                logger.error("No available balance for trading")
                return 0.0
            
            # Calculate position size with risk management
            # Use 95% of available balance to leave buffer for fees and margin requirements
            usable_balance = available_balance * 0.95
            
            # Calculate position notional value (balance * leverage)
            position_value = usable_balance * leverage
            
            # Convert to BTC quantity
            current_price = self.get_current_price()
            position_size = position_value / current_price
            
            # Round to 3 decimal places (BTC precision limit for futures)
            position_size = round(position_size, 3)
            
            logger.info(f"Position size calculated: {position_size:.6f} BTC")
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0

    def place_market_order(self, side: str, quantity: float) -> Optional[Dict]:
        """
        Place a market order.

        Args:
            side: "BUY" or "SELL"
            quantity: Order quantity in BTC

        Returns:
            Order information or None if failed
        """
        try:
            # Round quantity to correct precision
            rounded_qty = self._round_quantity(quantity)
            
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=side,
                type="MARKET",
                quantity=rounded_qty
            )
            
            logger.info(f"Market order placed: {side} {rounded_qty} BTC - {order['orderId']}")
            return order
            
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None

    def place_stop_loss_order(self, side: str, quantity: float, stop_price: float) -> Optional[Dict]:
        """
        Place a stop-loss order.

        Args:
            side: "BUY" or "SELL"
            quantity: Order quantity in BTC
            stop_price: Stop price

        Returns:
            Order information or None if failed
        """
        try:
            # Round to correct precision
            rounded_qty = self._round_quantity(quantity)
            rounded_stop_price = self._round_price(stop_price)
            
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=side,
                type="STOP_MARKET",
                quantity=rounded_qty,
                stopPrice=rounded_stop_price,
                reduceOnly=True
            )
            
            logger.info(f"Stop-loss order placed: {side} {rounded_qty} BTC at ${rounded_stop_price} - {order['orderId']}")
            return order
            
        except Exception as e:
            logger.error(f"Error placing stop-loss order: {e}")
            return None

    def place_trailing_stop_order(self, side: str, quantity: float, callback_rate: float) -> Optional[Dict]:
        """
        Place a trailing stop order.

        Args:
            side: "BUY" or "SELL"
            quantity: Order quantity in BTC
            callback_rate: Callback rate percentage

        Returns:
            Order information or None if failed
        """
        try:
            # Round quantity to correct precision
            rounded_qty = self._round_quantity(quantity)
            
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=side,
                type="TRAILING_STOP_MARKET",
                quantity=rounded_qty,
                callbackRate=callback_rate,
                reduceOnly=True
            )
            
            logger.info(f"Trailing stop order placed: {side} {rounded_qty} BTC at {callback_rate}% - {order['orderId']}")
            return order
            
        except Exception as e:
            logger.error(f"Error placing trailing stop order: {e}")
            return None

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get order status by ID."""
        try:
            order = self.client.futures_get_order(symbol=self.symbol, orderId=order_id)
            return order
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None

    def get_order_fees(self, order_id: str) -> Optional[float]:
        """Get actual fees paid for an order."""
        try:
            order = self.client.futures_get_order(symbol=self.symbol, orderId=order_id)
            if order and order.get('status') == 'FILLED':
                # Binance returns fees in the order response
                fees = float(order.get('commission', 0))
                logger.info(f"Order {order_id} fees: {fees} USDT")
                return fees
            return 0.0
        except Exception as e:
            logger.error(f"Error getting order fees: {e}")
            return None

    def get_trading_status(self) -> Dict:
        """Get current trading status."""
        try:
            balance = self.get_account_balance()
            positions = self.get_open_positions()
            price = self.get_current_price()
            
            return {
                "account_balance": balance,
                "open_positions": positions,
                "current_price": price,
                "symbol": self.symbol,
                "testnet": settings.binance_testnet
            }
            
        except Exception as e:
            logger.error(f"Error getting trading status: {e}")
            return {"error": str(e)}
