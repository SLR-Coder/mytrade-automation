# utils/common.py
# -*- coding: utf-8 -*-
"""
Common Utilities - Shared functions across all robots
Eliminates code duplication and provides consistent behavior
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("CommonUtils")


def parse_float(value: Optional[Any]) -> Optional[float]:
    """
    Parse float value handling Turkish locale (comma as decimal separator)

    Args:
        value: Value to parse (can be string, number, or None)

    Returns:
        Parsed float value or None if parsing fails

    Examples:
        >>> parse_float("1,234.56")
        1234.56
        >>> parse_float("123,45")
        123.45
        >>> parse_float(None)
        None
    """
    if not value:
        return None

    try:
        # Handle both comma and dot as decimal separators
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


def status_text(robot_no: int, ok: bool) -> str:
    """
    Generate standardized status text for robot

    Args:
        robot_no: Robot number (1-8)
        ok: Success status

    Returns:
        Formatted status string (e.g., "Robot 3 ✅" or "Robot 5 ❌")
    """
    return f"Robot {robot_no} {'✅' if ok else '❌'}"


def get_latest_market_data(ws: Any, cols: Any) -> List[Dict]:
    """
    Read latest market data from Google Sheets after last separator

    This function:
    1. Reads all rows from the worksheet
    2. Finds the last "Ayırıcı" (separator) row
    3. Returns all market data rows after that separator
    4. Parses technical indicators and support/resistance levels

    Args:
        ws: Google Sheets worksheet object
        cols: Column mapping object (from schema.resolve_columns)

    Returns:
        List of market data dictionaries:
        [
            {
                "market": "BTC/USDT",
                "price": 45000.0,
                "indicators": {...},
                "row_index": 15  # 1-based row number in sheet
            },
            ...
        ]
    """
    logger.info("📊 Son piyasa verileri okunuyor...")

    all_rows = ws.get_all_values()
    if len(all_rows) <= 1:
        logger.warning("⚠️ Sheet'te veri yok (sadece header)")
        return []

    # Find last separator row (Column B'de "📊 VERİ TOPLAMA RAPORU")
    separator_idx = None
    for i in range(len(all_rows) - 1, 0, -1):
        if len(all_rows[i]) > cols.B - 1:
            market_value = all_rows[i][cols.B - 1]
            # Check for separator marker in Column B
            if market_value and ("📊" in market_value or "RAPORU" in market_value):
                separator_idx = i
                logger.info(f"✓ Separator bulundu: Satır {i + 1}")
                break

    # Get data rows after separator (or all rows if no separator)
    if separator_idx is None:
        data_rows = all_rows[1:]  # Skip header
        start_index = 2  # Row 2 in sheet (1-based)
    else:
        data_rows = all_rows[separator_idx + 1:]
        start_index = separator_idx + 2  # +2 because 1-based and skip separator

    markets_data = []

    for offset, row in enumerate(data_rows):
        # Skip empty rows
        if len(row) < cols.B:
            continue

        market = row[cols.B - 1] if len(row) > cols.B - 1 else ""
        if not market:
            continue

        # Parse price
        try:
            price_str = row[cols.C - 1] if len(row) > cols.C - 1 and row[cols.C - 1] else "0"
            price = parse_float(price_str) or 0.0
        except:
            price = 0.0

        # Parse technical indicators (Schema: G=RSI, H=MACD, etc.)
        indicators = {}
        try:
            if len(row) > cols.G - 1:
                indicators['rsi'] = parse_float(row[cols.G - 1])
            if len(row) > cols.H - 1:
                indicators['macd'] = parse_float(row[cols.H - 1])
            if len(row) > cols.I - 1:
                indicators['macd_signal'] = parse_float(row[cols.I - 1])
            if len(row) > cols.J - 1:
                indicators['macd_histogram'] = parse_float(row[cols.J - 1])
            if len(row) > cols.K - 1:
                indicators['bb_upper'] = parse_float(row[cols.K - 1])
            if len(row) > cols.L - 1:
                indicators['bb_middle'] = parse_float(row[cols.L - 1])
            if len(row) > cols.M - 1:
                indicators['bb_lower'] = parse_float(row[cols.M - 1])
            if len(row) > cols.N - 1:
                indicators['ema_9'] = parse_float(row[cols.N - 1])
            if len(row) > cols.O - 1:
                indicators['ema_21'] = parse_float(row[cols.O - 1])
            if len(row) > cols.P - 1:
                indicators['ema_50'] = parse_float(row[cols.P - 1])
            if len(row) > cols.Q - 1:
                indicators['ema_200'] = parse_float(row[cols.Q - 1])
            if len(row) > cols.R - 1:
                indicators['support'] = parse_float(row[cols.R - 1])
            if len(row) > cols.S - 1:
                indicators['resistance'] = parse_float(row[cols.S - 1])
            if len(row) > cols.T - 1:
                indicators['trend'] = row[cols.T - 1]

            # Parse support/resistance levels
            support_levels = []
            resistance_levels = []

            if len(row) > cols.Q - 1 and row[cols.Q - 1]:
                val = parse_float(row[cols.Q - 1])
                if val:
                    support_levels.append(val)

            if len(row) > cols.R - 1 and row[cols.R - 1]:
                val = parse_float(row[cols.R - 1])
                if val:
                    resistance_levels.append(val)

            indicators['support_levels'] = support_levels
            indicators['resistance_levels'] = resistance_levels

        except Exception as e:
            logger.warning(f"⚠️ Indicator parse hatası {market}: {e}")

        # Calculate row index (1-based)
        row_index = start_index + offset

        markets_data.append({
            "market": market,
            "price": price,
            "indicators": indicators,
            "row_index": row_index
        })

    logger.info(f"✓ {len(markets_data)} piyasa verisi okundu")
    return markets_data


def get_last_6_batches(ws: Any, cols: Any) -> Dict[str, List[Dict]]:
    """
    Read last 6 batches of market data for temporal trend analysis

    This function reads the last 30 minutes of data (6 batches x 5 min each)
    and returns historical data grouped by market symbol.

    Args:
        ws: Google Sheets worksheet object
        cols: Column mapping object (from schema.resolve_columns)

    Returns:
        Dictionary mapping market symbols to their historical data:
        {
            "BTC/USDT": [
                {"price": 95000, "indicators": {...}, "timestamp": "batch_1"},
                {"price": 95200, "indicators": {...}, "timestamp": "batch_2"},
                ...
            ],
            "EUR/USD": [...],
            ...
        }
    """
    logger.info("📊 Son 6 batch (30 dakika) verisi okunuyor...")

    all_rows = ws.get_all_values()
    if len(all_rows) <= 1:
        logger.warning("⚠️ Sheet'te veri yok")
        return {}

    # Find last 6 separators
    separator_indices = []
    for i in range(len(all_rows) - 1, 0, -1):
        if len(all_rows[i]) > cols.B - 1:
            market_value = all_rows[i][cols.B - 1]
            if market_value and ("📊" in market_value or "RAPORU" in market_value):
                separator_indices.append(i)
                if len(separator_indices) == 6:
                    break

    if not separator_indices:
        logger.warning("⚠️ Hiç separator bulunamadı, sadece son batch okunacak")
        # Fallback to single batch
        latest = get_latest_market_data(ws, cols)
        result = {}
        for item in latest:
            result[item['market']] = [item]
        return result

    # Reverse to get chronological order (oldest to newest)
    separator_indices.reverse()
    logger.info(f"✓ {len(separator_indices)} batch bulundu")

    # Group data by market
    temporal_data = {}

    for batch_idx, sep_idx in enumerate(separator_indices, 1):
        # Determine data range for this batch
        if batch_idx < len(separator_indices):
            next_sep = separator_indices[batch_idx]
            data_rows = all_rows[sep_idx + 1:next_sep]
        else:
            # Last batch - go to end of sheet
            data_rows = all_rows[sep_idx + 1:]

        # Parse each row in this batch
        for row in data_rows:
            if len(row) < cols.B:
                continue

            market = row[cols.B - 1] if len(row) > cols.B - 1 else ""
            if not market or "📊" in market:
                continue

            # Parse price
            try:
                price_str = row[cols.C - 1] if len(row) > cols.C - 1 and row[cols.C - 1] else "0"
                price = parse_float(price_str) or 0.0
            except:
                price = 0.0

            # Parse indicators
            indicators = {}
            try:
                if len(row) > cols.G - 1:
                    indicators['rsi'] = parse_float(row[cols.G - 1])
                if len(row) > cols.H - 1:
                    indicators['macd'] = parse_float(row[cols.H - 1])
                if len(row) > cols.K - 1:
                    indicators['bb_upper'] = parse_float(row[cols.K - 1])
                if len(row) > cols.L - 1:
                    indicators['bb_middle'] = parse_float(row[cols.L - 1])
                if len(row) > cols.M - 1:
                    indicators['bb_lower'] = parse_float(row[cols.M - 1])
                if len(row) > cols.N - 1:
                    indicators['ema_9'] = parse_float(row[cols.N - 1])
                if len(row) > cols.O - 1:
                    indicators['ema_21'] = parse_float(row[cols.O - 1])
                if len(row) > cols.P - 1:
                    indicators['ema_50'] = parse_float(row[cols.P - 1])
                if len(row) > cols.T - 1:
                    indicators['trend'] = row[cols.T - 1]
            except:
                pass

            # Initialize market list if not exists
            if market not in temporal_data:
                temporal_data[market] = []

            # Append batch data
            temporal_data[market].append({
                "price": price,
                "indicators": indicators,
                "batch": batch_idx,
                "timestamp": f"batch_{batch_idx}"
            })

    logger.info(f"✓ {len(temporal_data)} piyasa için temporal veri hazır (her biri {len(separator_indices)} batch)")
    return temporal_data
