# Trump Twitter Trading Bot

Automated cryptocurrency trading system that monitors Donald Trump's Twitter posts via RapidAPI, analyzes sentiment using Claude AI, and executes leveraged BTC futures trades on Binance with dynamic risk management.

## 🎯 System Overview

This bot:
1. **Monitors** @realDonaldTrump on Twitter (via RapidAPI Twitter241)
2. **Analyzes** post sentiment using Claude AI (0-10 scale)
3. **Executes** BTC futures trades on Binance with dynamic leverage
4. **Manages** risk with dual stop-loss strategy
5. **Notifies** via Telegram with real-time updates

## 📊 System Architecture

```mermaid
graph TB
    subgraph "Data Source"
        A[Twitter RapidAPI<br/>@realDonaldTrump]
    end
    
    subgraph "Core System"
        C[Twitter Monitor<br/>Polling every 30s]
        D[Sentiment Analyzer<br/>Claude Sonnet API]
        E[Trading Engine<br/>Binance Futures]
        F[Risk Manager<br/>Dual Stop-Loss]
        G[Telegram Bot<br/>Interactive Notifications]
    end
    
    subgraph "Infrastructure"
        H[(PostgreSQL<br/>Trade History)]
    end
    
    A --> |Latest Tweet| C
    C --> |New Post| D
    D --> |Score 0-10| E
    E --> F
    F --> |Execute Trade| E
    E --> H
    C --> H
    D --> H
    E --> G
    
    style D fill:#f9f,stroke:#333
    style E fill:#ff9,stroke:#333
    style F fill:#f99,stroke:#333
```

## 🎮 Trading Logic

### Sentiment Score Mapping

```mermaid
graph LR
    A[Score < 5] -->|SHORT| B[Open Short Position]
    C[Score = 5] -->|NEUTRAL| D[No Position]
    E[Score > 5] -->|LONG| F[Open Long Position]
    
    style B fill:#f99
    style D fill:#ff9
    style F fill:#9f9
```

### Leverage & Risk Map

| Score | Sentiment | Leverage | Position | Trailing Stop |
|-------|-----------|----------|----------|---------------|
| 0 | Extreme Bearish | 50x | SHORT | 0.5% |
| 1 | Very Bearish | 30x | SHORT | 0.75% |
| 2 | Bearish | 15x | SHORT | 1.0% |
| 3 | Moderately Bearish | 10x | SHORT | 1.5% |
| 4 | Slightly Bearish | 3x | SHORT | 2.0% |
| **5** | **Neutral** | **0x** | **NO POSITION** | **N/A** |
| 6 | Slightly Bullish | 3x | LONG | 2.0% |
| 7 | Moderately Bullish | 10x | LONG | 1.5% |
| 8 | Bullish | 15x | LONG | 1.0% |
| 9 | Very Bullish | 30x | LONG | 0.75% |
| 10 | Extreme Bullish | 50x | LONG | 0.5% |

### Risk Management

**Position Rules:**
- ✅ Only **ONE** position open at a time
- ✅ Uses **100%** of available balance per trade
- ✅ New signals are **skipped** if position is open
- ✅ Positions close via **trailing stop only**

**Stop-Loss Strategy:**
- 🛡️ **Fixed Stop-Loss:** Maximum 1% account loss
- 🔄 **Trailing Stop:** Dynamic callback (0.5%-2%) based on leverage
- 🎯 Higher leverage = Tighter trailing stop

## 🏗️ Project Structure

```
trump_trader/
├── config/
│   └── settings.py              # Pydantic settings
├── src/
│   ├── monitors/
│   │   └── twitter_rapidapi.py  # RapidAPI Twitter monitoring
│   ├── analysis/
│   │   └── sentiment_analyzer.py # Claude API sentiment scoring
│   ├── trading/
│   │   ├── binance_client.py    # Binance Futures wrapper
│   │   └── position_manager.py  # Position lifecycle
│   ├── notifications/
│   │   └── telegram_notifier.py # Telegram updates
│   ├── database/
│   │   ├── models.py            # SQLAlchemy models
│   │   └── repository.py        # Database operations
│   ├── bot/
│   │   └── trading_bot.py       # Main orchestrator
│   └── utils/
│       ├── logger.py            # Logging setup
│       └── helpers.py           # Utility functions
├── tests/                       # Pytest test suite
├── telegram_bot_handler.py      # Telegram command handler
├── main.py                      # CLI entry point
├── docker-compose.yml           # PostgreSQL
└── requirements.txt
```

## 🚀 Setup Instructions

### 1. Prerequisites

- Python 3.13+
- Docker & Docker Compose
- API Keys (see below)

### 2. Clone and Install

