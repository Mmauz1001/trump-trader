"""Application configuration management using Pydantic settings."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Twitter API
    twitter_api_key: str = Field("", description="Twitter API key")
    twitter_api_secret: str = Field("", description="Twitter API secret")
    twitter_bearer_token: str = Field("", description="Twitter Bearer token")
    trump_twitter_user_id: str = Field(
        default="25073877", description="Trump's Twitter user ID"
    )

    # Truth Social
    scrapecreators_api_key: str = Field("", description="ScrapeCreators API key")
    truthsocial_username: str = Field(
        default="realDonaldTrump", description="Trump's Truth Social username"
    )

    # Anthropic Claude
    anthropic_api_key: str = Field("", description="Anthropic Claude API key")

    # Binance
    binance_api_key: str = Field("", description="Binance API key")
    binance_api_secret: str = Field("", description="Binance API secret")
    binance_testnet: bool = Field(default=True, description="Use Binance testnet")

    # Telegram
    telegram_bot_token: str = Field("", description="Telegram bot token")
    telegram_channel_id: str = Field("", description="Telegram channel ID")

    # Database
    database_url: str = Field(
        default="postgresql://trump_trader:trump_trader_password@localhost:5432/trump_trader",
        description="PostgreSQL database URL",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    # Application
    dry_run_mode: bool = Field(
        default=False, description="Simulate trades without execution"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    max_leverage: int = Field(default=50, description="Maximum allowed leverage")
    fixed_stop_loss_percent: float = Field(
        default=1.0, description="Fixed stop-loss percentage"
    )
    max_callback_rate_percent: float = Field(
        default=2.0, description="Maximum trailing stop callback rate percentage"
    )

    @field_validator("fixed_stop_loss_percent")
    @classmethod
    def validate_stop_loss(cls, v):
        """Ensure stop-loss never exceeds 1%."""
        if v > 1.0:
            raise ValueError("Fixed stop-loss cannot exceed 1%")
        return v

    @field_validator("max_callback_rate_percent")
    @classmethod
    def validate_callback_rate(cls, v):
        """Ensure callback rate never exceeds 2%."""
        if v > 2.0:
            raise ValueError("Callback rate cannot exceed 2%")
        return v

    @field_validator("max_leverage")
    @classmethod
    def validate_leverage(cls, v):
        """Ensure leverage is within safe bounds."""
        if v > 50:
            raise ValueError("Leverage cannot exceed 50x")
        if v < 1:
            raise ValueError("Leverage must be at least 1x")
        return v


# Global settings instance
settings = Settings()

