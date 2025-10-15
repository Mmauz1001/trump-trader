"""Tests for sentiment analysis."""

import pytest
from unittest.mock import Mock, patch
import json

from src.analysis.sentiment_analyzer import SentimentAnalyzer


class TestSentimentAnalyzer:
    """Test sentiment analyzer functionality."""

    def test_init(self):
        """Test sentiment analyzer initialization."""
        analyzer = SentimentAnalyzer()
        assert analyzer.client is not None
        assert analyzer.db is not None
        assert analyzer.model_version == "claude-3-5-sonnet-20241022"

    @patch('src.analysis.sentiment_analyzer.anthropic.Anthropic')
    def test_test_connection_success(self, mock_anthropic_class):
        """Test successful connection test."""
        # Mock client instance
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock successful response
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_client.messages.create.return_value = mock_response
        
        analyzer = SentimentAnalyzer()
        result = analyzer.test_connection()
        
        assert result is True
        mock_client.messages.create.assert_called_once()

    @patch('src.analysis.sentiment_analyzer.anthropic.Anthropic')
    def test_test_connection_failure(self, mock_anthropic_class):
        """Test failed connection test."""
        # Mock client instance
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock failed response
        mock_client.messages.create.side_effect = Exception("API Error")
        
        analyzer = SentimentAnalyzer()
        result = analyzer.test_connection()
        
        assert result is False

    @patch('src.analysis.sentiment_analyzer.anthropic.Anthropic')
    def test_analyze_sentiment_success(self, mock_anthropic_class):
        """Test successful sentiment analysis."""
        # Mock client instance
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock successful response
        mock_response = Mock()
        mock_response.content = [Mock(text='{"score": 8, "reasoning": "Very bullish sentiment"}')]
        mock_client.messages.create.return_value = mock_response
        
        analyzer = SentimentAnalyzer()
        score, reasoning = analyzer.analyze_sentiment("Test post", "TWITTER")
        
        assert score == 8
        assert reasoning == "Very bullish sentiment"
        mock_client.messages.create.assert_called_once()

    @patch('src.analysis.sentiment_analyzer.anthropic.Anthropic')
    def test_analyze_sentiment_json_parse_error(self, mock_anthropic_class):
        """Test sentiment analysis with JSON parse error."""
        # Mock client instance
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.content = [Mock(text="Invalid JSON response")]
        mock_client.messages.create.return_value = mock_response
        
        analyzer = SentimentAnalyzer()
        score, reasoning = analyzer.analyze_sentiment("Test post", "TWITTER")
        
        # Should fallback to text extraction
        assert isinstance(score, int)
        assert 0 <= score <= 10
        assert "Analysis failed" in reasoning

    @patch('src.analysis.sentiment_analyzer.anthropic.Anthropic')
    def test_analyze_sentiment_api_error(self, mock_anthropic_class):
        """Test sentiment analysis with API error."""
        # Mock client instance
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock API error
        mock_client.messages.create.side_effect = Exception("API Error")
        
        analyzer = SentimentAnalyzer()
        score, reasoning = analyzer.analyze_sentiment("Test post", "TWITTER")
        
        # Should return neutral score on error
        assert score == 5
        assert "Analysis failed due to error" in reasoning

    def test_extract_score_from_text(self):
        """Test score extraction from text."""
        analyzer = SentimentAnalyzer()
        
        # Test various formats
        assert analyzer._extract_score_from_text("Score: 8/10") == 8
        assert analyzer._extract_score_from_text("The score is 7") == 7
        assert analyzer._extract_score_from_text("8") == 8
        assert analyzer._extract_score_from_text("No score here") == 5  # Default

