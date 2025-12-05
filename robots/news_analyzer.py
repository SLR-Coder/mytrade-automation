# robots/news_analyzer.py
# -*- coding: utf-8 -*-
"""
Robot 2: News Analyzer
Fetches news, performs sentiment analysis, saves to News tab, and shares to Telegram
"""

import os
import logging
import asyncio
import time
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import requests

import google.generativeai as genai
from telegram import Bot
from telegram.constants import ParseMode

from utils.secrets import get_secret
from utils.auth import get_gspread_client
from utils.common import status_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-2-NewsAnalyzer")

# Configuration
NEWS_TAB = "News"
NEWS_LOOKBACK_HOURS = int(os.getenv("NEWS_LOOKBACK_HOURS", "6"))
MAX_NEWS_PER_CATEGORY = 5
MAX_TELEGRAM_NEWS = 10


@dataclass
class NewsItem:
    """News item data structure"""
    published_at: datetime
    title: str
    summary: str
    turkish_summary: str
    source: str
    url: str
    sentiment_score: float
    sentiment_label: str
    impact: str
    related_markets: List[str]


class NewsAnalyzer:
    """News fetcher and sentiment analyzer"""

    def __init__(self):
        """Initialize news analyzer"""
        self.newsapi_key = get_secret("NEWSAPI_KEY", required=False)

        # Initialize Gemini for sentiment analysis and Turkish translations
        gemini_key = get_secret("GEMINI_API_KEY", required=False)
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.gemini_model = None

        logger.info(f"NewsAnalyzer initialized (NewsAPI: {'✓' if self.newsapi_key else '✗'}, Gemini: {'✓' if self.gemini_model else '✗'})")

    def fetch_news(self, query: str, lookback_hours: int = 24) -> List[dict]:
        """
        Fetch news from NewsAPI

        Args:
            query: Search query (e.g., "bitcoin OR crypto")
            lookback_hours: Hours to look back (not used in free tier)

        Returns:
            List of news articles
        """
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured")
            return []

        try:
            # Note: Free tier doesn't support 'from' date filtering well
            # So we fetch recent news and filter client-side if needed
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": self.newsapi_key,
                "pageSize": 10
            }

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            articles = data.get("articles", [])

            logger.info(f"✓ Fetched {len(articles)} news articles for '{query}'")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")
            return []

    def analyze_sentiment(self, title: str, description: Optional[str] = None) -> dict:
        """Analyze sentiment using Gemini"""
        if not self.gemini_model:
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "Nötr",
                "impact": "ORTA"
            }

        try:
            text = title
            if description:
                text += f" {description}"

            prompt = f"""Analyze the sentiment and market impact of this financial news:

"{text}"

Respond ONLY in this exact format (no extra text):
SENTIMENT_SCORE: [number from -1.0 to +1.0]
SENTIMENT_LABEL: [Pozitif/Negatif/Nötr]
IMPACT: [YÜKSEK/ORTA/DÜŞÜK]
"""

            response = self.gemini_model.generate_content(prompt)
            content = response.text
            return self._parse_sentiment_response(content)

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "Nötr",
                "impact": "ORTA"
            }

    def _parse_sentiment_response(self, content: str) -> dict:
        """Parse Gemini sentiment response"""
        sentiment_score = 0.0
        sentiment_label = "Nötr"
        impact = "ORTA"

        for line in content.strip().split('\n'):
            line = line.strip()
            if line.startswith("SENTIMENT_SCORE:"):
                try:
                    sentiment_score = float(line.split(":", 1)[1].strip())
                    sentiment_score = max(-1.0, min(1.0, sentiment_score))
                except:
                    pass
            elif line.startswith("SENTIMENT_LABEL:"):
                sentiment_label = line.split(":", 1)[1].strip()
            elif line.startswith("IMPACT:"):
                impact = line.split(":", 1)[1].strip().upper()

        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "impact": impact
        }

    def generate_turkish_summary(self, title: str, description: Optional[str] = None) -> str:
        """Generate Turkish summary of news using Gemini"""
        if not self.gemini_model:
            return title

        try:
            text = title
            if description:
                text += f"\n\n{description}"

            prompt = f"""Sen bir finansal haber çevirmenisin. Aşağıdaki İngilizce haberi Türkçeye çevir.

İngilizce:
"{text}"

Talimatlar:
1. Haberi Türkçeye çevir (2-3 cümle, kısa ve öz)
2. Profesyonel trader dili kullan
3. Sadece Türkçe çeviriyi ver, başka açıklama ekleme

Türkçe:"""

            response = self.gemini_model.generate_content(prompt)
            turkish = response.text.strip()

            # Clean up
            turkish = turkish.replace("Türkçe:", "").strip()
            turkish = turkish.replace("Türkçe Özet:", "").strip()

            return turkish if turkish else title

        except Exception as e:
            logger.error(f"Turkish summary generation failed: {e}")
            return title

    def determine_related_markets(self, title: str, description: str = "") -> List[str]:
        """Determine which markets are related to this news"""
        text = (title + " " + (description or "")).lower()
        markets = []

        # Crypto
        if any(word in text for word in ["bitcoin", "btc", "crypto", "cryptocurrency"]):
            markets.append("BTC/USDT")
        if any(word in text for word in ["ethereum", "eth"]):
            markets.append("ETH/USDT")
        if any(word in text for word in ["xrp", "ripple"]):
            markets.append("XRP/USDT")

        # Forex
        if any(word in text for word in ["dollar", "usd", "fed", "federal reserve"]):
            markets.append("EUR/USD")
        if any(word in text for word in ["euro", "ecb", "european"]):
            markets.append("EUR/USD")
        if any(word in text for word in ["lira", "turkey", "türkiye", "tcmb"]):
            markets.append("USD/TRY")
        if any(word in text for word in ["yen", "japan", "boj"]):
            markets.append("USD/JPY")
        if any(word in text for word in ["pound", "sterling", "uk", "boe"]):
            markets.append("GBP/USD")

        # Commodities
        if any(word in text for word in ["gold", "altın"]):
            markets.append("XAU/USD")
        if any(word in text for word in ["silver", "gümüş"]):
            markets.append("XAG/USD")
        if any(word in text for word in ["oil", "crude", "petrol"]):
            markets.append("OIL")

        # Stocks
        if any(word in text for word in ["apple", "iphone"]):
            markets.append("AAPL")
        if any(word in text for word in ["tesla", "musk"]):
            markets.append("TSLA")
        if any(word in text for word in ["nvidia", "gpu", "ai chip"]):
            markets.append("NVDA")
        if any(word in text for word in ["s&p", "sp500", "wall street"]):
            markets.append("SPY")

        return markets[:3] if markets else ["GENEL"]


