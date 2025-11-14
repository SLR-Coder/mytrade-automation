# -*- coding: utf-8 -*-
"""
Technical indicators calculator
Using pandas-ta for professional-grade indicators
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

try:
    import pandas_ta as ta
except ImportError:
    ta = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MyTrade-Indicators")


class TechnicalIndicators:
    """
    Calculate technical indicators from OHLCV data
    """

    @staticmethod
    def prepare_dataframe(candles: List[Dict]) -> pd.DataFrame:
        """
        Convert candle list to pandas DataFrame

        Args:
            candles: List of candle dicts with keys:
                     timestamp, open, high, low, close, volume

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        df = pd.DataFrame(candles)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)
        return df[['open', 'high', 'low', 'close', 'volume']]

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index)

        Args:
            df: DataFrame with 'close' column
            period: RSI period (default: 14)

        Returns:
            Series with RSI values (0-100)
        """
        if ta:
            return ta.rsi(df['close'], length=period)
        else:
            # Fallback manual calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            df: DataFrame with 'close' column
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line period (default: 9)

        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        if ta:
            macd_df = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
            return (
                macd_df[f'MACD_{fast}_{slow}_{signal}'],
                macd_df[f'MACDs_{fast}_{slow}_{signal}'],
                macd_df[f'MACDh_{fast}_{slow}_{signal}']
            )
        else:
            # Manual calculation
            ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
            ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            return macd_line, signal_line, histogram

    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame,
        period: int = 20,
        std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands

        Args:
            df: DataFrame with 'close' column
            period: SMA period (default: 20)
            std: Standard deviation multiplier (default: 2.0)

        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        if ta:
            bb = ta.bbands(df['close'], length=period, std=std)
            return (
                bb[f'BBU_{period}_{std}'],
                bb[f'BBM_{period}_{std}'],
                bb[f'BBL_{period}_{std}']
            )
        else:
            # Manual calculation
            middle = df['close'].rolling(window=period).mean()
            std_dev = df['close'].rolling(window=period).std()
            upper = middle + (std_dev * std)
            lower = middle - (std_dev * std)
            return upper, middle, lower

    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate EMA (Exponential Moving Average)

        Args:
            df: DataFrame with 'close' column
            period: EMA period

        Returns:
            Series with EMA values
        """
        if ta:
            return ta.ema(df['close'], length=period)
        else:
            return df['close'].ewm(span=period, adjust=False).mean()

    @staticmethod
    def find_support_resistance(
        df: pd.DataFrame,
        lookback: int = 100,
        num_levels: int = 2
    ) -> Tuple[List[float], List[float]]:
        """
        Find support and resistance levels

        Args:
            df: DataFrame with OHLC data
            lookback: Number of candles to look back
            num_levels: Number of support/resistance levels to find

        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        recent = df.tail(lookback)

        # Find local minima (support) and maxima (resistance)
        support_candidates = []
        resistance_candidates = []

        for i in range(2, len(recent) - 2):
            # Support: local minimum
            if (recent['low'].iloc[i] < recent['low'].iloc[i - 1] and
                recent['low'].iloc[i] < recent['low'].iloc[i - 2] and
                recent['low'].iloc[i] < recent['low'].iloc[i + 1] and
                recent['low'].iloc[i] < recent['low'].iloc[i + 2]):
                support_candidates.append(recent['low'].iloc[i])

            # Resistance: local maximum
            if (recent['high'].iloc[i] > recent['high'].iloc[i - 1] and
                recent['high'].iloc[i] > recent['high'].iloc[i - 2] and
                recent['high'].iloc[i] > recent['high'].iloc[i + 1] and
                recent['high'].iloc[i] > recent['high'].iloc[i + 2]):
                resistance_candidates.append(recent['high'].iloc[i])

        # Get strongest levels (most recent and significant)
        support_levels = sorted(support_candidates, reverse=True)[:num_levels]
        resistance_levels = sorted(resistance_candidates)[:num_levels]

        return support_levels, resistance_levels

    @staticmethod
    def determine_trend(df: pd.DataFrame) -> str:
        """
        Determine current trend based on EMAs

        Args:
            df: DataFrame with 'close' column

        Returns:
            "Bullish", "Bearish", or "Sideways"
        """
        ema9 = TechnicalIndicators.calculate_ema(df, 9).iloc[-1]
        ema21 = TechnicalIndicators.calculate_ema(df, 21).iloc[-1]
        ema50 = TechnicalIndicators.calculate_ema(df, 50).iloc[-1]
        close = df['close'].iloc[-1]

        # Strong bullish: price > EMA9 > EMA21 > EMA50
        if close > ema9 > ema21 > ema50:
            return "Bullish"

        # Strong bearish: price < EMA9 < EMA21 < EMA50
        if close < ema9 < ema21 < ema50:
            return "Bearish"

        # Otherwise sideways
        return "Sideways"

    @staticmethod
    def calculate_all(candles: List[Dict]) -> Dict:
        """
        Calculate all indicators at once

        Args:
            candles: List of candle dicts

        Returns:
            Dict with all indicator values:
            {
                "rsi": 58.5,
                "macd": 125.3,
                "macd_signal": 120.1,
                "macd_histogram": 5.2,
                "bb_upper": 68500.0,
                "bb_middle": 68000.0,
                "bb_lower": 67500.0,
                "ema_9": 68200.0,
                "ema_21": 67800.0,
                "ema_50": 67200.0,
                "ema_200": 66000.0,
                "support_levels": [67000.0, 66500.0],
                "resistance_levels": [69000.0, 69500.0],
                "trend": "Bullish"
            }
        """
        if not candles or len(candles) < 50:
            logger.warning("Not enough candles for indicator calculation")
            return {}

        df = TechnicalIndicators.prepare_dataframe(candles)

        # Calculate indicators
        rsi = TechnicalIndicators.calculate_rsi(df)
        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(df)
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(df)
        ema9 = TechnicalIndicators.calculate_ema(df, 9)
        ema21 = TechnicalIndicators.calculate_ema(df, 21)
        ema50 = TechnicalIndicators.calculate_ema(df, 50)
        ema200 = TechnicalIndicators.calculate_ema(df, 200)
        support, resistance = TechnicalIndicators.find_support_resistance(df)
        trend = TechnicalIndicators.determine_trend(df)

        # Return latest values
        return {
            "rsi": round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else None,
            "macd": round(macd_line.iloc[-1], 2) if not pd.isna(macd_line.iloc[-1]) else None,
            "macd_signal": round(signal_line.iloc[-1], 2) if not pd.isna(signal_line.iloc[-1]) else None,
            "macd_histogram": round(histogram.iloc[-1], 2) if not pd.isna(histogram.iloc[-1]) else None,
            "bb_upper": round(bb_upper.iloc[-1], 2) if not pd.isna(bb_upper.iloc[-1]) else None,
            "bb_middle": round(bb_middle.iloc[-1], 2) if not pd.isna(bb_middle.iloc[-1]) else None,
            "bb_lower": round(bb_lower.iloc[-1], 2) if not pd.isna(bb_lower.iloc[-1]) else None,
            "ema_9": round(ema9.iloc[-1], 2) if not pd.isna(ema9.iloc[-1]) else None,
            "ema_21": round(ema21.iloc[-1], 2) if not pd.isna(ema21.iloc[-1]) else None,
            "ema_50": round(ema50.iloc[-1], 2) if not pd.isna(ema50.iloc[-1]) else None,
            "ema_200": round(ema200.iloc[-1], 2) if not pd.isna(ema200.iloc[-1]) else None,
            "support_levels": [round(s, 2) for s in support],
            "resistance_levels": [round(r, 2) for r in resistance],
            "trend": trend
        }