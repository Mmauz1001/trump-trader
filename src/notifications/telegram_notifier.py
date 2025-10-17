"""Telegram notification system."""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from config.settings import settings
from src.utils import format_currency, setup_logger

logger = setup_logger(__name__)


class TelegramNotifier:
    """Telegram notification system."""

    def __init__(self):
        """Initialize Telegram notifier."""
        self.bot_token = settings.telegram_bot_token
        self.channel_id = settings.telegram_channel_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        logger.info("Telegram notifier initialized")

    def test_connection(self) -> bool:
        """Test Telegram bot connection."""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get("ok"):
                    logger.info(f"✅ Telegram bot connected: @{bot_info['result']['username']}")
                    return True
                else:
                    logger.error(f"❌ Telegram API error: {bot_info}")
                    return False
            else:
                logger.error(f"❌ Telegram connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Telegram connection failed: {e}")
            return False

    def send_message(self, text: str, parse_mode: str = "HTML", reply_markup: Dict = None) -> bool:
        """
        Send a message to the Telegram channel.

        Args:
            text: Message text
            parse_mode: Parse mode (HTML or Markdown)
            reply_markup: Inline keyboard markup

        Returns:
            True if successful
        """
        try:
            data = {
                "chat_id": self.channel_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            if reply_markup:
                data["reply_markup"] = reply_markup
            
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info("✅ Telegram message sent successfully")
                    return True
                else:
                    logger.error(f"❌ Telegram API error: {result}")
                    return False
            else:
                logger.error(f"❌ Telegram send failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending Telegram message: {e}")
            return False

    def notify_new_post(self, post_data: Dict) -> bool:
        """
        Notify about a new social media post.

        Args:
            post_data: Post data from social media monitor

        Returns:
            True if successful
        """
        try:
            platform = post_data["platform"]
            content = post_data["content"]
            posted_at = post_data["posted_at"]
            
            # Format timestamp
            if isinstance(posted_at, str):
                posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
            
            timestamp = posted_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Show full content (Telegram supports up to 4096 characters)
            if len(content) > 4000:
                content = content[:4000] + "..."
            
            # Create message
            message = f"""🚨 <b>NEW {platform} POST</b>

📅 <b>Time:</b> {timestamp}
📱 <b>Platform:</b> {platform}

📝 <b>Full Post:</b>
{content}

⏳ <b>Status:</b> Analyzing sentiment..."""

            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error notifying new post: {e}")
            return False

    def notify_post_with_sentiment(self, post_data: Dict, sentiment_result: Dict) -> bool:
        """
        Notify about a new post with combined sentiment analysis.

        Args:
            post_data: Post data from social media monitor
            sentiment_result: Sentiment analysis result

        Returns:
            True if successful
        """
        try:
            platform = post_data["platform"]
            content = post_data["content"]
            created_at = post_data.get("created_at") or post_data.get("posted_at")
            score = sentiment_result["score"]
            reasoning = sentiment_result["reasoning"]
            
            # Format timestamp
            if isinstance(created_at, str):
                # Handle different timestamp formats
                try:
                    # Try ISO format first (Truth Social)
                    if "T" in created_at:
                        posted_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    else:
                        # Try Twitter format: "Tue Oct 14 17:20:04 +0000 2025"
                        posted_at = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                except (ValueError, AttributeError):
                    # Fallback to current time
                    posted_at = datetime.now(timezone.utc)
            else:
                posted_at = created_at
            
            timestamp = posted_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Show full content (Telegram supports up to 4096 characters)
            if len(content) > 3000:  # Leave room for sentiment analysis
                content = content[:3000] + "..."
            
            # Determine sentiment emoji and action
            if score > 5:
                sentiment_emoji = "🟢"
                sentiment_text = "BULLISH"
                action_text = "LONG Signal"
            elif score < 5:
                sentiment_emoji = "🔴"
                sentiment_text = "BEARISH"
                action_text = "SHORT Signal"
            else:
                sentiment_emoji = "🟡"
                sentiment_text = "NEUTRAL"
                action_text = "No Action"
            
            # Create message
            message = f"""🚨 <b>NEW {platform} POST</b>

📅 <b>Time:</b> {timestamp}
📱 <b>Platform:</b> {platform}

📝 <b>Full Post:</b>
{content}

📊 <b>Sentiment Analysis:</b>
{sentiment_emoji} <b>Score:</b> {score}/10 ({sentiment_text})
🎯 <b>Action:</b> {action_text}

💭 <b>Reasoning:</b>
{reasoning[:500]}{'...' if len(reasoning) > 500 else ''}"""

            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error notifying post with sentiment: {e}")
            return False

    def notify_sentiment_analysis(self, sentiment_data: Dict) -> bool:
        """
        Notify about sentiment analysis results.

        Args:
            sentiment_data: Sentiment analysis data

        Returns:
            True if successful
        """
        try:
            score = sentiment_data["score"]
            reasoning = sentiment_data["reasoning"]
            platform = sentiment_data["platform"]
            content = sentiment_data["content"]
            
            # Determine sentiment emoji and color
            if score > 5:
                emoji = "🟢"
                sentiment_text = "BULLISH"
            elif score < 5:
                emoji = "🔴"
                sentiment_text = "BEARISH"
            else:
                emoji = "🟡"
                sentiment_text = "NEUTRAL"
            
            # Truncate content if too long
            if len(content) > 300:
                content = content[:300] + "..."
            
            # Create message
            message = f"""📊 <b>SENTIMENT ANALYSIS COMPLETE</b>

{emoji} <b>Sentiment:</b> {sentiment_text} ({score}/10)
📱 <b>Platform:</b> {platform}

💭 <b>Reasoning:</b>
{reasoning}

💬 <b>Content:</b>
{content}

🤖 <b>Next:</b> Evaluating trading decision..."""

            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error notifying sentiment analysis: {e}")
            return False

    def notify_trade_execution(self, trade_data: Dict) -> bool:
        """
        Notify about trade execution.

        Args:
            trade_data: Trade execution data

        Returns:
            True if successful
        """
        try:
            side = trade_data["side"]
            leverage = trade_data["leverage"]
            entry_price = trade_data["entry_price"]
            position_size = trade_data["position_size"]
            sentiment_score = trade_data["sentiment_score"]
            simulated = trade_data.get("simulated", False)
            
            # Determine side emoji
            side_emoji = "🟢" if side == "BUY" else "🔴"
            side_text = "LONG" if side == "BUY" else "SHORT"
            
            # Format values
            formatted_price = format_currency(entry_price)
            formatted_size = f"{position_size:.6f} BTC"
            formatted_value = format_currency(entry_price * position_size)
            
            # Get additional trade data
            stop_loss_price = trade_data.get("stop_loss_price", 0)
            trailing_callback_rate = trade_data.get("callback_rate", 0)
            fees = trade_data.get("fees", 0)
            order_id = trade_data.get("order_id", "N/A")
            
            # Calculate stop loss percentage
            stop_loss_pct = abs((stop_loss_price - entry_price) / entry_price) * 100 if stop_loss_price > 0 else 0
            
            # Calculate actual trailing stop price
            if trailing_callback_rate > 0:
                if side == "LONG":
                    trailing_stop_price = entry_price * (1 - trailing_callback_rate / 100)
                else:  # SHORT
                    trailing_stop_price = entry_price * (1 + trailing_callback_rate / 100)
                trailing_stop_pct = abs((trailing_stop_price - entry_price) / entry_price) * 100
                trailing_stop_text = f"${trailing_stop_price:,.2f} ({trailing_stop_pct:.1f}% away)"
            else:
                trailing_stop_text = "Not Set"
            
            # Create message
            if simulated:
                message = f"""🎯 <b>DRY RUN: TRADE EXECUTED</b>

🆔 <b>Order ID:</b> {order_id}
{side_emoji} <b>Position:</b> {side_text} {leverage}x
📊 <b>Size:</b> {formatted_size}
💵 <b>Notional Value:</b> {formatted_value}

💰 <b>PRICING:</b>
   Entry Price: {formatted_price}
   Stop Loss: ${stop_loss_price:,.2f} ({stop_loss_pct:.1f}% away)
   Trailing Stop: {trailing_stop_text}

🛡️ <b>RISK MANAGEMENT:</b>
   Fixed Stop-Loss: 1% max loss
   Trailing Rate: {trailing_callback_rate:.1f}% callback

💸 <b>Estimated Fees:</b> ${fees:.4f}
📈 <b>Sentiment Score:</b> {sentiment_score}/10

⚠️ <b>SIMULATED TRADE - NO REAL MONEY AT RISK</b>"""
            else:
                message = f"""🎯 <b>LIVE TRADE EXECUTED</b>

🆔 <b>Order ID:</b> {order_id}
{side_emoji} <b>Position:</b> {side_text} {leverage}x
📊 <b>Size:</b> {formatted_size}
💵 <b>Notional Value:</b> {formatted_value}

💰 <b>PRICING:</b>
   Entry Price: {formatted_price}
   Stop Loss: ${stop_loss_price:,.2f} ({stop_loss_pct:.1f}% away)
   Trailing Stop: {trailing_stop_text}

🛡️ <b>RISK MANAGEMENT:</b>
   Fixed Stop-Loss: 1% max loss
   Trailing Rate: {trailing_callback_rate:.1f}% callback

💸 <b>Estimated Fees:</b> ${fees:.4f}
📈 <b>Sentiment Score:</b> {sentiment_score}/10

🚨 <b>LIVE TRADE - REAL MONEY AT RISK</b>"""

            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error notifying trade execution: {e}")
            return False

    def notify_position_update(self, update_data: Dict) -> bool:
        """
        Notify about position updates.

        Args:
            update_data: Position update data

        Returns:
            True if successful
        """
        try:
            trade_id = update_data["trade_id"]
            current_price = update_data["current_price"]
            pnl_percentage = update_data["pnl_percentage"]
            pnl_usd = update_data["pnl_usd"]
            
            # Determine PnL emoji
            if pnl_percentage > 0:
                pnl_emoji = "🟢"
            elif pnl_percentage < 0:
                pnl_emoji = "🔴"
            else:
                pnl_emoji = "🟡"
            
            # Format values
            formatted_price = format_currency(current_price)
            formatted_pnl = format_currency(pnl_usd)
            
            # Create message
            message = f"""📊 <b>POSITION UPDATE</b>

🆔 <b>Trade ID:</b> {trade_id}
💰 <b>Current Price:</b> {formatted_price}
{pnl_emoji} <b>PnL:</b> {pnl_percentage:+.2f}% ({formatted_pnl})

⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"""

            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error notifying position update: {e}")
            return False

    def notify_position_closed(self, close_data: Dict) -> bool:
        """
        Notify about position closure with comprehensive results.

        Args:
            close_data: Position close data

        Returns:
            True if successful
        """
        try:
            # Required fields
            trade_id = close_data["trade_id"]
            exit_price = close_data["exit_price"]
            pnl_percentage = close_data["pnl_percentage"]
            pnl_usd = close_data["pnl_usd"]
            close_reason = close_data.get("close_reason", "UNKNOWN")
            
            # Optional fields with defaults
            side = close_data.get("side", "UNKNOWN")
            leverage = close_data.get("leverage", 0)
            entry_price = close_data.get("entry_price", 0)
            quantity = close_data.get("quantity", 0)
            notional_value = close_data.get("notional_value", 0)
            symbol = close_data.get("symbol", "BTCUSDT")
            fees = close_data.get("fees", 0)
            funding_fee = close_data.get("funding_fee", 0)
            opened_at = close_data.get("opened_at", "Unknown")
            
            # Determine result emoji and status
            if pnl_percentage > 0:
                status_emoji = "✅"
                status_text = "PROFIT"
                pnl_emoji = "🟢"
            elif pnl_percentage < 0:
                status_emoji = "❌"
                status_text = "LOSS"
                pnl_emoji = "🔴"
            else:
                status_emoji = "⚪"
                status_text = "BREAKEVEN"
                pnl_emoji = "🟡"
            
            # Format close reason
            reason_display = close_reason.replace("_", " ").title()
            
            # Calculate price change
            price_change = exit_price - entry_price if entry_price > 0 else 0
            price_change_pct = (price_change / entry_price * 100) if entry_price > 0 else 0
            
            # Calculate individual fees
            entry_fee = notional_value * 0.0005  # 0.05% taker fee
            exit_fee = notional_value * 0.0005   # 0.05% taker fee
            total_commission = entry_fee + exit_fee
            
            # Format funding fee emoji
            funding_emoji = '📈' if funding_fee > 0 else '📉' if funding_fee < 0 else '⚪'
            
            # Calculate Gross P/L by ADDING fees back to Net P/L
            # Net P/L comes from Binance REALIZED_PNL (already has fees deducted)
            # Gross P/L = Net P/L + All Fees
            total_fees = total_commission + abs(funding_fee)  # funding_fee can be negative (cost)
            gross_pnl = pnl_usd + total_fees
            gross_pnl_pct = (gross_pnl / notional_value * 100) if notional_value > 0 else 0
            
            message = f"""{status_emoji} <b>POSITION CLOSED - {status_text}</b>

🆔 <b>Trade ID:</b> {trade_id}
🔤 <b>Symbol:</b> {symbol} Perp
📈 <b>Side:</b> {side} {leverage}x
📦 <b>Size:</b> {quantity:.6f} BTC
💰 <b>Notional:</b> ${notional_value:,.2f} USDT

💵 <b>PRICING:</b>
   📍 Entry Price: ${entry_price:,.2f}
   🏁 Exit Price: ${exit_price:,.2f}
   📊 Change: ${price_change:+,.2f} ({price_change_pct:+.4f}%)

{pnl_emoji} <b>PROFIT/LOSS BREAKDOWN:</b>
   Gross P/L: ${gross_pnl:+.2f} ({gross_pnl_pct:+.2f}%)
   - Entry Fee: ${entry_fee:.4f}
   - Exit Fee: ${exit_fee:.4f}
   - Funding Fee: ${funding_fee:+.4f} {funding_emoji}
   ━━━━━━━━━━━━━━━━━━━━━━
   <b>Net P/L: ${pnl_usd:+.2f} ({pnl_percentage:+.2f}%)</b>

🔄 <b>Close Reason:</b> {reason_display}

⏰ <b>Opened:</b> {opened_at}
🏁 <b>Closed:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

"""
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error notifying position closure: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def notify_close_position_confirmation(self, position_data: Dict) -> bool:
        """
        Ask for confirmation before closing position.

        Args:
            position_data: Current position data for display

        Returns:
            True if successful
        """
        try:
            trade_id = position_data.get("trade_id", "N/A")
            side = position_data.get("side", "UNKNOWN")
            pnl_percentage = position_data.get("pnl_percentage", 0)
            pnl_usd = position_data.get("pnl_usd", 0)
            
            # Determine PnL emoji and text
            if pnl_percentage > 0:
                pnl_emoji = "🟢"
                pnl_text = f"+{pnl_percentage:.2f}% (+${abs(pnl_usd):.2f})"
            elif pnl_percentage < 0:
                pnl_emoji = "🔴"
                pnl_text = f"{pnl_percentage:.2f}% (-${abs(pnl_usd):.2f})"
            else:
                pnl_emoji = "🟡"
                pnl_text = f"{pnl_percentage:.2f}% ($0.00)"
            
            message = f"""⚠️ <b>CLOSE POSITION CONFIRMATION</b>

🆔 <b>Trade ID:</b> {trade_id}
📈 <b>Side:</b> {side}
{pnl_emoji} <b>Current PnL:</b> {pnl_text}

<b>Are you ABSOLUTELY SURE you want to close this position?</b>

This action cannot be undone! The position will be closed at market price.

Choose wisely:"""

            return self.send_message(message, reply_markup={
                "inline_keyboard": [
                    [{"text": "✅ YES, CLOSE NOW!", "callback_data": "close_position_execute"}],
                    [{"text": "❌ NO, KEEP IT OPEN", "callback_data": "close_position_cancel"}]
                ]
            })
            
        except Exception as e:
            logger.error(f"Error sending close confirmation: {e}")
            return False

    def notify_error(self, error_data: Dict) -> bool:
        """
        Notify about errors.

        Args:
            error_data: Error data

        Returns:
            True if successful
        """
        try:
            error_type = error_data["type"]
            error_message = error_data["message"]
            component = error_data.get("component", "Unknown")
            
            # Create message
            message = f"""❌ <b>ERROR ALERT</b>

🔧 <b>Component:</b> {component}
⚠️ <b>Type:</b> {error_type}
📝 <b>Message:</b> {error_message}

⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

🛠️ <b>Action Required:</b> Check logs and system status"""

            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error notifying error: {e}")
            return False

    def notify_position_status(self, position_data: Dict) -> bool:
        """
        Notify about current position status with refresh button.

        Args:
            position_data: Current position data

        Returns:
            True if successful
        """
        try:
            if not position_data:
                message = """📊 <b>POSITION STATUS</b>

❌ <b>No Open Position</b>

"""
                
                return self.send_message(message, reply_markup={
                    "inline_keyboard": [
                        [{"text": "🔄 Refresh Position", "callback_data": "refresh_position"}],
                        [{"text": "🏠 Main Menu", "callback_data": "get_main_menu"}]
                    ]
                })
            
            # Format position data (basic info from our database)
            side = position_data.get("side", "UNKNOWN")
            leverage = position_data.get("leverage", 0)
            entry_price = position_data.get("entry_price", 0)
            current_price = position_data.get("current_price", 0)
            pnl_percentage = position_data.get("pnl_percentage", 0)
            pnl_usd = position_data.get("pnl_usd", 0)
            trade_id = position_data.get("trade_id", "N/A")
            quantity = position_data.get("quantity", 0)
            notional_value = position_data.get("notional_value", 0)
            stop_loss_price = position_data.get("stop_loss_price", 0)
            stop_loss_active = position_data.get("stop_loss_active", False)
            trailing_callback_rate = position_data.get("trailing_callback_rate", 0)
            trailing_stop_active = position_data.get("trailing_stop_active", False)
            fees = position_data.get("fees", 0)
            funding_fee = position_data.get("funding_fee", 0)
            created_at = position_data.get("created_at", "")
            
            # Comprehensive Binance data
            symbol = position_data.get("symbol", "BTCUSDT")
            breakeven_price = position_data.get("breakeven_price", 0)
            mark_price = position_data.get("mark_price", current_price)
            liquidation_price = position_data.get("liquidation_price", 0)
            margin = position_data.get("margin", 0)
            margin_ratio = position_data.get("margin_ratio", 0)
            margin_type = position_data.get("margin_type", "CROSS")
            
            # Calculate price change since entry
            price_change = current_price - entry_price
            price_change_pct = (price_change / entry_price) * 100
            
            # Determine price change emoji
            if price_change_pct > 0:
                price_emoji = "📈"
            elif price_change_pct < 0:
                price_emoji = "📉"
            else:
                price_emoji = "➖"
            
            # Calculate actual trailing stop price
            if trailing_callback_rate > 0:
                if side == "LONG":
                    # For LONG: trailing stop moves up with price, triggers if price drops by callback rate
                    trailing_stop_price = current_price * (1 - trailing_callback_rate / 100)
                else:  # SHORT
                    # For SHORT: trailing stop moves down with price, triggers if price rises by callback rate
                    trailing_stop_price = current_price * (1 + trailing_callback_rate / 100)
                
                # Calculate distance from current price
                trailing_stop_distance = abs(trailing_stop_price - current_price) / current_price * 100
                trailing_stop_text = f"${trailing_stop_price:,.2f} ({trailing_stop_distance:.2f}% away)"
            else:
                trailing_stop_text = "Not Set"
            
            # Calculate stop loss distance from current price
            stop_loss_distance = abs(stop_loss_price - current_price) / current_price * 100 if stop_loss_price > 0 else 0
            
            # Determine position emoji
            if pnl_percentage > 0:
                pnl_emoji = "🟢"
            elif pnl_percentage < 0:
                pnl_emoji = "🔴"
            else:
                pnl_emoji = "🟡"
            
            message = f"""📊 <b>POSITION STATUS</b>

🆔 <b>Trade ID:</b> {trade_id}
🔤 <b>Symbol:</b> {symbol} Perp
📈 <b>Side:</b> {side} {leverage}x
📦 <b>Size:</b> {quantity:.6f} BTC
💰 <b>Notional:</b> ${notional_value:,.2f} USDT

💵 <b>PRICING:</b>
   📍 Entry Price: ${entry_price:,.2f}
   🎯 Break-Even: ${breakeven_price:,.2f}
   📊 Mark Price: ${mark_price:,.2f} {price_emoji} ({price_change_pct:+.2f}%)
   ⚠️ Liq. Price: ${liquidation_price:,.2f}

{pnl_emoji} <b>PNL (ROI):</b>
   {pnl_percentage:+.2f}% (${pnl_usd:+,.2f})

💼 <b>MARGIN ({margin_type}):</b>
   💰 Margin: ${margin:,.2f} USDT
   📊 Margin Ratio: {margin_ratio:.2f}%

🛡️ <b>RISK MANAGEMENT:</b>
   Stop Loss: ${stop_loss_price:,.2f} ({stop_loss_distance:.2f}% away) {'✅' if stop_loss_active else '⚠️ NOT ACTIVE'}
   Trailing Stop: {trailing_stop_text} {'✅' if trailing_stop_active else '⚠️ NOT ACTIVE'}
   Fixed Stop: 1% max loss
   Trailing Rate: {trailing_callback_rate:.1f}% callback

💸 <b>FEES & FUNDING:</b>
   Trading Fees: ${fees:.4f}
   Funding Fee: ${funding_fee:+.4f} {'📈' if funding_fee > 0 else '📉' if funding_fee < 0 else '⚪'}

⏰ <b>Opened:</b> {created_at}
🕐 <b>Updated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

"""
            
            return self.send_message(message, reply_markup={
                "inline_keyboard": [
                    [{"text": "🔄 Refresh Position", "callback_data": "refresh_position"}],
                    [{"text": "❌ Close Position", "callback_data": "close_position_confirm"}],
                    [{"text": "🏠 Main Menu", "callback_data": "get_main_menu"}]
                ]
            })
            
        except Exception as e:
            logger.error(f"Error notifying position status: {e}")
            return False

    def notify_trading_settings(self) -> bool:
        """
        Display comprehensive trading settings including leverage map and risk management.

        Returns:
            True if successful
        """
        try:
            message = """⚙️ <b>TRADING SETTINGS</b>

📊 <b>LEVERAGE MAP BY SENTIMENT SCORE:</b>

<b>SHORT POSITIONS (Score &lt; 5):</b>
   0 → 50x (Extreme Bearish)
   1 → 30x (Very Bearish)
   2 → 15x (Bearish)
   3 → 10x (Moderately Bearish)
   4 → 3x (Slightly Bearish)

<b>NEUTRAL (Score = 5):</b>
   5 → 0x (No Position)

<b>LONG POSITIONS (Score &gt; 5):</b>
   6 → 3x (Slightly Bullish)
   7 → 10x (Moderately Bullish)
   8 → 15x (Bullish)
   9 → 30x (Very Bullish)
   10 → 50x (Extreme Bullish)

🛡️ <b>RISK MANAGEMENT:</b>

<b>Fixed Stop Loss:</b>
   • Maximum: 1% loss from entry
   • Always active on all positions
   • Triggers if price moves against you

<b>Trailing Stop:</b>
   • Leverage-based callback rates:
     - 50x leverage → 0.5% callback
     - 30x leverage → 0.75% callback
     - 15x leverage → 1.0% callback
     - 10x leverage → 1.5% callback
     - 3x leverage → 2.0% callback
   • Maximum: 2% callback rate
   • Follows price in your favor
   • Locks in profits automatically

💡 <b>TRADING LOGIC:</b>
   • Only ONE position at a time
   • Uses ALL available liquidity
   • Auto-executes based on sentiment
   • Position closes via trailing stop

🔍 <b>MONITORING:</b>
   • Twitter: @realDonaldTrump
   • Poll interval: 30 seconds
   • AI Analysis: Claude Sonnet
   • Auto-trade: Enabled

"""
            
            return self.send_message(message, reply_markup={
                "inline_keyboard": [
                    [{"text": "🏠 Main Menu", "callback_data": "get_main_menu"}]
                ]
            })
            
        except Exception as e:
            logger.error(f"Error notifying trading settings: {e}")
            return False

    def notify_startup(self, account_data: Dict) -> bool:
        """
        Notify about application startup with account information.

        Args:
            account_data: Account balance and status data

        Returns:
            True if successful
        """
        try:
            balance = account_data.get("balance", 0)
            available_balance = account_data.get("available_balance", 0)
            margin_balance = account_data.get("margin_balance", 0)
            unrealized_pnl = account_data.get("unrealized_pnl", 0)
            trading_mode = account_data.get("trading_mode", "UNKNOWN")
            open_positions = account_data.get("open_positions", 0)
            total_trades = account_data.get("total_trades", 0)
            pnl_24h = account_data.get("pnl_24h", 0)
            
            # Get rate limit info if available
            twitter_rate_limit = account_data.get("twitter_rate_limit", {})
            truthsocial_rate_limit = account_data.get("truthsocial_rate_limit", {})
            
            # Determine mode emoji
            mode_emoji = "🔴" if trading_mode == "LIVE" else "🟡"
            
            # Format Unrealized PNL
            if unrealized_pnl > 0:
                upnl_emoji = "🟢"
                upnl_text = f"+${unrealized_pnl:,.2f}"
            elif unrealized_pnl < 0:
                upnl_emoji = "🔴"
                upnl_text = f"${unrealized_pnl:,.2f}"
            else:
                upnl_emoji = "⚪"
                upnl_text = "$0.00"
            
            # Format 24h PnL
            if pnl_24h > 0:
                pnl_emoji = "🟢"
                pnl_text = f"+${pnl_24h:,.2f}"
            elif pnl_24h < 0:
                pnl_emoji = "🔴"
                pnl_text = f"-${abs(pnl_24h):,.2f}"
            else:
                pnl_emoji = "🟡"
                pnl_text = "$0.00"
            
            # Format rate limit info
            rate_limit_text = ""
            has_rate_limits = (
                (twitter_rate_limit.get("remaining") and twitter_rate_limit.get("limit")) or
                (truthsocial_rate_limit.get("remaining") and truthsocial_rate_limit.get("limit"))
            )
            
            if has_rate_limits:
                rate_limit_text += "\n\n📊 <b>API RATE LIMITS</b>"
                
                if twitter_rate_limit.get("remaining") and twitter_rate_limit.get("limit"):
                    tw_remaining = twitter_rate_limit["remaining"]
                    tw_limit = twitter_rate_limit["limit"]
                    tw_pct = (int(tw_remaining) / int(tw_limit)) * 100
                    # Use ⁄ (fraction slash) instead of / to prevent phone number auto-linking
                    rate_limit_text += f"\n   🐦 Twitter: {tw_remaining}⁄{tw_limit} ({tw_pct:.0f}%)"
                
                if truthsocial_rate_limit.get("remaining") and truthsocial_rate_limit.get("limit"):
                    ts_remaining = truthsocial_rate_limit["remaining"]
                    ts_limit = truthsocial_rate_limit["limit"]
                    ts_pct = (int(ts_remaining) / int(ts_limit)) * 100
                    # Use ⁄ (fraction slash) instead of / to prevent phone number auto-linking
                    rate_limit_text += f"\n   🇺🇸 Truth Social: {ts_remaining}⁄{ts_limit} ({ts_pct:.0f}%)"
            
            message = f"""🚀 <b>TRUMP TRADER BOT STARTED</b>

✅ <b>Status:</b> Online and monitoring
{mode_emoji} <b>Mode:</b> {trading_mode}

💼 <b>ACCOUNT DETAILS (USDT)</b>
   💰 Wallet Balance: ${balance:,.8f}
   {upnl_emoji} Unrealized PNL: {upnl_text}
   📊 Margin Balance: ${margin_balance:,.8f}
   ✅ Available: ${available_balance:,.8f}

📈 <b>TRADING STATS</b>
   📊 Open Positions: {open_positions}
   📈 Total Trades: {total_trades}
   {pnl_emoji} 24h PnL: {pnl_text}

🔍 <b>Monitoring:</b> Twitter + Truth Social (30s)
🤖 <b>AI Analysis:</b> Claude 3.5 Sonnet
📱 <b>Notifications:</b> Telegram{rate_limit_text}

⏰ <b>Started:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

"""

            return self.send_message(message, reply_markup={
                "inline_keyboard": [
                    [{"text": "📊 Position Details", "callback_data": "get_position"}],
                    [{"text": "⚙️ Trading Settings", "callback_data": "get_trading_settings"}],
                    [{"text": "🔄 Refresh Data", "callback_data": "refresh_main_menu"}]
                ]
            })
            
        except Exception as e:
            logger.error(f"Error notifying startup: {e}")
            return False

    def send_test_message(self) -> bool:
        """Send a test message to verify the bot is working."""
        try:
            message = f"""🤖 <b>TRUMP TRADER BOT</b>

✅ <b>Status:</b> Online and ready
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
🔧 <b>Mode:</b> {'TESTNET' if settings.binance_testnet else 'LIVE TRADING'}

🚀 <b>System:</b> All systems operational"""

            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending test message: {e}")
            return False