def save_news_to_sheet(news_items: List[NewsItem], ws) -> int:
    """Save news items to the News sheet tab"""
    if not news_items:
        return 0

    rows_to_add = []
    for news in news_items:
        # Format sentiment score without + sign (Google Sheets interprets + as formula)
        score_str = f"{news.sentiment_score:.2f}"

        row = [
            news.published_at.strftime("%Y-%m-%d %H:%M"),  # Zaman
            news.title[:200],  # Başlık (truncate)
            news.source,  # Kaynak
            score_str,  # Duyarlılık Skoru (without + prefix)
            news.sentiment_label,  # Duyarlılık
            news.impact,  # Etki
            ", ".join(news.related_markets),  # İlgili Piyasalar
            news.turkish_summary[:500],  # Türkçe Özet (truncate)
            news.url  # URL
        ]
        rows_to_add.append(row)

    # Append rows to sheet
    try:
        ws.append_rows(rows_to_add, value_input_option='USER_ENTERED')
        logger.info(f"✓ Saved {len(rows_to_add)} news items to '{NEWS_TAB}' tab")
        return len(rows_to_add)
    except Exception as e:
        logger.error(f"Failed to save news to sheet: {e}")
        return 0


def format_telegram_news(news_items: List[NewsItem]) -> str:
    """Format news for Telegram message"""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Group by impact
    high_impact = [n for n in news_items if n.impact == "YÜKSEK"]
    medium_impact = [n for n in news_items if n.impact == "ORTA"]
    low_impact = [n for n in news_items if n.impact == "DÜŞÜK"]

    message = f"""━━━━━━━━━━━━━━━━━━━━━━
📰 <b>PİYASA HABERLERİ</b>
━━━━━━━━━━━━━━━━━━━━━━
🕐 {now}
"""

    def format_news_item(news: NewsItem) -> str:
        # Sentiment emoji
        if news.sentiment_label == "Pozitif":
            emoji = "📈"
        elif news.sentiment_label == "Negatif":
            emoji = "📉"
        else:
            emoji = "➡️"

        markets = ", ".join(news.related_markets) if news.related_markets else "Genel"

        return f"""
{emoji} <b>{news.title[:100]}{'...' if len(news.title) > 100 else ''}</b>

{news.turkish_summary[:300]}{'...' if len(news.turkish_summary) > 300 else ''}

├─ 📊 Etki: {news.impact}
├─ 🎯 Piyasalar: {markets}
├─ 📰 Kaynak: {news.source}
└─ 🕐 {news.published_at.strftime("%H:%M")}
"""

    if high_impact:
        message += "\n🔴 <b>YÜKSEK ETKİ:</b>"
        for news in high_impact[:3]:
            message += format_news_item(news)

    if medium_impact:
        message += "\n🟡 <b>ORTA ETKİ:</b>"
        for news in medium_impact[:4]:
            message += format_news_item(news)

    if low_impact and len(high_impact) + len(medium_impact) < 5:
        message += "\n🟢 <b>DÜŞÜK ETKİ:</b>"
        for news in low_impact[:3]:
            message += format_news_item(news)

    message += "\n━━━━━━━━━━━━━━━━━━━━━━"

    return message


