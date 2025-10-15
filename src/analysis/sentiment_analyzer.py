"""Sentiment analysis using Anthropic Claude API."""

import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except (ImportError, ModuleNotFoundError, TypeError):
    # Fallback for Python 3.13+ compatibility
    anthropic = None
    ANTHROPIC_AVAILABLE = False

from config.settings import settings
from src.database.repository import DatabaseRepository
from src.database.models import SentimentAnalysis, SocialMediaPost
from src.utils import setup_logger

logger = setup_logger(__name__)


class SentimentAnalyzer:
    """Sentiment analysis using Claude API."""

    def __init__(self):
        """Initialize sentiment analyzer."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic is not available. Please install it or use Python < 3.13")
        
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.db = DatabaseRepository()
        self.model_version = "claude-3-5-sonnet-20241022"
        
        logger.info("Sentiment analyzer initialized")

    def test_connection(self) -> bool:
        """Test Claude API connection."""
        try:
            # Test with a simple message
            test_message = "Test connection"
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": test_message}]
            )
            
            if response.content:
                logger.info("✅ Claude API connected successfully")
                return True
            else:
                logger.error("❌ Claude API: No response received")
                return False
                
        except Exception as e:
            logger.error(f"❌ Claude API connection failed: {e}")
            return False

    def analyze_sentiment(self, post_content: str, platform: str) -> Tuple[int, str]:
        """
        Analyze sentiment of a social media post.

        Args:
            post_content: The text content of the post
            platform: Platform name (TWITTER or TRUTHSOCIAL)

        Returns:
            Tuple of (score, reasoning)
        """
        try:
            # Create the prompt for Claude
            prompt = f"""Analyze this social media post from Donald Trump for financial market sentiment.

Post: "{post_content}"

Provide:
1. Sentiment Score (0-10): 0=extremely bearish, 5=neutral, 10=extremely bullish
2. Reasoning: 2-3 sentences explaining your score

Focus on implications for cryptocurrency markets, particularly Bitcoin.
Consider: policy statements, economic outlook, geopolitical tensions, market confidence.

Format response as JSON:
{{
  "score": <integer 0-10>,
  "reasoning": "<explanation>"
}}"""

            # Call Claude API
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                temperature=0.3,  # Lower temperature for more consistent results
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract response text
            response_text = response.content[0].text.strip()
            
            # Parse JSON response
            try:
                # Clean up response text (remove markdown formatting if present)
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                result = json.loads(response_text)
                score = int(result["score"])
                reasoning = result["reasoning"]
                
                # Validate score range
                if not 0 <= score <= 10:
                    logger.warning(f"Score {score} out of range, clamping to 0-10")
                    score = max(0, min(10, score))
                
                logger.info(f"Sentiment analysis: Score {score}/10 - {reasoning[:50]}...")
                return score, reasoning
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to parse Claude response: {e}")
                logger.error(f"Response text: {response_text}")
                
                # Fallback: try to extract score from text
                score = self._extract_score_from_text(response_text)
                reasoning = f"Analysis failed, extracted score: {score}"
                return score, reasoning
                
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            # Return neutral score on error
            return 5, f"Analysis failed due to error: {str(e)}"

    def _extract_score_from_text(self, text: str) -> int:
        """Extract score from text if JSON parsing fails."""
        try:
            # Look for patterns like "score: 8" or "8/10"
            import re
            
            # Try to find number followed by /10
            match = re.search(r'(\d+)/10', text)
            if match:
                return int(match.group(1))
            
            # Try to find "score:" followed by number
            match = re.search(r'score[:\s]*(\d+)', text, re.IGNORECASE)
            if match:
                return int(match.group(1))
            
            # Try to find any number between 0-10
            match = re.search(r'\b([0-9]|10)\b', text)
            if match:
                return int(match.group(1))
            
            # Default to neutral
            return 5
            
        except Exception:
            return 5

    def process_post(self, post_data: Dict) -> Optional[Dict]:
        """
        Process a post and perform sentiment analysis.

        Args:
            post_data: Post data from social media monitor

        Returns:
            Sentiment analysis result or None if analysis fails
        """
        try:
            post_id = post_data["post_id"]
            content = post_data["content"]
            platform = post_data["platform"]
            
            # Check if sentiment already exists for this post
            existing_sentiment = self.db.get_session().query(
                SentimentAnalysis
            ).filter_by(post_id=post_id).first()
            
            if existing_sentiment:
                logger.debug(f"Sentiment already exists for post {post_id}")
                return {
                    "sentiment_id": existing_sentiment.id,
                    "score": existing_sentiment.score,
                    "reasoning": existing_sentiment.reasoning
                }
            
            # Perform sentiment analysis
            score, reasoning = self.analyze_sentiment(content, platform)
            
            # Store in database
            sentiment = self.db.create_sentiment(
                post_id=post_id,
                score=score,
                reasoning=reasoning,
                model_version=self.model_version
            )
            
            logger.info(f"✅ Sentiment analysis stored: {sentiment.id} - Score {score}/10")
            
            return {
                "sentiment_id": sentiment.id,
                "score": score,
                "reasoning": reasoning,
                "platform": platform,
                "content": content[:100] + "..." if len(content) > 100 else content
            }
            
        except Exception as e:
            logger.error(f"Error processing post for sentiment: {e}")
            return None

    def get_sentiment_summary(self, hours: int = 24) -> Dict:
        """
        Get sentiment summary for the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            Sentiment summary statistics
        """
        try:
            from datetime import datetime, timedelta
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            with self.db.get_session() as session:
                sentiments = session.query(SentimentAnalysis).join(
                    SocialMediaPost
                ).filter(
                    SentimentAnalysis.analyzed_at >= cutoff_time
                ).all()
                
                if not sentiments:
                    return {
                        "total_posts": 0,
                        "average_score": 5.0,
                        "bullish_posts": 0,
                        "bearish_posts": 0,
                        "neutral_posts": 0,
                        "scores": []
                    }
                
                scores = [s.score for s in sentiments]
                avg_score = sum(scores) / len(scores)
                
                bullish = len([s for s in scores if s > 5])
                bearish = len([s for s in scores if s < 5])
                neutral = len([s for s in scores if s == 5])
                
                return {
                    "total_posts": len(sentiments),
                    "average_score": round(avg_score, 2),
                    "bullish_posts": bullish,
                    "bearish_posts": bearish,
                    "neutral_posts": neutral,
                    "scores": scores,
                    "timeframe_hours": hours
                }
                
        except Exception as e:
            logger.error(f"Error getting sentiment summary: {e}")
            return {"error": str(e)}
