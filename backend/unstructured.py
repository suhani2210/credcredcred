import feedparser
import logging
from typing import List

logger = logging.getLogger(__name__)

# Try to import transformers, fallback to basic sentiment if not available
try:
    from transformers import pipeline
    sentiment_model = pipeline(
        "text-classification",
        model="ProsusAI/finbert",
        return_all_scores=False
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("Transformers not available. Using basic sentiment analysis.")
    TRANSFORMERS_AVAILABLE = False
except Exception as e:
    logger.warning(f"Could not load sentiment model: {e}. Using basic sentiment analysis.")
    TRANSFORMERS_AVAILABLE = False

def basic_sentiment_score(headlines: List[str]) -> float:
    """Basic sentiment analysis using keyword matching as fallback"""
    positive_words = ['up', 'rise', 'gain', 'growth', 'profit', 'beat', 'strong', 'increase', 'bull']
    negative_words = ['down', 'fall', 'loss', 'decline', 'drop', 'weak', 'decrease', 'bear', 'crash']
    
    total_score = 0
    count = 0
    
    for headline in headlines:
        headline_lower = headline.lower()
        positive_count = sum(1 for word in positive_words if word in headline_lower)
        negative_count = sum(1 for word in negative_words if word in headline_lower)
        
        if positive_count > negative_count:
            total_score += 0.7
        elif negative_count > positive_count:
            total_score += 0.3
        else:
            total_score += 0.5
        count += 1
    
    return total_score / count if count > 0 else 0.5

def news_sentiment_score(ticker: str) -> float:
    """
    Get sentiment score for a ticker based on recent news headlines
    
    Returns:
        float: Sentiment score between 0 and 1 (0 = negative, 1 = positive)
    """
    try:
        # Fetch news headlines
        feed_url = f"https://news.google.com/rss/search?q={ticker}+stock+financial"
        feed = feedparser.parse(feed_url)
        
        if not feed.entries:
            logger.warning(f"No news found for {ticker}")
            return 0.5  # Neutral default
        
        headlines = [entry.title for entry in feed.entries[:20]]  # Limit to recent 20
        
        if not headlines:
            return 0.5
        
        if TRANSFORMERS_AVAILABLE:
            try:
                # Use FinBERT for financial sentiment analysis
                results = sentiment_model(headlines)
                
                label_to_score = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}
                
                scores = []
                for headline, result in zip(headlines, results):
                    label = result["label"].lower()
                    confidence = result["score"]
                    
                    if label in label_to_score:
                        score = label_to_score[label]
                        # Weight by confidence
                        weighted_score = score * confidence + 0.5 * (1 - confidence)
                        scores.append(weighted_score)
                        logger.debug(f"'{headline[:50]}...' -> {label} ({confidence:.3f}) = {weighted_score:.3f}")
                
                if scores:
                    final_sentiment = sum(scores) / len(scores)
                else:
                    final_sentiment = 0.5
                    
                logger.info(f"Sentiment for {ticker}: {final_sentiment:.3f} (from {len(headlines)} headlines)")
                return max(0.0, min(1.0, final_sentiment))
                
            except Exception as e:
                logger.warning(f"Error with FinBERT model for {ticker}: {e}. Using basic sentiment.")
                return basic_sentiment_score(headlines)
        else:
            # Use basic sentiment analysis
            return basic_sentiment_score(headlines)
            
    except Exception as e:
        logger.error(f"Error getting sentiment for {ticker}: {e}")
        return 0.5  # Neutral default on error

# Test function
if __name__ == "__main__":
    test_ticker = "AAPL"
    score = news_sentiment_score(test_ticker)
    print(f"Sentiment score for {test_ticker}: {score:.3f}")