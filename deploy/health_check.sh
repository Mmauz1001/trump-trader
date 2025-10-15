#!/bin/bash
# Health check script to verify deployment
# Usage: bash health_check.sh

set -e

echo "🏥 Running Health Check..."
echo "=================================================="

# Check if services are running
echo "1️⃣ Checking services status..."
if ! systemctl is-active --quiet trump-trader.service; then
    echo "❌ Main bot service is not running"
    exit 1
fi

if ! systemctl is-active --quiet trump-trader-telegram.service; then
    echo "❌ Telegram handler service is not running"
    exit 1
fi
echo "✅ Both services are running"

# Check for duplicate processes
echo ""
echo "2️⃣ Checking for duplicate processes..."
MAIN_PROCS=$(ps aux | grep "main.py" | grep python | grep -v grep | wc -l)
TELEGRAM_PROCS=$(ps aux | grep "telegram_bot_handler.py" | grep python | grep -v grep | wc -l)

if [ "$MAIN_PROCS" -ne 1 ]; then
    echo "❌ Found $MAIN_PROCS main.py processes (expected 1)"
    exit 1
fi

if [ "$TELEGRAM_PROCS" -ne 1 ]; then
    echo "❌ Found $TELEGRAM_PROCS telegram_bot_handler processes (expected 1)"
    exit 1
fi
echo "✅ No duplicate processes"

# Check logs for errors
echo ""
echo "3️⃣ Checking recent logs for errors..."
RECENT_ERRORS=$(sudo journalctl -u trump-trader.service -u trump-trader-telegram.service --since '5 minutes ago' | grep -i error | wc -l)
if [ "$RECENT_ERRORS" -gt 0 ]; then
    echo "⚠️  Found $RECENT_ERRORS error(s) in recent logs"
    sudo journalctl -u trump-trader.service -u trump-trader-telegram.service --since '5 minutes ago' | grep -i error | head -10
else
    echo "✅ No errors in recent logs"
fi

# Check if bot is monitoring
echo ""
echo "4️⃣ Checking if bot is actively monitoring..."
if ! grep -q "Twitter monitoring started" /home/ubuntu/trump_trader/logs/trump_trader.log 2>/dev/null; then
    echo "⚠️  Warning: Twitter monitoring may not be started"
else
    echo "✅ Twitter monitoring is active"
fi

# Check API connections
echo ""
echo "5️⃣ Verifying API connections..."
TWITTER_OK=$(grep -c "Twitter RapidAPI monitor initialized" /home/ubuntu/trump_trader/logs/trump_trader.log 2>/dev/null || echo "0")
CLAUDE_OK=$(grep -c "Sentiment analyzer initialized" /home/ubuntu/trump_trader/logs/trump_trader.log 2>/dev/null || echo "0")
BINANCE_OK=$(grep -c "Binance client initialized" /home/ubuntu/trump_trader/logs/trump_trader.log 2>/dev/null || echo "0")
TELEGRAM_OK=$(grep -c "Telegram notifier initialized" /home/ubuntu/trump_trader/logs/trump_trader.log 2>/dev/null || echo "0")

if [ "$TWITTER_OK" -gt 0 ] && [ "$CLAUDE_OK" -gt 0 ] && [ "$BINANCE_OK" -gt 0 ] && [ "$TELEGRAM_OK" -gt 0 ]; then
    echo "✅ All APIs initialized"
else
    echo "⚠️  Some APIs may not be initialized"
    echo "   Twitter: $TWITTER_OK | Claude: $CLAUDE_OK | Binance: $BINANCE_OK | Telegram: $TELEGRAM_OK"
fi

echo ""
echo "=================================================="
echo "✅ Health check passed!"
echo "=================================================="
echo ""
echo "📊 Current Status:"
sudo systemctl status trump-trader.service --no-pager -l | head -10
echo ""
echo "Process PIDs:"
ps aux | grep -E '(main.py|telegram_bot_handler.py)' | grep python | grep -v grep
echo ""

