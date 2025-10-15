#!/bin/bash

# Trump Trader - AWS EC2 Deployment Script
# This script deploys the application to an EC2 instance

set -e  # Exit on error

echo "========================================"
echo "Trump Trader - AWS Deployment Script"
echo "========================================"
echo ""

# Configuration
APP_DIR="/home/ubuntu/trump_trader"
VENV_DIR="$APP_DIR/venv"
LOGS_DIR="$APP_DIR/logs"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Step 1: Install system dependencies
print_step "Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3-venv python3-pip postgresql-client git > /dev/null 2>&1
print_success "System dependencies installed"

# Step 2: Create application directory
print_step "Creating application directory..."
mkdir -p $APP_DIR
mkdir -p $LOGS_DIR
print_success "Directories created"

# Step 3: Clone or update repository
print_step "Updating application code..."
if [ -d "$APP_DIR/.git" ]; then
    cd $APP_DIR
    git pull origin main
else
    git clone https://github.com/Mmmauz1001/trump_trader.git $APP_DIR
    cd $APP_DIR
fi
print_success "Code updated"

# Step 4: Create virtual environment
print_step "Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi
source $VENV_DIR/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Virtual environment ready"

# Step 5: Set up environment variables
print_step "Configuring environment variables..."
if [ ! -f "$APP_DIR/.env" ]; then
    print_error ".env file not found!"
    echo "Please create .env file with your configuration"
    echo "You can use .env.example as a template"
    exit 1
fi
print_success "Environment configured"

# Step 6: Test database connection
print_step "Testing database connection..."
python3 << 'PYTHON'
from config.settings import settings
from src.database.repository import DatabaseRepository

try:
    db = DatabaseRepository()
    print("Database connection successful!")
except Exception as e:
    print(f"Database connection failed: {e}")
    exit(1)
PYTHON
print_success "Database connection verified"

# Step 7: Install systemd services
print_step "Installing systemd services..."
sudo cp $APP_DIR/deploy/trump-trader.service /etc/systemd/system/
sudo cp $APP_DIR/deploy/trump-trader-telegram.service /etc/systemd/system/
sudo systemctl daemon-reload
print_success "Services installed"

# Step 8: Enable and start services
print_step "Starting services..."
sudo systemctl enable trump-trader.service
sudo systemctl enable trump-trader-telegram.service
sudo systemctl restart trump-trader.service
sudo systemctl restart trump-trader-telegram.service
print_success "Services started"

# Step 9: Check service status
echo ""
echo "========================================"
echo "Service Status:"
echo "========================================"
sudo systemctl status trump-trader.service --no-pager -l
echo ""
sudo systemctl status trump-trader-telegram.service --no-pager -l

echo ""
print_success "Deployment complete!"
echo ""
echo "Useful commands:"
echo "  View main bot logs:      sudo journalctl -u trump-trader.service -f"
echo "  View telegram logs:      sudo journalctl -u trump-trader-telegram.service -f"
echo "  Restart main bot:        sudo systemctl restart trump-trader.service"
echo "  Restart telegram:        sudo systemctl restart trump-trader-telegram.service"
echo "  Check status:            sudo systemctl status trump-trader.service"
echo ""

