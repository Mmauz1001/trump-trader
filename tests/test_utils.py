"""Atomic tests for utility functions."""

import pytest

from src.utils.helpers import (
    calculate_pnl_percentage,
    format_currency,
    get_callback_rate_for_leverage,
    get_leverage_for_score,
    get_position_side,
    hash_content,
    should_open_position,
)


class TestHashContent:
    """Test content hashing functionality."""

    def test_hash_content_returns_consistent_hash(self):
        """Hash should be consistent for same input."""
        content = "Test content"
        hash1 = hash_content(content)
        hash2 = hash_content(content)
        assert hash1 == hash2

    def test_hash_content_different_for_different_input(self):
        """Different content should produce different hashes."""
        hash1 = hash_content("content1")
        hash2 = hash_content("content2")
        assert hash1 != hash2

    def test_hash_content_is_64_chars(self):
        """SHA-256 hash should be 64 hexadecimal characters."""
        result = hash_content("test")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestFormatCurrency:
    """Test currency formatting."""

    def test_format_currency_default_decimals(self):
        """Format currency with default 2 decimals."""
        assert format_currency(1234.567) == "$1,234.57"

    def test_format_currency_custom_decimals(self):
        """Format currency with custom decimal places."""
        assert format_currency(1234.567, decimals=4) == "$1,234.5670"

    def test_format_currency_zero(self):
        """Format zero amount."""
        assert format_currency(0) == "$0.00"

    def test_format_currency_negative(self):
        """Format negative amount."""
        assert format_currency(-1234.56) == "$-1,234.56"


class TestCalculatePnlPercentage:
    """Test PnL percentage calculation."""

    def test_long_position_profit(self):
        """Calculate profit for long position."""
        pnl = calculate_pnl_percentage(100, 110, "LONG")
        assert pnl == pytest.approx(10.0)

    def test_long_position_loss(self):
        """Calculate loss for long position."""
        pnl = calculate_pnl_percentage(100, 95, "LONG")
        assert pnl == pytest.approx(-5.0)

    def test_short_position_profit(self):
        """Calculate profit for short position."""
        pnl = calculate_pnl_percentage(100, 90, "SHORT")
        assert pnl == pytest.approx(10.0)

    def test_short_position_loss(self):
        """Calculate loss for short position."""
        pnl = calculate_pnl_percentage(100, 105, "SHORT")
        assert pnl == pytest.approx(-5.0)

    def test_invalid_side_raises_error(self):
        """Invalid position side should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid side"):
            calculate_pnl_percentage(100, 110, "INVALID")


class TestGetLeverageForScore:
    """Test leverage mapping based on sentiment score."""

    @pytest.mark.parametrize("score,expected_leverage", [
        (0, 50),
        (1, 30),
        (2, 15),
        (3, 10),
        (4, 3),
        (5, 0),
        (6, 3),
        (7, 10),
        (8, 15),
        (9, 30),
        (10, 50),
    ])
    def test_leverage_for_all_scores(self, score, expected_leverage):
        """Test leverage mapping for all valid scores."""
        assert get_leverage_for_score(score) == expected_leverage

    def test_score_below_range_raises_error(self):
        """Score below 0 should raise ValueError."""
        with pytest.raises(ValueError, match="Score must be between 0 and 10"):
            get_leverage_for_score(-1)

    def test_score_above_range_raises_error(self):
        """Score above 10 should raise ValueError."""
        with pytest.raises(ValueError, match="Score must be between 0 and 10"):
            get_leverage_for_score(11)


class TestGetCallbackRateForLeverage:
    """Test callback rate mapping based on leverage."""

    @pytest.mark.parametrize("leverage,expected_rate", [
        (50, 0.5),
        (30, 0.8),
        (15, 1.2),
        (10, 1.5),
        (3, 2.0),
    ])
    def test_callback_rate_for_standard_leverages(self, leverage, expected_rate):
        """Test callback rates for standard leverage values."""
        assert get_callback_rate_for_leverage(leverage) == expected_rate

    def test_callback_rate_for_unknown_leverage_returns_max(self):
        """Unknown leverage should return maximum callback rate."""
        assert get_callback_rate_for_leverage(5) == 2.0
        assert get_callback_rate_for_leverage(100) == 2.0

    def test_callback_rate_never_exceeds_max(self):
        """Callback rate should never exceed 2%."""
        for leverage in [3, 10, 15, 30, 50, 7, 100]:
            assert get_callback_rate_for_leverage(leverage) <= 2.0


class TestShouldOpenPosition:
    """Test position opening logic based on sentiment score."""

    @pytest.mark.parametrize("score,expected", [
        (0, True),   # Extreme short
        (1, True),
        (2, True),
        (3, True),
        (4, True),
        (5, False),  # Neutral - no position
        (6, True),
        (7, True),
        (8, True),
        (9, True),
        (10, True),  # Extreme long
    ])
    def test_should_open_position_for_all_scores(self, score, expected):
        """Test position opening decision for all scores."""
        assert should_open_position(score) == expected


class TestGetPositionSide:
    """Test position side determination based on sentiment score."""

    @pytest.mark.parametrize("score,expected_side", [
        (0, "SHORT"),
        (1, "SHORT"),
        (2, "SHORT"),
        (3, "SHORT"),
        (4, "SHORT"),
        (6, "LONG"),
        (7, "LONG"),
        (8, "LONG"),
        (9, "LONG"),
        (10, "LONG"),
    ])
    def test_get_position_side_for_valid_scores(self, score, expected_side):
        """Test position side for all non-neutral scores."""
        assert get_position_side(score) == expected_side

    def test_neutral_score_raises_error(self):
        """Neutral score (5) should raise ValueError."""
        with pytest.raises(ValueError, match="Cannot determine position side for neutral score"):
            get_position_side(5)

