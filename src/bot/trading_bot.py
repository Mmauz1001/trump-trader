"""Main trading bot orchestrator."""

import asyncio
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional

try:
    from src.analysis.sentiment_analyzer import SentimentAnalyzer
    SENTIMENT_AVAILABLE = True
except (ImportError, ModuleNotFoundError, TypeError):
    SENTIMENT_AVAILABLE = False
    SentimentAnalyzer = None
from src.database.repository import DatabaseRepository
# Twitter and Truth Social via RapidAPI
from src.monitors.twitter_rapidapi import TwitterRapidAPI as TwitterMonitor
from src.monitors.truthsocial_rapidapi import TruthSocialRapidAPI as TruthSocialMonitor

TWITTER_AVAILABLE = True
TWITTER_METHOD = "RapidAPI (30s)"
TRUTH_SOCIAL_AVAILABLE = True
TRUTH_SOCIAL_METHOD = "RapidAPI (30s)"
from src.notifications.telegram_notifier import TelegramNotifier
from src.trading.position_manager import PositionManager
from src.utils import setup_logger

logger = setup_logger(__name__)


class TradingBot:
    """Main trading bot orchestrator."""

    def __init__(self):
        """Initialize the trading bot."""
        self.db = DatabaseRepository()
        
        if SENTIMENT_AVAILABLE and SentimentAnalyzer is not None:
            try:
                self.sentiment_analyzer = SentimentAnalyzer()
            except ImportError:
                self.sentiment_analyzer = None
                logger.warning("Sentiment analyzer not available - running in limited mode")
        else:
            self.sentiment_analyzer = None
            logger.warning("Sentiment analyzer not available - running in limited mode")
        
        self.position_manager = PositionManager()
        self.telegram = TelegramNotifier()
        
        # Twitter and Truth Social via RapidAPI
        self.twitter_monitor = TwitterMonitor(on_new_post=self._on_new_post)
        logger.info(f"Using Twitter monitor: {TWITTER_METHOD}")
        
        self.truthsocial_monitor = TruthSocialMonitor(on_new_post=self._on_new_post)
        logger.info(f"Using Truth Social monitor: {TRUTH_SOCIAL_METHOD}")
        
        # Bot state
        self.is_running = False
        self.monitoring_threads = []
        
        logger.info("Trading bot initialized")

    def test_all_connections(self) -> Dict[str, bool]:
        """Test all API connections."""
        logger.info("Testing all API connections...")
        
        results = {
            "twitter": self.twitter_monitor.test_connection() if self.twitter_monitor else False,
            "truth_social": self.truthsocial_monitor.test_connection() if self.truthsocial_monitor else False,
            "claude": self.sentiment_analyzer.test_connection() if self.sentiment_analyzer else False,
            "binance": self.position_manager.binance.test_connection(),
            "telegram": self.telegram.test_connection()
        }
        
        # Log results
        for service, status in results.items():
            status_icon = "✅" if status else "❌"
            logger.info(f"{status_icon} {service.upper()}: {'Connected' if status else 'Failed'}")
        
        return results

    def _on_new_post(self, post_data: Dict) -> None:
        """
        Handle new social media post.

        Args:
            post_data: Post data from social media monitor
        """
        try:
            logger.info(f"New post detected: {post_data['platform']}")
            
            # Perform sentiment analysis
            if self.sentiment_analyzer:
                sentiment_result = self.sentiment_analyzer.process_post(post_data)
                
                if not sentiment_result:
                    logger.error("Sentiment analysis failed")
                    return
                
                # Notify about post with combined sentiment analysis
                self.telegram.notify_post_with_sentiment(post_data, sentiment_result)
                
                # Check if we should trade
                should_trade, reason = self.position_manager.should_trade(sentiment_result["score"])
                
                if not should_trade:
                    logger.info(f"Not trading: {reason}")
                    return
                
                # Check if we already have an open position
                open_trade = self.db.get_open_trade()
                if open_trade:
                    logger.info("Position already open, skipping new trade")
                    return
                
                # Prepare and execute trade
                trade_params = self.position_manager.prepare_trade(sentiment_result["score"])
                
                if not trade_params:
                    logger.error("Failed to prepare trade")
                    return
                
                # Execute trade
                trade_result = self.position_manager.execute_trade(
                    trade_params, 
                    sentiment_result["sentiment_id"]
                )
                
                # Send position status after trade execution
                if trade_result:
                    self._send_position_status()
            else:
                logger.warning("Sentiment analyzer not available - skipping analysis and trading")
                return
            
            if trade_result:
                # Notify about trade execution
                self.telegram.notify_trade_execution(trade_result)
                logger.info("✅ Trade executed successfully")
            else:
                logger.error("❌ Trade execution failed")
                
        except Exception as e:
            logger.error(f"Error handling new post: {e}")
            self.telegram.notify_error({
                "type": "Post Processing Error",
                "message": str(e),
                "component": "TradingBot"
            })

    def _send_position_status(self) -> None:
        """Send current position status to Telegram."""
        try:
            open_trade = self.db.get_open_trade()
            if open_trade:
                # Get actual PnL from Binance (includes leverage and fees)
                binance_pnl = self.position_manager.binance.get_position_pnl()
                
                if binance_pnl:
                    # Use comprehensive Binance data
                    current_price = binance_pnl["mark_price"]
                    pnl_percentage = binance_pnl["pnl_percentage"]
                    pnl_usd = binance_pnl["unrealized_pnl"]
                    symbol = binance_pnl["symbol"]
                    breakeven_price = binance_pnl["breakeven_price"]
                    mark_price = binance_pnl["mark_price"]
                    liquidation_price = binance_pnl["liquidation_price"]
                    margin = binance_pnl["margin"]
                    margin_ratio = binance_pnl["margin_ratio"]
                    margin_type = binance_pnl["margin_type"]
                else:
                    # Fallback to calculation if Binance data unavailable
                    current_price = self.position_manager.binance.get_current_price()
                    from src.utils.helpers import calculate_pnl_percentage
                    pnl_percentage = calculate_pnl_percentage(
                        open_trade.entry_price,
                        current_price,
                        open_trade.side,
                        open_trade.leverage
                    )
                    pnl_usd = (pnl_percentage / 100) * open_trade.notional_value
                    # Use defaults for missing Binance data
                    symbol = "BTCUSDT"
                    breakeven_price = open_trade.entry_price * 1.001  # Approximate
                    mark_price = current_price
                    liquidation_price = 0
                    margin = open_trade.notional_value / open_trade.leverage
                    margin_ratio = 0
                    margin_type = "CROSS"
                
                # Calculate fees - try to get actual fees first, fallback to estimate
                actual_fees = 0.0
                if open_trade.entry_order_id:
                    actual_fees = self.position_manager.binance.get_order_fees(open_trade.entry_order_id) or 0.0
                
                if actual_fees > 0:
                    fees = actual_fees
                else:
                    # Fallback to estimate (Binance USDT-M futures: 0.05% taker fee)
                    fees = open_trade.notional_value * 0.0005
                
                # Format created_at timestamp
                created_at_str = open_trade.opened_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(open_trade, 'opened_at') else "Unknown"
                
                # Get funding fees since position opened
                funding_fee = 0.0
                try:
                    import time
                    start_time = int(open_trade.opened_at.timestamp() * 1000) if hasattr(open_trade, 'opened_at') else None
                    if start_time:
                        end_time = int(time.time() * 1000)
                        funding_history = self.position_manager.binance.client.futures_income_history(
                            incomeType="FUNDING_FEE",
                            startTime=start_time,
                            endTime=end_time,
                            limit=1000
                        )
                        funding_fee = sum(float(entry['income']) for entry in funding_history)
                except Exception as e:
                    logger.warning(f"Could not fetch funding fees: {e}")
                
                # Get ACTUAL stop orders from Binance
                stop_orders = self.position_manager.binance.get_stop_orders()
                
                # Use actual stop-loss price if order exists, otherwise use database value
                if stop_orders["stop_loss"]:
                    stop_loss_price = stop_orders["stop_loss"]["stop_price"]
                    stop_loss_active = True
                else:
                    stop_loss_price = open_trade.fixed_stop_loss_price
                    stop_loss_active = False
                
                # Use actual trailing stop callback rate if order exists, otherwise use database value
                if stop_orders["trailing_stop"]:
                    trailing_callback_rate = stop_orders["trailing_stop"]["callback_rate"]
                    trailing_stop_active = True
                else:
                    trailing_callback_rate = open_trade.trailing_callback_rate
                    trailing_stop_active = False
                
                position_data = {
                    "trade_id": open_trade.id,
                    "side": open_trade.side,
                    "leverage": open_trade.leverage,
                    "quantity": open_trade.quantity,
                    "notional_value": open_trade.notional_value,
                    "entry_price": open_trade.entry_price,
                    "current_price": current_price,
                    "pnl_percentage": pnl_percentage,
                    "pnl_usd": pnl_usd,
                    "stop_loss_price": stop_loss_price,
                    "stop_loss_active": stop_loss_active,
                    "trailing_callback_rate": trailing_callback_rate,
                    "trailing_stop_active": trailing_stop_active,
                    "fees": fees,
                    "funding_fee": funding_fee,
                    "created_at": created_at_str,
                    # Comprehensive Binance data
                    "symbol": symbol,
                    "breakeven_price": breakeven_price,
                    "mark_price": mark_price,
                    "liquidation_price": liquidation_price,
                    "margin": margin,
                    "margin_ratio": margin_ratio,
                    "margin_type": margin_type
                }
            else:
                position_data = None
            
            self.telegram.notify_position_status(position_data)
            
        except Exception as e:
            logger.error(f"Error sending position status: {e}")

    def _get_account_info(self) -> Dict:
        """Get account information for startup notification."""
        try:
            # Get account balance and details from Binance
            account_info = self.position_manager.binance.get_account_balance()
            balance = account_info.get("total_balance", 0)
            available_balance = account_info.get("available_balance", 0)
            margin_balance = account_info.get("margin_balance", 0)
            unrealized_pnl = account_info.get("unrealized_pnl", 0)
            
            # Get trading mode
            from config.settings import settings
            trading_mode = "LIVE" if not settings.binance_testnet else "TESTNET"
            
            # Get open positions count
            open_trade = self.db.get_open_trade()
            open_positions = 1 if open_trade else 0
            
            # Get total trades count
            total_trades = self.db.get_total_trades_count()
            
            # Calculate actual 24h PnL from Binance income history (includes all fees)
            # This is more accurate than database as it includes entry/exit fees
            try:
                from datetime import datetime, timedelta
                import time
                
                # Get current timestamp
                end_time = int(time.time() * 1000)
                # Get 24 hours ago timestamp
                start_time = int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp() * 1000)
                
                # Fetch REALIZED_PNL from Binance income history
                realized_pnl = self.position_manager.binance.client.futures_income_history(
                    incomeType="REALIZED_PNL",
                    startTime=start_time,
                    endTime=end_time,
                    limit=1000
                )
                
                # Fetch COMMISSION from Binance income history
                commissions = self.position_manager.binance.client.futures_income_history(
                    incomeType="COMMISSION",
                    startTime=start_time,
                    endTime=end_time,
                    limit=1000
                )
                
                # Fetch FUNDING_FEE from Binance income history
                funding_fees = self.position_manager.binance.client.futures_income_history(
                    incomeType="FUNDING_FEE",
                    startTime=start_time,
                    endTime=end_time,
                    limit=1000
                )
                
                # Sum all realized PnL, commissions, and funding fees
                realized_pnl_sum = sum(float(entry['income']) for entry in realized_pnl)
                commission_24h = sum(float(entry['income']) for entry in commissions)
                funding_24h = sum(float(entry['income']) for entry in funding_fees)
                
                # Total = PnL + Commission + Funding (can be positive or negative)
                pnl_24h = realized_pnl_sum + commission_24h + funding_24h
                
                logger.info(f"24h PnL from Binance: PnL={realized_pnl_sum:.2f}, Commission={commission_24h:.2f}, Funding={funding_24h:.2f}, Total={pnl_24h:.2f}")
            except Exception as e:
                logger.warning(f"Could not fetch 24h PnL from Binance, falling back to database: {e}")
                # Fallback to database
                pnl_24h = 0
                trades_24h = self.db.get_trades_last_24h()
                for trade in trades_24h:
                    if trade.pnl_usd is not None:
                        pnl_24h += trade.pnl_usd
            
            # Get rate limit info from monitors
            # Always fetch fresh rate limits by triggering test connections
            twitter_rate_limit = {}
            truthsocial_rate_limit = {}
            
            if self.twitter_monitor:
                logger.info("Fetching fresh Twitter rate limits...")
                self.twitter_monitor.test_connection()
                twitter_status = self.twitter_monitor.get_monitoring_status()
                twitter_rate_limit = twitter_status.get("rate_limit", {})
                logger.info(f"Twitter rate limit for startup: {twitter_rate_limit}")
            
            if self.truthsocial_monitor:
                logger.info("Fetching fresh Truth Social rate limits...")
                self.truthsocial_monitor.test_connection()
                truthsocial_status = self.truthsocial_monitor.get_monitoring_status()
                truthsocial_rate_limit = truthsocial_status.get("rate_limit", {})
                logger.info(f"Truth Social rate limit for startup: {truthsocial_rate_limit}")
            
            return {
                "balance": float(balance),
                "available_balance": float(available_balance),
                "margin_balance": float(margin_balance),
                "unrealized_pnl": float(unrealized_pnl),
                "trading_mode": trading_mode,
                "open_positions": open_positions,
                "total_trades": total_trades,
                "pnl_24h": pnl_24h,
                "twitter_rate_limit": twitter_rate_limit,
                "truthsocial_rate_limit": truthsocial_rate_limit
            }
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {
                "balance": 0,
                "trading_mode": "UNKNOWN",
                "open_positions": 0,
                "total_trades": 0,
                "pnl_24h": 0
            }

    def start_monitoring(self) -> None:
        """Start monitoring social media accounts."""
        if self.is_running:
            logger.warning("Bot is already running")
            return
        
        logger.info("Starting social media monitoring...")
        
        # Test connections first
        connection_results = self.test_all_connections()
        failed_connections = [k for k, v in connection_results.items() if not v]
        
        # Check if we have Twitter monitoring and sentiment analysis
        has_twitter = connection_results.get("twitter", False)
        has_sentiment = connection_results.get("claude", False)
        
        if not has_twitter:
            logger.error("Twitter RapidAPI not available - REQUIRED")
            logger.error("Cannot start monitoring without Twitter data source")
            return
        
        if not has_sentiment:
            logger.error("Sentiment analysis not available")
            logger.error("Cannot start trading without sentiment analysis")
            return
        
        if failed_connections:
            logger.warning(f"Some services unavailable: {failed_connections}")
            logger.warning("Starting with available services only")
        
        # Send startup notification with account info
        try:
            # Wait a moment for APIs to fully initialize
            import time
            time.sleep(2)
            account_info = self._get_account_info()
            self.telegram.notify_startup(account_info)
            logger.info("Startup notification sent with account info")
        except Exception as e:
            logger.error(f"Error sending startup notification: {e}")
            # Fallback to simple test message
            self.telegram.send_test_message()
        
        # Start monitoring threads
        self.is_running = True
        
        # Twitter monitoring
        if self.twitter_monitor:
            twitter_thread = threading.Thread(
                target=self.twitter_monitor.start_monitoring,
                name="TwitterMonitor"
            )
            twitter_thread.daemon = True
            twitter_thread.start()
            self.monitoring_threads.append(twitter_thread)
            logger.info("Twitter monitoring started")
        else:
            logger.warning("Twitter monitoring not available")
        
        # Truth Social monitoring
        if self.truthsocial_monitor:
            truthsocial_thread = threading.Thread(
                target=self.truthsocial_monitor.start_monitoring,
                name="TruthSocialMonitor"
            )
            truthsocial_thread.daemon = True
            truthsocial_thread.start()
            self.monitoring_threads.append(truthsocial_thread)
            logger.info("Truth Social monitoring started")
        else:
            logger.warning("Truth Social monitoring not available")
        
        logger.info("🚀 Social media monitoring started (Twitter + Truth Social)")
        logger.info("Bot is now running and monitoring for new posts...")

    def stop_monitoring(self) -> None:
        """Stop monitoring social media accounts."""
        if not self.is_running:
            logger.warning("Bot is not running")
            return
        
        logger.info("Stopping social media monitoring...")
        
        # Stop monitors
        if self.twitter_monitor:
            self.twitter_monitor.stop_monitoring()
        if self.truthsocial_monitor:
            self.truthsocial_monitor.stop_monitoring()
        
        # Wait for threads to finish
        for thread in self.monitoring_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.monitoring_threads.clear()
        self.is_running = False
        
        logger.info("✅ Social media monitoring stopped")

    def get_status(self) -> Dict:
        """Get current bot status."""
        try:
            # Get monitoring status
            twitter_status = self.twitter_monitor.get_monitoring_status() if self.twitter_monitor else {"error": "Twitter monitor not available"}
            # Truth Social removed entirely
            
            # Get trading status
            trading_status = self.position_manager.get_trading_status()
            
            # Get recent sentiment summary
            sentiment_summary = self.sentiment_analyzer.get_sentiment_summary(hours=24) if self.sentiment_analyzer else {"error": "Sentiment analyzer not available"}
            
            return {
                "bot_running": self.is_running,
                "monitoring": {
                    "twitter": twitter_status
                },
                "trading": trading_status,
                "sentiment_summary": sentiment_summary,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return {"error": str(e)}

    def close_all_positions(self) -> tuple[bool, str]:
        """
        Close all open positions.
        
        Returns:
            Tuple of (success, error_message). If successful, error_message is empty.
        """
        try:
            logger.info("Closing all open positions...")
            
            # Get open trade
            open_trade = self.db.get_open_trade()
            
            if not open_trade:
                logger.info("No open positions to close")
                return True, ""
            
            # Close position
            success = self.position_manager.close_position(
                open_trade.id, 
                "MANUAL_CLOSE"
            )
            
            if success:
                logger.info("✅ All positions closed")
                
                # Get the closed trade data for notification
                closed_trade = self.db.get_trade_by_id(open_trade.id)
                if closed_trade and not closed_trade.is_open:
                    # Get fees - try actual fees first, fallback to estimate
                    actual_fees = 0.0
                    if closed_trade.entry_order_id:
                        actual_fees = self.position_manager.binance.get_order_fees(closed_trade.entry_order_id) or 0.0
                    
                    fees = actual_fees if actual_fees > 0 else (closed_trade.notional_value * 0.0005)
                    
                    # Get funding fees since position opened
                    funding_fee = 0.0
                    try:
                        import time
                        start_time = int(closed_trade.opened_at.timestamp() * 1000) if hasattr(closed_trade, 'opened_at') else None
                        if start_time:
                            end_time = int(time.time() * 1000)
                            funding_history = self.position_manager.binance.client.futures_income_history(
                                incomeType="FUNDING_FEE",
                                startTime=start_time,
                                endTime=end_time,
                                limit=1000
                            )
                            funding_fee = sum(float(entry['income']) for entry in funding_history)
                    except Exception as e:
                        logger.warning(f"Could not fetch funding fees: {e}")
                    
                    # Format opened_at timestamp
                    opened_at_str = closed_trade.opened_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(closed_trade, 'opened_at') else "Unknown"
                    
                    # Send comprehensive close notification
                    close_data = {
                        "trade_id": closed_trade.id,
                        "side": closed_trade.side,
                        "leverage": closed_trade.leverage,
                        "entry_price": closed_trade.entry_price,
                        "exit_price": closed_trade.exit_price,
                        "quantity": closed_trade.quantity,
                        "notional_value": closed_trade.notional_value,
                        "pnl_percentage": closed_trade.pnl_percentage,
                        "pnl_usd": closed_trade.pnl_usd,
                        "close_reason": closed_trade.close_reason or "MANUAL_CLOSE",
                        "symbol": closed_trade.symbol,
                        "fees": fees,
                        "funding_fee": funding_fee,
                        "opened_at": opened_at_str
                    }
                    self.telegram.notify_position_closed(close_data)
                
                return True, ""
            else:
                error_msg = "Failed to close position on exchange - check position_manager logs"
                logger.error(f"❌ {error_msg}")
                return False, error_msg
                
        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Error closing positions: {error_msg}")
            logger.error(traceback.format_exc())
            return False, error_msg

    def run_forever(self) -> None:
        """Run the bot forever (for production use)."""
        try:
            self.start_monitoring()
            
            # Keep the main thread alive
            while self.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            self.stop_monitoring()
            logger.info("Bot shutdown complete")
