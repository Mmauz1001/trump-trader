"""Pytest configuration and fixtures for tests."""

import os
import pytest
from unittest.mock import Mock


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables before any imports."""
    # Set dummy environment variables for testing
    os.environ["TWITTER_API_KEY"] = "test_twitter_key"
    os.environ["TWITTER_API_SECRET"] = "test_twitter_secret"
    os.environ["TWITTER_BEARER_TOKEN"] = "test_twitter_token"
    os.environ["TRUMP_TWITTER_USER_ID"] = "25073877"
    
    os.environ["SCRAPECREATORS_API_KEY"] = "test_scrape_key"
    # Truth Social removed - using only Twitter RapidAPI
    
    os.environ["ANTHROPIC_API_KEY"] = "test_anthropic_key"
    
    # Use testnet keys from environment if available, otherwise use dummy values
    os.environ["BINANCE_API_KEY"] = os.getenv("BINANCE_API_KEY", "test_binance_key")
    os.environ["BINANCE_API_SECRET"] = os.getenv("BINANCE_API_SECRET", "test_binance_secret")
    os.environ["BINANCE_TESTNET"] = "true"
    os.environ["BINANCE_TESTNET_API_KEY"] = os.getenv("BINANCE_TESTNET_API_KEY", "test_testnet_key")
    os.environ["BINANCE_TESTNET_API_SECRET"] = os.getenv("BINANCE_TESTNET_API_SECRET", "test_testnet_secret")
    
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_telegram_token"
    os.environ["TELEGRAM_CHANNEL_ID"] = "test_channel_id"
    
    os.environ["DATABASE_URL"] = "postgresql://trump_trader:trump_trader_password@localhost:5432/trump_trader_test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    
    # DRY_RUN_MODE removed - using BINANCE_TESTNET instead
    os.environ["LOG_LEVEL"] = "ERROR"  # Reduce log noise in tests
    
    yield
    
    # Cleanup after all tests
    pass


@pytest.fixture
def mock_database():
    """Mock database repository for tests."""
    from unittest.mock import Mock
    db = Mock()
    db.create_post = Mock(return_value=Mock(id=1))
    db.create_sentiment = Mock(return_value=Mock(id=1))
    db.create_trade = Mock(return_value=Mock(id=1))
    db.get_open_trade = Mock(return_value=None)
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client for tests."""
    redis_client = Mock()
    redis_client.get = Mock(return_value=None)
    redis_client.set = Mock(return_value=True)
    redis_client.exists = Mock(return_value=False)
    return redis_client


@pytest.fixture
def sample_post_content():
    """Sample Trump post content for testing."""
    return "America is the greatest country in the world! Our economy is booming!"


@pytest.fixture
def sample_sentiment_response():
    """Sample Claude API sentiment response."""
    return {
        "score": 8,
        "reasoning": "The post expresses strong positive sentiment about America and the economy, indicating bullish market confidence."
    }

