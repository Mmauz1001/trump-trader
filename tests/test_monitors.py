"""Tests for social media monitors."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

# Try to import Twitter monitor
try:
    from src.monitors.twitter_rapidapi import TwitterRapidAPI as TwitterMonitor
    TWITTER_AVAILABLE = True
except ImportError:
    TWITTER_AVAILABLE = False
    TwitterMonitor = None

# Try to import Truth Social monitor
try:
    from src.monitors.truthsocial_rapidapi import TruthSocialRapidAPI as TruthSocialMonitor
    TRUTH_SOCIAL_AVAILABLE = True
except ImportError:
    TRUTH_SOCIAL_AVAILABLE = False
    TruthSocialMonitor = None


class TestTwitterMonitor:
    """Test Twitter monitor functionality."""

    @pytest.mark.skipif(not TWITTER_AVAILABLE, reason="Twitter monitor not available")
    def test_init(self):
        """Test Twitter monitor initialization."""
        monitor = TwitterMonitor()
        assert monitor.api_key is not None
        assert monitor.api_host is not None
        assert monitor.db is not None
        assert monitor.is_monitoring is False

    @pytest.mark.skipif(not TWITTER_AVAILABLE, reason="Twitter monitor not available")
    @patch('src.monitors.twitter_rapidapi.requests.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection test."""
        # Mock successful API response with proper structure
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"result":{"data":{"user":{"result":{"core":{"screen_name":"realDonaldTrump"}}}}}}'
        mock_response.json.return_value = {
            "result": {
                "data": {
                    "user": {
                        "result": {
                            "__typename": "User",
                            "core": {
                                "screen_name": "realDonaldTrump"
                            }
                        }
                    }
                }
            }
        }
        mock_get.return_value = mock_response
        
        monitor = TwitterMonitor()
        result = monitor.test_connection()
        
        assert result is True
        mock_get.assert_called_once()

    @pytest.mark.skipif(not TWITTER_AVAILABLE, reason="Twitter monitor not available")
    @patch('src.monitors.twitter_rapidapi.requests.get')
    def test_test_connection_failure(self, mock_get):
        """Test failed connection test."""
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        monitor = TwitterMonitor()
        result = monitor.test_connection()
        
        assert result is False

    @pytest.mark.skipif(not TWITTER_AVAILABLE, reason="Twitter monitor not available")
    @patch('src.monitors.twitter_rapidapi.requests.get')
    def test_get_recent_tweets(self, mock_get):
        """Test getting recent tweets."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"result":{"timeline":...}}'
        mock_response.json.return_value = {
            "result": {
                "timeline": {
                    "instructions": [
                        {
                            "type": "TimelineAddEntries",
                            "entries": [
                                {
                                    "content": {
                                        "entryType": "TimelineTimelineItem",
                                        "__typename": "TimelineTimelineItem",
                                        "itemContent": {
                                            "itemType": "TimelineTweet",
                                            "tweet_results": {
                                                "result": {
                                                    "__typename": "Tweet",
                                                    "rest_id": "123456789",
                                                    "legacy": {
                                                        "full_text": "Test tweet",
                                                        "created_at": "Tue Oct 15 00:00:00 +0000 2024",
                                                        "retweet_count": 10,
                                                        "favorite_count": 20,
                                                        "reply_count": 5
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        }
        mock_get.return_value = mock_response
        
        monitor = TwitterMonitor()
        tweets = monitor.get_recent_tweets(max_results=1)
        
        assert len(tweets) == 1
        assert tweets[0]["id"] == "123456789"
        assert tweets[0]["text"] == "Test tweet"
        assert tweets[0]["platform"] == "TWITTER"

    @pytest.mark.skipif(not TWITTER_AVAILABLE, reason="Twitter monitor not available")
    @patch('src.monitors.twitter_rapidapi.DatabaseRepository')
    def test_process_tweet_success(self, mock_db_class):
        """Test successful tweet processing."""
        # Mock database
        mock_db = Mock()
        mock_db.post_exists.return_value = False
        mock_post = Mock()
        mock_post.id = 1
        mock_db.create_post.return_value = mock_post
        mock_db_class.return_value = mock_db
        
        monitor = TwitterMonitor()
        monitor.db = mock_db
        
        tweet_data = {
            "id": "123456789",
            "text": "Test tweet",
            "created_at": "Tue Oct 15 00:00:00 +0000 2024",
            "public_metrics": {"like_count": 100},
            "platform": "TWITTER"
        }
        
        result = monitor.process_tweet(tweet_data)
        
        assert result is not None
        assert result["post_id"] == 1
        assert result["platform"] == "TWITTER"
        mock_db.create_post.assert_called_once()

    @pytest.mark.skipif(not TWITTER_AVAILABLE, reason="Twitter monitor not available")
    @patch('src.monitors.twitter_rapidapi.DatabaseRepository')
    def test_process_tweet_duplicate(self, mock_db_class):
        """Test processing duplicate tweet."""
        # Mock database
        mock_db = Mock()
        mock_db.post_exists.return_value = True
        mock_db_class.return_value = mock_db
        
        monitor = TwitterMonitor()
        monitor.db = mock_db
        
        tweet_data = {
            "id": "123456789",
            "text": "Test tweet",
            "created_at": "Tue Oct 15 00:00:00 +0000 2024",
            "public_metrics": {"like_count": 100},
            "platform": "TWITTER"
        }
        
        result = monitor.process_tweet(tweet_data)
        
        assert result is None
        mock_db.create_post.assert_not_called()


class TestTruthSocialMonitor:
    """Test Truth Social monitor functionality."""

    @pytest.mark.skipif(not TRUTH_SOCIAL_AVAILABLE, reason="Truth Social monitor not available")
    def test_init(self):
        """Test Truth Social monitor initialization."""
        monitor = TruthSocialMonitor()
        assert monitor.api_key is not None
        assert monitor.api_host is not None
        assert monitor.username is not None
        assert monitor.db is not None
        assert monitor.is_monitoring is False

    @pytest.mark.skipif(not TRUTH_SOCIAL_AVAILABLE, reason="Truth Social monitor not available")
    @patch('src.monitors.truthsocial_rapidapi.requests.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection test."""
        # Mock successful API response (Truth Social returns list directly)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '[{"id":"115387504970821391","content":"<p>Test post</p>"}]'
        mock_response.json.return_value = [
            {
                "id": "115387504970821391",
                "content": "<p>Test post</p>",
                "created_at": "2025-10-17T03:59:58.840000Z"
            }
        ]
        mock_get.return_value = mock_response
        
        monitor = TruthSocialMonitor()
        result = monitor.test_connection()
        
        assert result is True
        mock_get.assert_called_once()

    @pytest.mark.skipif(not TRUTH_SOCIAL_AVAILABLE, reason="Truth Social monitor not available")
    @patch('src.monitors.truthsocial_rapidapi.requests.get')
    def test_test_connection_failure(self, mock_get):
        """Test failed connection test."""
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        monitor = TruthSocialMonitor()
        result = monitor.test_connection()
        
        assert result is False

    @pytest.mark.skipif(not TRUTH_SOCIAL_AVAILABLE, reason="Truth Social monitor not available")
    @patch('src.monitors.truthsocial_rapidapi.requests.get')
    def test_test_connection_empty_list(self, mock_get):
        """Test connection with empty response list."""
        # Mock empty list response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '[]'
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        monitor = TruthSocialMonitor()
        result = monitor.test_connection()
        
        assert result is False

    @pytest.mark.skipif(not TRUTH_SOCIAL_AVAILABLE, reason="Truth Social monitor not available")
    @patch('src.monitors.truthsocial_rapidapi.requests.get')
    def test_get_recent_posts(self, mock_get):
        """Test getting recent posts from Truth Social."""
        # Mock successful API response (actual structure from Truth Social API)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '[{"id":"115387504970821391","content":"<p>Test post</p>"}]'
        mock_response.json.return_value = [
            {
                "id": "115387504970821391",
                "created_at": "2025-10-17T03:59:58.840000Z",
                "content": "<p>Test post with <strong>HTML</strong></p>",
                "reblogs_count": 2337,
                "favourites_count": 7176,
                "replies_count": 1059
            }
        ]
        mock_get.return_value = mock_response
        
        monitor = TruthSocialMonitor()
        posts = monitor.get_recent_posts(max_results=1)
        
        assert len(posts) == 1
        assert posts[0]["id"] == "115387504970821391"
        assert posts[0]["text"] == "Test post with HTML"  # HTML tags stripped
        assert posts[0]["platform"] == "TRUTH_SOCIAL"
        assert posts[0]["public_metrics"]["repost_count"] == 2337
        assert posts[0]["public_metrics"]["like_count"] == 7176

    @pytest.mark.skipif(not TRUTH_SOCIAL_AVAILABLE, reason="Truth Social monitor not available")
    @patch('src.monitors.truthsocial_rapidapi.DatabaseRepository')
    def test_process_post_success(self, mock_db_class):
        """Test successful post processing."""
        # Mock database
        mock_db = Mock()
        mock_db.post_exists.return_value = False
        mock_post = Mock()
        mock_post.id = 1
        mock_db.create_post.return_value = mock_post
        mock_db_class.return_value = mock_db
        
        monitor = TruthSocialMonitor()
        monitor.db = mock_db
        
        post_data = {
            "id": "115387504970821391",
            "text": "Test post",
            "created_at": "2025-10-17T03:59:58.840000Z",
            "public_metrics": {"like_count": 100},
            "platform": "TRUTH_SOCIAL"
        }
        
        result = monitor.process_post(post_data)
        
        assert result is not None
        assert result["post_id"] == 1
        assert result["platform"] == "TRUTH_SOCIAL"
        mock_db.create_post.assert_called_once()

    @pytest.mark.skipif(not TRUTH_SOCIAL_AVAILABLE, reason="Truth Social monitor not available")
    @patch('src.monitors.truthsocial_rapidapi.DatabaseRepository')
    def test_process_post_duplicate(self, mock_db_class):
        """Test processing duplicate post."""
        # Mock database
        mock_db = Mock()
        mock_db.post_exists.return_value = True
        mock_db_class.return_value = mock_db
        
        monitor = TruthSocialMonitor()
        monitor.db = mock_db
        
        post_data = {
            "id": "115387504970821391",
            "text": "Test post",
            "created_at": "2025-10-17T03:59:58.840000Z",
            "public_metrics": {"like_count": 100},
            "platform": "TRUTH_SOCIAL"
        }
        
        result = monitor.process_post(post_data)
        
        assert result is None
        mock_db.create_post.assert_not_called()

    @pytest.mark.skipif(not TRUTH_SOCIAL_AVAILABLE, reason="Truth Social monitor not available")
    @patch('src.monitors.truthsocial_rapidapi.requests.get')
    def test_html_stripping(self, mock_get):
        """Test that HTML tags are properly stripped from content."""
        # Mock response with complex HTML
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "123",
                "created_at": "2025-10-17T03:59:58.840000Z",
                "content": '<p>Test <a href="url">link</a> and <strong>bold</strong> text</p>',
                "reblogs_count": 0,
                "favourites_count": 0,
                "replies_count": 0
            }
        ]
        mock_get.return_value = mock_response
        
        monitor = TruthSocialMonitor()
        posts = monitor.get_recent_posts(max_results=1)
        
        assert len(posts) == 1
        assert posts[0]["text"] == "Test link and bold text"
        assert "<p>" not in posts[0]["text"]
        assert "<a" not in posts[0]["text"]
        assert "<strong>" not in posts[0]["text"]
