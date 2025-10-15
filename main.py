#!/usr/bin/env python3
"""Main entry point for the Trump Trading Bot."""

import argparse
import sys
from typing import Optional

from src.bot.trading_bot import TradingBot
from src.utils import setup_logger

logger = setup_logger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Trump Trading Bot")
    parser.add_argument(
        "command",
        choices=["test", "start", "stop", "status", "close-positions", "position-status"],
        help="Command to execute"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize bot
    bot = TradingBot()
    
    try:
        if args.command == "test":
            test_connections(bot)
        elif args.command == "start":
            start_bot(bot)
        elif args.command == "stop":
            stop_bot(bot)
        elif args.command == "status":
            show_status(bot)
        elif args.command == "close-positions":
            close_positions(bot)
        elif args.command == "position-status":
            send_position_status(bot)
        else:
            logger.error(f"Unknown command: {args.command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def test_connections(bot: TradingBot) -> None:
    """Test all API connections."""
    logger.info("Testing all API connections...")
    
    results = bot.test_all_connections()
    
    # Print results
    print("\n" + "="*50)
    print("CONNECTION TEST RESULTS")
    print("="*50)
    
    all_connected = True
    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        status_text = "Connected" if status else "Failed"
        print(f"{status_icon} {service.upper():12} {status_text}")
        
        if not status:
            all_connected = False
    
    print("="*50)
    
    if all_connected:
        print("🎉 All connections successful!")
        sys.exit(0)
    else:
        print("❌ Some connections failed. Check your API keys and configuration.")
        sys.exit(1)


def start_bot(bot: TradingBot) -> None:
    """Start the trading bot."""
    logger.info("Starting Trump Trading Bot...")
    
    # Test connections first - ONLY RapidAPI
    results = bot.test_all_connections()
    
    # Check if Twitter monitoring and sentiment analysis are available
    twitter_ok = results.get("twitter", False)
    claude_ok = results.get("claude", False)
    
    if not twitter_ok:
        logger.error("Twitter RapidAPI not available - REQUIRED")
        sys.exit(1)
    
    if not claude_ok:
        logger.error("Claude API not available - REQUIRED")
        sys.exit(1)
    
    logger.info("✅ All required services available - ONLY Twitter RapidAPI")
    
    # Start monitoring
    bot.start_monitoring()
    
    try:
        # Keep running
        bot.run_forever()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot.stop_monitoring()
    except Exception as e:
        logger.error(f"Bot error: {e}")
        bot.stop_monitoring()
        sys.exit(1)


def stop_bot(bot: TradingBot) -> None:
    """Stop the trading bot."""
    logger.info("Stopping Trump Trading Bot...")
    bot.stop_monitoring()
    logger.info("Bot stopped")


def show_status(bot: TradingBot) -> None:
    """Show bot status."""
    logger.info("Getting bot status...")
    
    status = bot.get_status()
    
    # Print status
    print("\n" + "="*50)
    print("TRUMP TRADING BOT STATUS")
    print("="*50)
    
    print(f"🤖 Bot Running: {'Yes' if status.get('bot_running') else 'No'}")
    
    # Monitoring status
    monitoring = status.get('monitoring', {})
    print(f"\n📱 MONITORING:")
    for platform, platform_status in monitoring.items():
        running = platform_status.get('is_running', False)
        status_icon = "🟢" if running else "🔴"
        print(f"  {status_icon} {platform.upper()}: {'Active' if running else 'Inactive'}")
    
    # Trading status
    trading = status.get('trading', {})
    print(f"\n💰 TRADING:")
    print(f"  Mode: {'DRY RUN' if trading.get('dry_run_mode') else 'LIVE'}")
    
    open_trade = trading.get('open_trade')
    if open_trade:
        print(f"  Position: {open_trade['side']} {open_trade['leverage']}x @ ${open_trade['entry_price']:.2f}")
    else:
        print("  Position: None")
    
    # Sentiment summary
    sentiment = status.get('sentiment_summary', {})
    if sentiment and not sentiment.get('error'):
        print(f"\n📊 SENTIMENT (24h):")
        print(f"  Posts: {sentiment.get('total_posts', 0)}")
        print(f"  Average Score: {sentiment.get('average_score', 0)}/10")
        print(f"  Bullish: {sentiment.get('bullish_posts', 0)}")
        print(f"  Bearish: {sentiment.get('bearish_posts', 0)}")
        print(f"  Neutral: {sentiment.get('neutral_posts', 0)}")
    
    print("="*50)


def close_positions(bot: TradingBot) -> None:
    """Close all open positions."""
    logger.info("Closing all open positions...")
    
    success, error_msg = bot.close_all_positions()
    
    if success:
        print("✅ All positions closed successfully")
        sys.exit(0)
    else:
        print(f"❌ Failed to close positions: {error_msg}")
        sys.exit(1)


def send_position_status(bot: TradingBot) -> None:
    """Send current position status to Telegram."""
    logger.info("Sending position status to Telegram...")
    bot._send_position_status()
    logger.info("Position status sent successfully.")


if __name__ == "__main__":
    main()