async def send_news_to_telegram(news_items: List[NewsItem], bot_token: str, chat_id: str) -> bool:
    """Send news to Telegram with retry logic"""
    if not news_items:
        logger.info("No news to send to Telegram")
        return True

    try:
        bot = Bot(token=bot_token)
        message = format_telegram_news(news_items)

        # Retry logic
        for attempt in range(3):
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
                logger.info(f"✓ News sent to Telegram ({len(news_items)} items)")
                return True
            except Exception as e:
                if attempt < 2:
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"Telegram error (attempt {attempt + 1}/3), waiting {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    except Exception as e:
        logger.error(f"Failed to send news to Telegram: {e}")
        return False


def run():
    """Main execution function for Robot 2"""
    logger.info("=" * 60)
    logger.info("ROBOT 2: NEWS ANALYZER - STARTING")
    logger.info("=" * 60)

    try:
        # Initialize
        analyzer = NewsAnalyzer()

        # Get secrets
        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID")
        telegram_token = get_secret("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = get_secret("TELEGRAM_CHAT_ID")

        # Connect to Google Sheets
        gc = get_gspread_client()
        spreadsheet = gc.open_by_key(sheet_id)

        # Get or create News tab
        try:
            news_ws = spreadsheet.worksheet(NEWS_TAB)
        except:
            logger.warning(f"'{NEWS_TAB}' tab not found, creating...")
            news_ws = spreadsheet.add_worksheet(title=NEWS_TAB, rows=1000, cols=10)
            # Add header row
            news_ws.append_row([
                "Zaman", "Başlık", "Kaynak", "Duyarlılık Skoru",
                "Duyarlılık", "Etki", "İlgili Piyasalar", "Türkçe Özet", "URL"
            ])

        # Define search queries
        queries = {
            "crypto": "bitcoin OR ethereum OR cryptocurrency",
            "forex": "forex OR USD OR EUR OR central bank OR interest rate",
            "commodities": "gold price OR oil price OR commodities",
            "stocks": "stock market OR S&P 500 OR NASDAQ OR earnings",
            "turkey": "Turkey economy OR Turkish lira OR TCMB"
        }

        all_news: List[NewsItem] = []

        # Fetch and analyze news (sentiment only - no Turkish translation yet)
        for category, query in queries.items():
            logger.info(f"\n📰 Fetching {category} news...")

            articles = analyzer.fetch_news(query, lookback_hours=NEWS_LOOKBACK_HOURS)

            for article in articles[:MAX_NEWS_PER_CATEGORY]:
                try:
                    title = article.get("title", "")
                    description = article.get("description", "")
                    source = article.get("source", {}).get("name", "Bilinmiyor")
                    url = article.get("url", "")

                    # Parse date
                    pub_str = article.get("publishedAt", "")
                    try:
                        published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    except:
                        published_at = datetime.now(timezone.utc)

                    # Skip old or duplicate news
                    if any(n.title == title for n in all_news):
                        continue

                    # Analyze sentiment ONLY (save AI calls - no Turkish translation yet)
                    sentiment = analyzer.analyze_sentiment(title, description)

                    # Determine related markets (no AI needed)
                    related_markets = analyzer.determine_related_markets(title, description)

                    news_item = NewsItem(
                        published_at=published_at,
                        title=title,
                        summary=description[:200] if description else "",
                        turkish_summary="",  # Will be filled later for top 10 only
                        source=source,
                        url=url,
                        sentiment_score=sentiment["sentiment_score"],
                        sentiment_label=sentiment["sentiment_label"],
                        impact=sentiment["impact"],
                        related_markets=related_markets
                    )

                    all_news.append(news_item)

                    logger.info(
                        f"  ✓ {title[:50]}... | "
                        f"{sentiment['sentiment_label']} ({sentiment['sentiment_score']:+.2f}) | "
                        f"{sentiment['impact']}"
                    )

                    # Rate limiting for Gemini
                    time.sleep(0.3)

                except Exception as e:
                    logger.warning(f"Failed to process article: {e}")
                    continue

        # Sort by impact and time
        impact_order = {"YÜKSEK": 0, "ORTA": 1, "DÜŞÜK": 2}
        all_news.sort(key=lambda x: (impact_order.get(x.impact, 1), -x.published_at.timestamp()))

        # Generate Turkish summaries ONLY for top 10 (save AI calls!)
        top_news = all_news[:MAX_TELEGRAM_NEWS]
        logger.info(f"\n🇹🇷 Generating Turkish summaries for top {len(top_news)} news...")
        for news in top_news:
            news.turkish_summary = analyzer.generate_turkish_summary(news.title, news.summary)
            time.sleep(0.3)

        # Save ONLY top 10 to Google Sheets (the ones with Turkish summaries)
        saved = save_news_to_sheet(top_news, news_ws)

        # Send to Telegram
        if top_news:
            asyncio.run(send_news_to_telegram(top_news, telegram_token, telegram_chat_id))

        # Summary
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"✅ ROBOT 2 TAMAMLANDI!")
        logger.info(f"  📰 Toplam haber çekildi: {len(all_news)}")
        logger.info(f"  🇹🇷 Türkçeye çevrilen: {len(top_news)}")
        logger.info(f"  💾 Sheet'e kaydedilen: {saved}")
        logger.info(f"  📱 Telegram'a gönderilen: {len(top_news)}")
        logger.info(f"  🔴 Yüksek etki: {len([n for n in top_news if n.impact == 'YÜKSEK'])}")
        logger.info(f"  🟡 Orta etki: {len([n for n in top_news if n.impact == 'ORTA'])}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ ROBOT 2 FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run()
