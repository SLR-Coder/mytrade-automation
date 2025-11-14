# tests/test_telegram_formatter.py
# -*- coding: utf-8 -*-
"""
Tests for Telegram formatter utilities
"""

import pytest
from utils.telegram_formatter import (
    format_trading_signal,
    format_performance_report,
    format_error_notification
)

class TestTelegramFormatter:
    """Test Telegram message formatting"""

    def test_format_trading_signal_buy(self):
        """Test formatting BUY signal"""
        message = format_trading_signal(
            market="BTC/USDT",
            signal="BUY",
            confidence=80,
            reasoning="Strong bullish momentum",
            price=50000.0,
            indicators={"rsi": 65.0, "trend": "bullish"}
        )

        assert "🚀" in message  # BUY emoji
        assert "BTC/USDT" in message
        assert "80%" in message
        assert "50,000" in message
        assert "RSI: 65.0" in message
        assert "bullish" in message

    def test_format_trading_signal_sell(self):
        """Test formatting SELL signal"""
        message = format_trading_signal(
            market="ETH/USDT",
            signal="SELL",
            confidence=70,
            reasoning="Overbought conditions",
            price=3000.0,
            indicators={"rsi": 75.0, "trend": "bearish"}
        )

        assert "🔻" in message  # SELL emoji
        assert "ETH/USDT" in message
        assert "70%" in message
        assert "Overbought" in message

    def test_format_trading_signal_hold(self):
        """Test formatting HOLD signal"""
        message = format_trading_signal(
            market="BNB/USDT",
            signal="HOLD",
            confidence=60,
            reasoning="Market consolidating",
            price=400.0
        )

        assert "⏸" in message  # HOLD emoji
        assert "BNB/USDT" in message
        assert "60%" in message

    def test_format_performance_report(self):
        """Test formatting performance report"""
        metrics = {
            "win_rate": 65.5,
            "avg_profit_percent": 3.2,
            "avg_loss_percent": -1.5,
            "total_signals": 100,
            "successful_signals": 65,
            "failed_signals": 30,
            "pending_signals": 5
        }

        message = format_performance_report(metrics)

        assert "Performance Report" in message
        assert "65.5%" in message
        assert "✅" in message  # Good win rate
        assert "3.2%" in message
        assert "-1.5%" in message
        assert "Total Signals: 100" in message

    def test_format_error_notification(self):
        """Test formatting error notification"""
        message = format_error_notification(
            robot_name="Market Harvester",
            error="API rate limit exceeded",
            attempt=2,
            max_retries=3
        )

        assert "🚨" in message
        assert "Market Harvester" in message
        assert "2/4" in message  # attempt/total
        assert "API rate limit" in message
        assert "Retrying" in message

    def test_format_error_max_retries(self):
        """Test error notification when max retries exceeded"""
        message = format_error_notification(
            robot_name="AI Signal Generator",
            error="Connection timeout",
            attempt=4,
            max_retries=3
        )

        assert "Max retries exceeded" in message
        assert "❌" in message

    def test_long_reasoning_truncation(self):
        """Test that long reasoning gets truncated"""
        long_reasoning = "A" * 250  # Long string

        message = format_trading_signal(
            market="TEST/USDT",
            signal="BUY",
            confidence=70,
            reasoning=long_reasoning,
            price=100.0
        )

        assert "..." in message  # Should be truncated
        assert len(message) < len(long_reasoning) + 100  # Should be shorter

    def test_rsi_status_classification(self):
        """Test RSI status classification"""
        # Oversold
        message = format_trading_signal(
            market="TEST/USDT",
            signal="BUY",
            confidence=70,
            reasoning="Test",
            price=100.0,
            indicators={"rsi": 25.0}
        )
        assert "Oversold" in message

        # Overbought
        message = format_trading_signal(
            market="TEST/USDT",
            signal="SELL",
            confidence=70,
            reasoning="Test",
            price=100.0,
            indicators={"rsi": 75.0}
        )
        assert "Overbought" in message

        # Neutral
        message = format_trading_signal(
            market="TEST/USDT",
            signal="HOLD",
            confidence=70,
            reasoning="Test",
            price=100.0,
            indicators={"rsi": 50.0}
        )
        assert "Neutral" in message