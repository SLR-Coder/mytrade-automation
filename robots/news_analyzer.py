# robots/news_analyzer.py
# -*- coding: utf-8 -*-
"""
Robot 2: News Analyzer
Fetches news and performs sentiment analysis using AI
"""

import os
import logging
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
import requests
import google.generativeai as genai

# Database imports removed - using Google Sheets only for production
# from core.models import NewsItem
# from core.database import get_db_session
# from data.models.news import NewsModel
from dataclasses import dataclass
from typing import Optional as OptionalType

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.schema import resolve_columns


@dataclass
class NewsItem:
    """News item data structure (replaced database model)"""
    published_at: str
    title: str
    summary: str
    turkish_summary: str
    source: str
    url: str
    sentiment_score: float
    sentiment_label: str
    impact: str
    related_markets: str

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-2-NewsAnalyzer")

# Environment variables
SHEET_TAB = os.getenv("SHEET_TAB", "MarketData")
NEWS_LOOKBACK_HOURS = int(os.getenv("NEWS_LOOKBACK_HOURS", "24"))


class NewsAnalyzer:
    """News fetcher and sentiment analyzer"""

    def __init__(self):
        """Initialize news analyzer"""
        self.newsapi_key = get_secret("NEWSAPI_KEY", required=False)

        # Initialize Gemini for Turkish translations
        gemini_key = get_secret("GEMINI_API_KEY", required=False)
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.gemini_model = None

        logger.info(f"NewsAnalyzer initialized (NewsAPI: {'✓' if self.newsapi_key else '✗'}, Gemini: {'✓' if self.gemini_model else '✗'})")

    def fetch_news(self, query: str, lookback_hours: int = 24) -> List[dict]:
        """
        Fetch news from NewsAPI

        Args:
            query: Search query (e.g., "bitcoin OR crypto")
            lookback_hours: Hours to look back

        Returns:
            List of news articles
        """
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured")
            return []

        try:
            from_date = (datetime.utcnow() - timedelta(hours=lookback_hours)).isoformat()

            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "from": from_date,
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": self.newsapi_key,
                "pageSize": 20
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            articles = data.get("articles", [])

            logger.info(f"✓ Fetched {len(articles)} news articles for '{query}'")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")
            return []

    def analyze_sentiment(self, title: str, description: Optional[str] = None) -> dict:
        """
        Analyze sentiment using Gemini

        Args:
            title: News title
            description: News description

        Returns:
            Dict with sentiment_score, sentiment_label, impact
        """
        if not self.gemini_model:
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "impact": "MEDIUM"
            }

        try:
            text = title
            if description:
                text += f" {description}"

            prompt = f"""Analyze the sentiment and market impact of this news:

"{text}"

Provide your analysis in this format:
SENTIMENT_SCORE: [number from -1.0 (very negative) to +1.0 (very positive)]
SENTIMENT_LABEL: [positive/negative/neutral]
IMPACT: [HIGH/MEDIUM/LOW]
REASONING: [Brief explanation]
"""

            response = self.gemini_model.generate_content(prompt)
            content = response.text
            return self._parse_sentiment_response(content)

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "impact": "MEDIUM"
            }

    def _parse_sentiment_response(self, content: str) -> dict:
        """Parse Gemini sentiment response"""
        lines = content.strip().split('\n')

        sentiment_score = 0.0
        sentiment_label = "neutral"
        impact = "MEDIUM"

        for line in lines:
            line = line.strip()
            if line.startswith("SENTIMENT_SCORE:"):
                try:
                    sentiment_score = float(line.split(":", 1)[1].strip())
                    sentiment_score = max(-1.0, min(1.0, sentiment_score))  # Clamp
                except:
                    pass
            elif line.startswith("SENTIMENT_LABEL:"):
                sentiment_label = line.split(":", 1)[1].strip().lower()
            elif line.startswith("IMPACT:"):
                impact = line.split(":", 1)[1].strip().upper()

        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "impact": impact
        }

    def generate_turkish_summary(self, title: str, description: Optional[str] = None, sentiment_label: str = "neutral") -> Optional[str]:
        """
        Generate Turkish summary of news using Gemini 2.5 Pro

        Args:
            title: News title (English)
            description: News description (English)
            sentiment_label: Sentiment label (positive/negative/neutral)

        Returns:
            Turkish summary string
        """
        if not self.gemini_model:
            return None

        try:
            text = title
            if description:
                text += f"\n\n{description}"

            # Sentiment emoji for context
            sentiment_emoji = "📈" if sentiment_label == "positive" else "📉" if sentiment_label == "negative" else "➡️"

            prompt = f"""Sen bir finansal haber çevirmenisin. Aşağıdaki İngilizce haberi Türkçeye çevir ve özetle.

İngilizce Haber:
"{text}"

Sentiment: {sentiment_label}

Talimatlar:
1. Haberi Türkçeye çevir (2-3 cümle, kısa ve öz)
2. Profesyonel trader dili kullan
3. Piyasaya etkisini vurgula
4. Sadece Türkçe özeti ver, başka açıklama ekleme

Türkçe Özet:"""

            response = self.gemini_model.generate_content(prompt)
            turkish_summary = response.text.strip()

            # Remove any "Türkçe Özet:" prefix if present
            turkish_summary = turkish_summary.replace("Türkçe Özet:", "").strip()

            # Add sentiment emoji
            turkish_summary = f"{sentiment_emoji} {turkish_summary}"

            return turkish_summary

        except Exception as e:
            logger.error(f"Turkish summary generation failed: {e}")
            return None


