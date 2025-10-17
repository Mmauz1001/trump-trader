"""Twitter monitor using RapidAPI Twitter241 for real-time data."""

import json
import time
import websocket
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable

import requests
from config.settings import settings
from src.database.repository import DatabaseRepository
from src.utils import hash_content, get_timestamp, setup_logger

logger = setup_logger(__name__)


class TwitterRapidAPI:
    """Twitter monitor using RapidAPI Twitter241 for real-time monitoring."""

    def __init__(self, on_new_post: Optional[Callable] = None):
        """Initialize Twitter RapidAPI monitor."""
        self.api_key = settings.rapidapi_key
        self.api_host = settings.rapidapi_host
        self.base_url = f"https://{self.api_host}"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        self.on_new_post = on_new_post
        self.db = DatabaseRepository()
        self.is_monitoring = False
        self.ws = None
        self.last_rate_limit = {"limit": None, "remaining": None, "reset": None}
        
        logger.info("Twitter RapidAPI monitor initialized")

    def _log_rate_limit(self, response: requests.Response) -> None:
        """Log RapidAPI rate limit information from response headers."""
        try:
            limit = response.headers.get('X-RateLimit-Limit', 'N/A')
            remaining = response.headers.get('X-RateLimit-Remaining', 'N/A')
            reset = response.headers.get('X-RateLimit-Reset', 'N/A')
            
            # Store for later retrieval
            self.last_rate_limit = {
                "limit": limit if limit != 'N/A' else None,
                "remaining": remaining if remaining != 'N/A' else None,
                "reset": reset if reset != 'N/A' else None
            }
            
            if remaining != 'N/A':
                logger.info(f"📊 RapidAPI Twitter Rate Limit - Remaining: {remaining}/{limit}, Resets: {reset}")
                
                # Warn if approaching limit
                if remaining != 'N/A' and limit != 'N/A':
                    remaining_pct = (int(remaining) / int(limit)) * 100
                    if remaining_pct < 10:
                        logger.warning(f"⚠️ RapidAPI Twitter rate limit low: {remaining_pct:.1f}% remaining!")
        except Exception as e:
            logger.debug(f"Could not parse rate limit headers: {e}")

    def test_connection(self) -> bool:
        """Test RapidAPI connection."""
        try:
            # Test with a simple user lookup - try different endpoint formats
            url = f"{self.base_url}/user"
            params = {"username": "realDonaldTrump"}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response text: {response.text[:200]}...")
            self._log_rate_limit(response)
            
            if response.status_code == 200:
                data = response.json()
                # Parse the nested response structure
                user_data = data.get("result", {}).get("data", {}).get("user", {}).get("result", {})
                if user_data and user_data.get("core", {}).get("screen_name"):
                    username = user_data["core"]["screen_name"]
                    logger.info(f"✅ RapidAPI Twitter connected. User: @{username}")
                    return True
                else:
                    logger.error("❌ RapidAPI Twitter: User not found")
                    return False
            else:
                logger.error(f"❌ RapidAPI Twitter connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ RapidAPI Twitter connection failed: {e}")
            return False

    def get_recent_tweets(self, max_results: int = 10) -> List[Dict]:
        """Get recent tweets from Trump's account."""
        try:
            # Use the correct working endpoint from RapidAPI documentation
            url = f"{self.base_url}/user-tweets"
            params = {
                "user": "25073877",  # Trump's user ID
                "count": max_results
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            logger.info(f"Tweets response status: {response.status_code}")
            logger.info(f"Tweets response text: {response.text[:200]}...")
            self._log_rate_limit(response)
            
            # Check for rate limit error
            if response.status_code == 429:
                logger.error(f"⚠️ RapidAPI Twitter RATE LIMIT exceeded!")
                logger.error(f"Rate limit will reset at: {self.last_rate_limit.get('reset', 'unknown')}")
                
                # Notify via Telegram if callback is available
                try:
                    from src.notifications.telegram_notifier import TelegramNotifier
                    telegram = TelegramNotifier()
                    telegram.notify_error({
                        "type": "RateLimit",
                        "message": f"Twitter API rate limit exceeded. Resets at: {self.last_rate_limit.get('reset', 'unknown')}",
                        "component": "Twitter Monitor"
                    })
                except Exception as e:
                    logger.debug(f"Could not send Telegram notification: {e}")
                
                # Return empty to avoid crashing, polling will continue
                return []
            
            if response.status_code == 200:
                data = response.json()
                # Parse the actual response structure
                tweets = []
                
                # Navigate through the nested structure
                timeline = data.get("result", {}).get("timeline", {})
                instructions = timeline.get("instructions", [])
                
                for instruction in instructions:
                    if instruction.get("type") == "TimelineAddEntries":
                        entries = instruction.get("entries", [])
                        for entry in entries:
                            # Stop if we've reached the requested limit
                            if len(tweets) >= max_results:
                                break
                                
                            content = entry.get("content", {})
                            if content.get("entryType") == "TimelineTimelineItem":
                                item_content = content.get("itemContent", {})
                                if item_content.get("itemType") == "TimelineTweet":
                                    tweet_results = item_content.get("tweet_results", {}).get("result", {})
                                    if tweet_results.get("__typename") == "Tweet":
                                        # Extract tweet data
                                        legacy = tweet_results.get("legacy", {})
                                        
                                        tweet_dict = {
                                            "id": tweet_results.get("rest_id"),
                                            "text": legacy.get("full_text", ""),
                                            "created_at": legacy.get("created_at"),
                                            "public_metrics": {
                                                "retweet_count": legacy.get("retweet_count", 0),
                                                "like_count": legacy.get("favorite_count", 0),
                                                "reply_count": legacy.get("reply_count", 0)
                                            },
                                            "platform": "TWITTER"
                                        }
                                        tweets.append(tweet_dict)
                    
                    # Stop processing instructions if we have enough tweets
                    if len(tweets) >= max_results:
                        break
                
                logger.info(f"Retrieved {len(tweets)} recent tweet(s) (requested: {max_results})")
                return tweets
            else:
                logger.error(f"Error retrieving tweets: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving recent tweets: {e}")
            return []

    def process_tweet(self, tweet_data: Dict) -> Optional[Dict]:
        """Process a single tweet and store in database."""
        try:
            # Create content hash for deduplication
            content_hash = hash_content(tweet_data["text"])
            
            # Check if tweet already exists
            if self.db.post_exists(content_hash):
                logger.debug(f"Tweet already exists: {content_hash[:8]}...")
                return None
            
            # Prepare engagement metrics
            engagement_metrics = json.dumps(tweet_data.get("public_metrics", {}))
            
            # Parse the created_at timestamp
            from datetime import datetime
            try:
                # Parse Twitter's timestamp format: "Tue Oct 14 17:20:04 +0000 2025"
                posted_at = datetime.strptime(tweet_data["created_at"], "%a %b %d %H:%M:%S %z %Y")
            except ValueError:
                # Fallback to current time if parsing fails
                posted_at = datetime.now(timezone.utc)
            
            # Store in database
            post = self.db.create_post(
                content_hash=content_hash,
                platform=tweet_data["platform"],
                content=tweet_data["text"],
                posted_at=posted_at,
                post_id=str(tweet_data["id"]),
                engagement_metrics=engagement_metrics
            )
            
            logger.info(f"✅ New tweet stored: {post.id} - {tweet_data['text'][:50]}...")
            
            # Return processed data for sentiment analysis
            return {
                "post_id": post.id,
                "platform": tweet_data["platform"],
                "content": tweet_data["text"],
                "external_id": str(tweet_data["id"]),
                "created_at": tweet_data["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Error processing tweet: {e}")
            return None

    def start_monitoring(self) -> None:
        """Start monitoring using polling (WebSocket not available in current tier)."""
        logger.info("Starting Twitter RapidAPI monitoring...")
        
        # Test connection first
        if not self.test_connection():
            logger.error("Cannot start monitoring - API connection failed")
            return
        
        # Get only the most recent tweet first (we only need the latest one)
        recent_tweets = self.get_recent_tweets(max_results=1)
        for tweet in recent_tweets:
            self.process_tweet(tweet)
        
        # Start polling monitoring (WebSocket not available in current tier)
        self.is_monitoring = True
        self._start_polling_monitoring()

    def _start_polling_monitoring(self) -> None:
        """Start polling-based monitoring for tweets."""
        def polling_worker():
            logger.info("🚀 Twitter polling monitoring started - checking latest tweet every 30 seconds")
            last_tweet_id = None
            
            while self.is_monitoring:
                try:
                    # Get only the most recent tweet (we only need to check if there's a new one)
                    tweets = self.get_recent_tweets(max_results=1)
                    
                    if tweets:
                        latest_tweet = tweets[0]
                        
                        # Process only if this is a NEW tweet (different from last one)
                        if last_tweet_id is None or latest_tweet["id"] != last_tweet_id:
                            new_tweets = [latest_tweet]
                        else:
                            new_tweets = []
                        
                        # Process only new tweets
                        for tweet in new_tweets:
                            processed = self.process_tweet(tweet)
                            if processed and self.on_new_post:
                                self.on_new_post(processed)
                        
                        # Update last tweet ID to the most recent one
                        if tweets:
                            last_tweet_id = tweets[0]["id"]
                    
                    # Wait 30 seconds before next check
                    time.sleep(30)
                    
                except Exception as e:
                    logger.error(f"Error in polling monitoring: {e}")
                    time.sleep(30)  # Wait before retrying
        
        # Start polling in a separate thread
        polling_thread = threading.Thread(target=polling_worker, name="TwitterPolling")
        polling_thread.daemon = True
        polling_thread.start()

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self.is_monitoring = False
        logger.info("Twitter monitoring stopped")

    def get_monitoring_status(self) -> Dict:
        """Get current monitoring status."""
        return {
            "monitoring": self.is_monitoring,
            "platform": "TWITTER",
            "method": "RapidAPI Polling",
            "real_time": False,
            "polling_interval": "30 seconds",
            "last_check": get_timestamp(),
            "rate_limit": self.last_rate_limit
        }
