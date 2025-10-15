#!/usr/bin/env python3
"""
Telegram bot command handler for receiving and responding to commands.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List
from src.database.repository import DatabaseRepository
from src.analysis.sentiment_analyzer import SentimentAnalyzer
from src.trading.position_manager import PositionManager
from src.notifications.telegram_notifier import TelegramNotifier
from src.bot.trading_bot import TradingBot
from config.settings import settings
import requests
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBotHandler:
    """Handle Telegram bot commands."""
    
    def __init__(self):
        """Initialize the bot handler."""
        self.bot_token = settings.telegram_bot_token
        self.channel_id = settings.telegram_channel_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Initialize trading bot components
        self.db = DatabaseRepository()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.position_manager = PositionManager()
        self.telegram = TelegramNotifier()
        self.bot = TradingBot()
        
        logger.info("Telegram bot handler initialized")
    
    def get_updates(self, offset: int = None) -> List[Dict]:
        """Get updates from Telegram."""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {}
            if offset:
                params['offset'] = offset
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data.get("result", [])
                else:
                    logger.error(f"Telegram API error: {data}")
                    return []
            else:
                logger.error(f"Failed to get updates: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []
    
    def send_message_to_channel(self, text: str) -> bool:
        """Send message to the channel."""
        return self.telegram.send_message(text)
    
    def handle_command(self, update: Dict) -> None:
        """Handle a command from Telegram."""
        try:
            # Handle callback queries (button clicks)
            if "callback_query" in update:
                callback_query = update["callback_query"]
                data = callback_query.get("data", "")
                chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
                
                # Only respond to messages in our channel
                if str(chat_id) != str(self.channel_id):
                    return
                
                logger.info(f"✅ Received callback: {data}")
                
                if data == "get_position":
                    logger.info("🔹 Routing to: handle_position_command")
                    self.handle_position_command()
                elif data == "refresh_position":
                    logger.info("🔹 Routing to: handle_position_command (refresh)")
                    self.handle_position_command()  # Refresh position status
                elif data == "get_main_menu":
                    logger.info("🔹 Routing to: handle_main_menu_command")
                    self.handle_main_menu_command()  # Show main menu
                elif data == "refresh_main_menu":
                    logger.info("🔹 Routing to: handle_main_menu_command (refresh)")
                    self.handle_main_menu_command()  # Refresh main menu
                elif data == "get_trading_settings":
                    logger.info("🔹 Routing to: handle_trading_settings_command")
                    self.handle_trading_settings_command()  # Show trading settings
                elif data == "close_position_confirm":
                    logger.info("🔹 Routing to: handle_close_position_confirm")
                    self.handle_close_position_confirm()  # Ask for confirmation
                elif data == "close_position_execute":
                    logger.info("🔹 Routing to: handle_close_position_execute")
                    self.handle_close_position_execute()  # Actually close
                elif data == "close_position_cancel":
                    logger.info("🔹 Routing to: handle_close_position_cancel")
                    self.handle_close_position_cancel()  # Cancel close
                else:
                    logger.warning(f"❌ Unknown callback: {data}")
                return
            
            # Handle text messages
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            
            # Only respond to messages in our channel
            if str(chat_id) != str(self.channel_id):
                return
            
            logger.info(f"Received command: {text}")
            
            if text == "/status" or text == "/position":
                self.handle_position_command()
            elif text == "/refresh":
                self.handle_main_menu_command()
            else:
                logger.info(f"Unknown command: {text}")
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
    
    def handle_position_command(self) -> None:
        """Handle /status command (position)."""
        try:
            logger.info("Handling /status command (position)")
            self.bot._send_position_status()
        except Exception as e:
            logger.error(f"Error handling position command: {e}")
            self.send_message_to_channel("❌ Error getting position data")
    
    def handle_main_menu_command(self) -> None:
        """Handle main menu command - show/refresh main menu."""
        try:
            logger.info("Handling main menu command - showing/refreshing main menu")
            # Get fresh account info (already includes all fields)
            account_data = self.bot._get_account_info()
            
            # Send startup notification with complete data
            self.bot.telegram.notify_startup(account_data)
        except Exception as e:
            logger.error(f"Error handling main menu command: {e}")
            self.send_message_to_channel("❌ Error refreshing main menu data")
    
    def handle_trading_settings_command(self) -> None:
        """Handle trading settings command - show leverage map and risk settings."""
        try:
            logger.info("⚙️ Handling trading settings command")
            # Send trading settings
            result = self.bot.telegram.notify_trading_settings()
            if result:
                logger.info("✅ Trading settings sent successfully")
            else:
                logger.error("❌ Failed to send trading settings")
        except Exception as e:
            logger.error(f"❌ Error handling trading settings command: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.send_message_to_channel("❌ Error displaying trading settings")
    
    def handle_close_position_confirm(self) -> None:
        """Handle close position confirmation request."""
        try:
            logger.info("Handling close position confirmation request")
            # Get current position data
            open_trade = self.bot.db.get_open_trade()
            
            if not open_trade:
                self.send_message_to_channel("❌ No open position to close!")
                return
            
            # Get actual PnL from Binance
            binance_pnl = self.bot.position_manager.binance.get_position_pnl()
            
            if binance_pnl:
                # Use actual Binance data
                pnl_percentage = binance_pnl["pnl_percentage"]
                pnl_usd = binance_pnl["unrealized_pnl"]
            else:
                # Fallback to calculation
                current_price = self.bot.position_manager.binance.get_current_price()
                from src.utils.helpers import calculate_pnl_percentage
                pnl_percentage = calculate_pnl_percentage(
                    open_trade.entry_price,
                    current_price,
                    open_trade.side,
                    open_trade.leverage
                )
                pnl_usd = (pnl_percentage / 100) * open_trade.notional_value
            
            # Prepare position data for confirmation
            position_data = {
                "trade_id": open_trade.id,
                "side": open_trade.side,
                "pnl_percentage": pnl_percentage,
                "pnl_usd": pnl_usd
            }
            
            # Send confirmation message
            self.bot.telegram.notify_close_position_confirmation(position_data)
            
        except Exception as e:
            logger.error(f"Error handling close position confirmation: {e}")
            self.send_message_to_channel("❌ Error requesting position closure confirmation")
    
    def handle_close_position_execute(self) -> None:
        """Handle actual position closure."""
        try:
            logger.info("Handling position closure execution")
            
            # Send "closing..." message BEFORE closing
            self.send_message_to_channel("⏳ Closing position... Stand by for results...")
            
            # Close all positions (this will send the detailed results)
            success, error_msg = self.bot.close_all_positions()
            
            if not success:
                # Send detailed error message to Telegram
                error_text = f"❌ <b>FAILED TO CLOSE POSITION</b>\n\n"
                error_text += f"🔴 <b>Error Details:</b>\n"
                error_text += f"<code>{error_msg}</code>\n\n"
                error_text += f"📋 Check application logs for full traceback"
                self.send_message_to_channel(error_text)
                logger.error(f"Position close failed: {error_msg}")
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error executing position close: {e}")
            logger.error(error_trace)
            
            # Send detailed error to Telegram
            error_text = f"❌ <b>EXCEPTION DURING POSITION CLOSE</b>\n\n"
            error_text += f"🔴 <b>Error:</b> {type(e).__name__}\n"
            error_text += f"💬 <b>Message:</b> {str(e)}\n\n"
            error_text += f"📋 <b>Traceback:</b>\n"
            error_text += f"<code>{error_trace[-500:]}</code>"  # Last 500 chars
            self.send_message_to_channel(error_text)
    
    def handle_close_position_cancel(self) -> None:
        """Handle position closure cancellation."""
        try:
            logger.info("Position closure cancelled by user")
            self.send_message_to_channel("✅ Position close cancelled. Your position remains open.")
            # Show position status again
            self.handle_position_command()
            
        except Exception as e:
            logger.error(f"Error handling close cancellation: {e}")
            self.send_message_to_channel("❌ Error handling cancellation")
    
    def start_polling(self) -> None:
        """Start polling for updates."""
        logger.info("Starting Telegram bot polling...")
        last_update_id = None
        
        while True:
            try:
                updates = self.get_updates(last_update_id)
                
                for update in updates:
                    last_update_id = update.get("update_id", 0) + 1
                    self.handle_command(update)
                
                time.sleep(1)  # Poll every second
                
            except KeyboardInterrupt:
                logger.info("Stopping bot polling...")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(5)

def main():
    """Main function."""
    handler = TelegramBotHandler()
    handler.start_polling()

if __name__ == "__main__":
    main()
