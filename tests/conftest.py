# tests/conftest.py
# -*- coding: utf-8 -*-
"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_gspread_client():
    """Mock Google Sheets client"""
    mock_client = Mock()
    mock_worksheet = Mock()
    mock_worksheet.get_all_values.return_value = []
    mock_client.open_by_key.return_value.worksheet.return_value = mock_worksheet
    return mock_client

@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot"""
    mock_bot = AsyncMock()
    mock_bot.send_message.return_value = True
    return mock_bot

@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "market": "BTC/USDT",
        "price": 50000.0,
        "volume": 1000000.0,
        "change_percent": 5.2,
        "indicators": {
            "rsi": 65.0,
            "macd": 100.0,
            "bb_upper": 52000.0,
            "bb_middle": 50000.0,
            "bb_lower": 48000.0,
            "trend": "bullish"
        }
    }

@pytest.fixture
def sample_ai_signal():
    """Sample AI signal for testing"""
    return {
        "signal": "BUY",
        "confidence": 75,
        "reasoning": "Strong bullish indicators with RSI showing momentum"
    }