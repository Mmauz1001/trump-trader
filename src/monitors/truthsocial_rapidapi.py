"""Truth Social monitor using RapidAPI for real-time data."""

import json
import re
import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable
from urllib.parse import quote

import requests
from config.settings import settings
from src.database.repository import DatabaseRepository
from src.utils import hash_content, get_timestamp, setup_logger

logger = setup_logger(__name__)


class TruthSocialRapidAPI:
    """Truth Social monitor using RapidAPI for real-time monitoring."""

    def __init__(self, on_new_post: Optional[Callable] = None):
        """Initialize Truth Social RapidAPI monitor."""
        self.api_key = settings.rapidapi_key  # Using same RapidAPI key
        self.api_host = settings.truth_social_rapidapi_host
        self.base_url = f"https://{self.api_host}"
        self.username = settings.trump_truth_social_username
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        self.on_new_post = on_new_post
        self.db = DatabaseRepository()
        self.is_monitoring = False
        
        logger.info("Truth Social RapidAPI monitor initialized")

    def test_connection(self) -> bool:
        """Test RapidAPI connection."""
        try:
            # Test with a simple user feed lookup
            url = f"{self.base_url}/users/{self.username}/feed"
            params = {
                "continue_from_id": "{}",
                "limit": 1
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=20)
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response text: {response.text[:200]}...")
            
            if response.status_code == 200:
                data = response.json()
                # The API returns a list directly
                if isinstance(data, list) and len(data) > 0:
                    logger.info(f"✅ RapidAPI Truth Social connected. User: @{self.username}")
                    return True
                else:
                    logger.error(f"❌ RapidAPI Truth Social: Unexpected response structure (type: {type(data)})")
                    return False
            else:
                logger.error(f"❌ RapidAPI Truth Social connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ RapidAPI Truth Social connection failed: {e}")
            return False

    def get_recent_posts(self, max_results: int = 10) -> List[Dict]:
        """Get recent posts from Trump's Truth Social account."""
        try:
            # Use the feed endpoint
            url = f"{self.base_url}/users/{self.username}/feed"
            params = {
                "continue_from_id": "{}",
                "limit": max_results
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=20)
            
            logger.info(f"Posts response status: {response.status_code}")
            logger.info(f"Posts response text: {response.text[:200]}...")
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                # The API returns a list directly
                if isinstance(data, list):
                    feed_items = data[:max_results]
                else:
                    # Fallback if response structure changes
                    feed_items = data.get("feed", []) or data.get("statuses", [])
                
                for item in feed_items:
                    # Extract plain text from HTML content
                    content = item.get("content", "")
                    # Simple HTML tag removal (for better text processing)
                    text = re.sub(r'<[^>]+>', '', content)
                    
                    # Extract post data based on actual API response structure
                    post_dict = {
                        "id": item.get("id"),
                        "text": text.strip(),
                        "created_at": item.get("created_at"),
                        "public_metrics": {
                            "repost_count": item.get("reblogs_count", 0),
                            "like_count": item.get("favourites_count", 0),
                            "reply_count": item.get("replies_count", 0)
                        },
                        "platform": "TRUTH_SOCIAL"
                    }
                    
                    # Only add if we have valid content
                    if post_dict["text"] and post_dict["id"]:
                        posts.append(post_dict)
                
                logger.info(f"Retrieved {len(posts)} recent post(s) (requested: {max_results})")
                return posts
            else:
                logger.error(f"Error retrieving posts: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving recent posts: {e}")
            return []

    def process_post(self, post_data: Dict) -> Optional[Dict]:
        """Process a single post and store in database."""
        try:
            # Create content hash for deduplication
            content_hash = hash_content(post_data["text"])
            
            # Check if post already exists
            if self.db.post_exists(content_hash):
                logger.debug(f"Post already exists: {content_hash[:8]}...")
                return None
            
            # Prepare engagement metrics
            engagement_metrics = json.dumps(post_data.get("public_metrics", {}))
            
            # Parse the created_at timestamp
            try:
                # Try ISO format first
                if "T" in post_data["created_at"]:
                    posted_at = datetime.fromisoformat(post_data["created_at"].replace("Z", "+00:00"))
                else:
                    # Try other common formats
                    posted_at = datetime.strptime(post_data["created_at"], "%Y-%m-%d %H:%M:%S")
                    posted_at = posted_at.replace(tzinfo=timezone.utc)
            except (ValueError, AttributeError):
                # Fallback to current time if parsing fails
                posted_at = datetime.now(timezone.utc)
            
            # Store in database
            post = self.db.create_post(
                content_hash=content_hash,
                platform=post_data["platform"],
                content=post_data["text"],
                posted_at=posted_at,
                post_id=str(post_data["id"]),
                engagement_metrics=engagement_metrics
            )
            
            logger.info(f"✅ New Truth Social post stored: {post.id} - {post_data['text'][:50]}...")
            
            # Return processed data for sentiment analysis
            return {
                "post_id": post.id,
                "platform": post_data["platform"],
                "content": post_data["text"],
                "external_id": str(post_data["id"]),
                "created_at": post_data["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Error processing post: {e}")
            return None

    def start_monitoring(self) -> None:
        """Start monitoring using polling."""
        logger.info("Starting Truth Social RapidAPI monitoring...")
        
        # Test connection first
        if not self.test_connection():
            logger.error("Cannot start monitoring - API connection failed")
            return
        
        # Get only the most recent post first
        recent_posts = self.get_recent_posts(max_results=1)
        for post in recent_posts:
            self.process_post(post)
        
        # Start polling monitoring
        self.is_monitoring = True
        self._start_polling_monitoring()

    def _start_polling_monitoring(self) -> None:
        """Start polling-based monitoring for posts."""
        def polling_worker():
            logger.info("🚀 Truth Social polling monitoring started - checking latest post every 30 seconds")
            last_post_id = None
            
            while self.is_monitoring:
                try:
                    # Get only the most recent post
                    posts = self.get_recent_posts(max_results=1)
                    
                    if posts:
                        latest_post = posts[0]
                        
                        # Process only if this is a NEW post
                        if last_post_id is None or latest_post["id"] != last_post_id:
                            new_posts = [latest_post]
                        else:
                            new_posts = []
                        
                        # Process only new posts
                        for post in new_posts:
                            processed = self.process_post(post)
                            if processed and self.on_new_post:
                                self.on_new_post(processed)
                        
                        # Update last post ID
                        if posts:
                            last_post_id = posts[0]["id"]
                    
                    # Wait 30 seconds before next check (same as Twitter)
                    time.sleep(30)
                    
                except Exception as e:
                    logger.error(f"Error in polling monitoring: {e}")
                    time.sleep(30)  # Wait before retrying
        
        # Start polling in a separate thread
        polling_thread = threading.Thread(target=polling_worker, name="TruthSocialPolling")
        polling_thread.daemon = True
        polling_thread.start()

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self.is_monitoring = False
        logger.info("Truth Social monitoring stopped")

    def get_monitoring_status(self) -> Dict:
        """Get current monitoring status."""
        return {
            "monitoring": self.is_monitoring,
            "platform": "TRUTH_SOCIAL",
            "method": "RapidAPI Polling",
            "real_time": False,
            "polling_interval": "30 seconds",
            "last_check": get_timestamp()
        }