```bash
cd /Users/siempi/Documents/repo/trump_trader

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start Infrastructure

```bash
# Start PostgreSQL
docker-compose up -d

# Verify service is running
docker-compose ps
```

### 4. Configure Environment

Create `.env` file with the following:

```bash
# Twitter (via RapidAPI Twitter241)
RAPIDAPI_KEY=your_rapidapi_key
RAPIDAPI_HOST=twitter241.p.rapidapi.com
TRUMP_TWITTER_USER_ID=25073877

# Anthropic Claude
ANTHROPIC_API_KEY=your_claude_key

# Binance (Live or Testnet)
BINANCE_API_KEY=your_binance_key
BINANCE_API_SECRET=your_binance_secret
BINANCE_TESTNET=false  # Set to true for testnet

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=your_channel_id

# Database
DATABASE_URL=postgresql://trump_trader:trump_trader_password@localhost:5432/trump_trader
```

### 5. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

### 6. Start Application

```bash
# Start main bot
python main.py start

# In another terminal, start Telegram handler
python telegram_bot_handler.py
```

## 📡 API Setup

### 1. RapidAPI (Twitter)
- Go to: https://rapidapi.com/davethebeast/api/twitter241
- Subscribe to a plan (Basic: $25/month for 100K requests)
- Copy your API key
- Add to `.env`: `RAPIDAPI_KEY`

### 2. Anthropic Claude
- Go to: https://console.anthropic.com/
- Create API key
- Model: Claude 3.5 Sonnet
- Add to `.env`: `ANTHROPIC_API_KEY`

### 3. Binance
- **Testnet:** https://testnet.binancefuture.com/
- **Live:** https://www.binance.com/
- Enable Futures trading
- Generate API keys
- Add to `.env`: `BINANCE_API_KEY`, `BINANCE_API_SECRET`

### 4. Telegram Bot
- Message @BotFather on Telegram
- Create bot with `/newbot`
- Get bot token
- Create channel and add bot as admin
- Get channel ID
- Add to `.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`

## 💬 Telegram Commands

The bot provides an interactive menu with buttons:

- 📊 **Position Details** - View current position with live data
- ⚙️ **Trading Settings** - View leverage map & risk settings
- 🔄 **Refresh Data** - Refresh main menu with latest data
- ❌ **Close Position** - Manually close position (with confirmation)

## 🧪 Testing

```bash
# Test API connections
python main.py test

# Run all tests
pytest

# Run specific test file
pytest tests/test_trading.py

# With verbose output
pytest -v

# With coverage report
pytest --cov=src --cov-report=term-missing
```

## 📊 Monitoring

- **Application Logs:** Console output (configurable level)
- **Database:** Full trade history in `trades` table
- **Telegram:** Real-time notifications with interactive buttons
- **Position Status:** Live PnL, break-even, liquidation price, margin ratio

## 🔒 Safety Features

1. ✅ **Testnet Support** - Practice with Binance testnet
2. ✅ **Fixed Stop-Loss** - Never exceeds 1% account loss
3. ✅ **Trailing Stop** - Locks in profits automatically
4. ✅ **Single Position** - Only 1 open position at a time
5. ✅ **Skip Logic** - New signals skipped if position is open
6. ✅ **Leverage Limits** - Maximum 50x, validated in settings

## 💰 Cost Estimates (Monthly)

| Service | Cost |
|---------|------|
| RapidAPI Twitter241 | $25 |
| Anthropic Claude API | $50-100 |
| AWS (Tokyo Region) | $50-100 |
| **Total** | **$125-225/month** |

## 🛠️ CLI Commands

```bash
# Test all API connections
python main.py test

# Start the bot
python main.py start

# Show bot status
python main.py status

# Close all positions
python main.py close-positions

# Send position status to Telegram
python main.py position-status

# Stop the bot
python main.py stop
```

## 🚨 Emergency Procedures

### Stop Trading Immediately
```bash
# Kill all processes
pkill -f "python main.py start"
pkill -f "telegram_bot_handler.py"

# Close positions manually via Binance web interface
```

### Database Backup
```bash
docker exec trump_trader_postgres pg_dump -U trump_trader trump_trader > backup_$(date +%Y%m%d).sql
```

## 📈 Production Deployment

For AWS deployment (Tokyo region):
1. Use ECS/Fargate for container orchestration
2. RDS PostgreSQL for database
3. CloudWatch for logging
4. Secrets Manager for API keys
5. Application Load Balancer for high availability

## ⚠️ Risk Warning

**Trading with leverage carries substantial risk of loss. This system can result in complete loss of capital. Use at your own risk. Never invest more than you can afford to lose.**

## 📝 License

Private - Not for distribution

---

**Version:** 1.0.0  
**Last Updated:** October 2025  
**Status:** Production Ready 🚀
