"""Utility helper functions."""

import hashlib
from datetime import datetime
from typing import Any, Dict


def hash_content(content: str) -> str:
    """
    Generate a SHA-256 hash of content for deduplication.

    Args:
        content: Text content to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.utcnow()


def format_currency(amount: float, decimals: int = 2) -> str:
    """
    Format amount as currency string.

    Args:
        amount: Amount to format
        decimals: Number of decimal places

    Returns:
        Formatted currency string
    """
    return f"${amount:,.{decimals}f}"


def calculate_pnl_percentage(entry_price: float, exit_price: float, side: str) -> float:
    """
    Calculate profit/loss percentage.

    Args:
        entry_price: Entry price
        exit_price: Exit price
        side: Position side ('LONG' or 'SHORT')

    Returns:
        PnL percentage
    """
    if side == "LONG":
        return ((exit_price - entry_price) / entry_price) * 100
    elif side == "SHORT":
        return ((entry_price - exit_price) / entry_price) * 100
    else:
        raise ValueError(f"Invalid side: {side}")


def get_leverage_for_score(score: int) -> int:
    """
    Get leverage multiplier based on sentiment score.

    Args:
        score: Sentiment score (0-10)

    Returns:
        Leverage multiplier

    Raises:
        ValueError: If score is out of range
    """
    if not 0 <= score <= 10:
        raise ValueError(f"Score must be between 0 and 10, got {score}")

    leverage_map: Dict[int, int] = {
        0: 50,
        1: 30,
        2: 15,
        3: 10,
        4: 3,
        5: 0,  # Neutral - no position
        6: 3,
        7: 10,
        8: 15,
        9: 30,
        10: 50,
    }

    return leverage_map[score]


def get_callback_rate_for_leverage(leverage: int) -> float:
    """
    Get trailing stop callback rate based on leverage.
    Max callback rate is 2% regardless of leverage.

    Args:
        leverage: Leverage multiplier

    Returns:
        Callback rate as decimal (e.g., 0.5 for 0.5%)
    """
    callback_map: Dict[int, float] = {
        50: 0.5,
        30: 0.8,
        15: 1.2,
        10: 1.5,
        3: 2.0,
    }

    return callback_map.get(leverage, 2.0)


def should_open_position(score: int) -> bool:
    """
    Determine if a position should be opened based on sentiment score.
    Long: score > 5
    Short: score < 5
    Neutral: score == 5 (no position)

    Args:
        score: Sentiment score (0-10)

    Returns:
        True if position should be opened, False otherwise
    """
    return score != 5


def get_position_side(score: int) -> str:
    """
    Get position side based on sentiment score.

    Args:
        score: Sentiment score (0-10)

    Returns:
        'LONG' if score > 5, 'SHORT' if score < 5

    Raises:
        ValueError: If score is 5 (neutral)
    """
    if score > 5:
        return "LONG"
    elif score < 5:
        return "SHORT"
    else:
        raise ValueError("Cannot determine position side for neutral score (5)")

