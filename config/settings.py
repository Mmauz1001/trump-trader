"""Application configuration management using Pydantic settings."""

import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str:
    """
    Determine which env file to load based on APP_ENV variable.
    
    Standard naming convention: .env.<environment>
    
    Priority:
    1. APP_ENV=production -> .env.production
    2. APP_ENV=local -> .env.local
    3. Default -> .env (for backward compatibility)
    """
    app_env = os.getenv("APP_ENV", "default")
    
    if app_env == "production":
        return ".env.production"
    elif app_env == "local":
        return ".env.local"
    else:
        return ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Social Media Monitoring (via RapidAPI)
    # Twitter
    trump_twitter_user_id: str = Field(
        default="25073877", description="Trump's Twitter user ID"
    )
    # Truth Social
    trump_truth_social_username: str = Field(
        default="realDonaldTrump", description="Trump's Truth Social username"
    )
    truth_social_rapidapi_host: str = Field(
        default="truth-social-api.p.rapidapi.com", 
        description="RapidAPI host for Truth Social"
    )

    # Anthropic Claude
    anthropic_api_key: str = Field("", description="Anthropic Claude API key")

    # Binance
    binance_api_key: str = Field("", description="Binance API key (live)")
    binance_api_secret: str = Field("", description="Binance API secret (live)")
    binance_testnet: bool = Field(default=True, description="Use Binance testnet")
    binance_testnet_api_key: str = Field("", description="Binance testnet API key")
    binance_testnet_api_secret: str = Field("", description="Binance testnet API secret")
    
    @property
    def active_binance_api_key(self) -> str:
        """Get the active Binance API key based on testnet setting."""
        if self.binance_testnet:
            return self.binance_testnet_api_key or self.binance_api_key
        return self.binance_api_key
    
    @property
    def active_binance_api_secret(self) -> str:
        """Get the active Binance API secret based on testnet setting."""
        if self.binance_testnet:
            return self.binance_testnet_api_secret or self.binance_api_secret
        return self.binance_api_secret

    # Telegram
    telegram_bot_token: str = Field("", description="Telegram bot token")
    telegram_channel_id: str = Field("", description="Telegram channel ID")
    
    # RapidAPI
    rapidapi_key: str = Field("", description="RapidAPI key for Twitter241")
    rapidapi_host: str = Field("twitter241.p.rapidapi.com", description="RapidAPI host for Twitter241")

    # Database
    database_url: str = Field(
        default="postgresql://trump_trader:trump_trader_password@localhost:5432/trump_trader",
        description="PostgreSQL database URL",
    )

    # Application
    log_level: str = Field(default="INFO", description="Logging level")


# Global settings instance
settings = Settings()