async def run():
    """Main execution function for Robot 2"""
    logger.info("=" * 60)
    logger.info("ROBOT 2: NEWS ANALYZER - STARTING")
    logger.info("=" * 60)

    try:
        # Initialize analyzer
        analyzer = NewsAnalyzer()

        # Define news queries for different markets
        queries = {
            "crypto": "bitcoin OR ethereum OR cryptocurrency OR crypto market",
            "forex": "USD TRY OR forex OR currency market OR central bank",
            "commodities": "gold price OR silver OR commodities",
        }

        all_news_items: List[NewsItem] = []

        # Fetch news for each category
        for category, query in queries.items():
            logger.info(f"\nFetching {category} news...")

            articles = analyzer.fetch_news(query, lookback_hours=NEWS_LOOKBACK_HOURS)

            for article in articles[:10]:  # Limit to top 10 per category
                try:
                    title = article.get("title", "")
                    description = article.get("description", "")
                    source = article.get("source", {}).get("name", "Bilinmiyor")
                    url = article.get("url", "")
                    published_at = datetime.fromisoformat(
                        article.get("publishedAt", "").replace("Z", "+00:00")
                    )

                    # Analyze sentiment
                    sentiment = analyzer.analyze_sentiment(title, description)

                    # Generate Turkish summary
                    turkish_summary = analyzer.generate_turkish_summary(
                        title,
                        description,
                        sentiment["sentiment_label"]
                    )

                    # Determine related markets
                    related_markets = []
                    title_lower = title.lower()
                    if any(word in title_lower for word in ["bitcoin", "btc", "crypto"]):
                        related_markets.extend(["BTC/USDT", "ETH/USDT"])
                    if any(word in title_lower for word in ["usd", "try", "lira", "dollar"]):
                        related_markets.append("USD/TRY")
                    if any(word in title_lower for word in ["gold", "silver"]):
                        related_markets.append("GOLD")

                    news_item = NewsItem(
                        title=title,
                        summary=description[:200] if description else None,
                        turkish_summary=turkish_summary,
                        source=source,
                        published_at=published_at,
                        url=url,
                        sentiment_score=sentiment["sentiment_score"],
                        sentiment_label=sentiment["sentiment_label"],
                        impact=sentiment["impact"],
                        related_markets=related_markets
                    )

                    all_news_items.append(news_item)

                    logger.info(
                        f"  ✓ {title[:60]}... | "
                        f"Sentiment: {sentiment['sentiment_label']} "
                        f"({sentiment['sentiment_score']:+.2f}) | "
                        f"Impact: {sentiment['impact']}"
                    )

                except Exception as e:
                    logger.error(f"Failed to process article: {e}")
                    continue

        # Database save removed - using Google Sheets only for production
        # if all_news_items:
        #     async with get_db_session() as session:
        #         for news_item in all_news_items:
        #             news_model = NewsModel(...)
        #             session.add(news_model)
        #     logger.info(f"\n✓ Saved {len(all_news_items)} news items to database")

        # Update Google Sheets (write top news to a summary column)
        try:
            sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
            gc = get_gspread_client()
            ws = gc.open_by_key(sheet_id).worksheet(SHEET_TAB)

            # Get high impact news
            high_impact_news = [n for n in all_news_items if n.impact == "HIGH"][:3]

            if high_impact_news:
                news_summary = "📰 Top News:\n" + "\n".join([
                    f"• {n.title[:50]}... ({n.sentiment_label})"
                    for n in high_impact_news
                ])

                # Write to column T (News Summary) in first data row
                ws.update_acell("T2", news_summary[:500])  # Truncate if needed
                logger.info("✓ Updated Google Sheets with news summary")

        except Exception as e:
            logger.error(f"Failed to update Google Sheets: {e}")

        # Summary
        logger.info("=" * 60)
        logger.info(f"✓ ROBOT 2 COMPLETED!")
        logger.info(f"  Total news analyzed: {len(all_news_items)}")
        logger.info(f"  High impact news: {len([n for n in all_news_items if n.impact == 'HIGH'])}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ ROBOT 2 FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Database initialization removed - using Google Sheets only
    # from core.database import init_database, close_database

    async def main():
        # await init_database()  # Removed - no database in production
        try:
            await run()
        finally:
            pass  # await close_database()  # Removed - no database in production

    asyncio.run(main())