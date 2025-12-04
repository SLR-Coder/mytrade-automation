# utils/common.py
# -*- coding: utf-8 -*-
"""
Common Utilities - Shared functions across all robots
Eliminates code duplication and provides consistent behavior
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
import gspread

logger = logging.getLogger("CommonUtils")


# ============================================================================
# GOOGLE SHEETS BATCH UPDATE UTILITIES
# ============================================================================

def batch_update_cells(
    worksheet: gspread.Worksheet,
    updates: List[Tuple[int, int, Any]],
    rate_limit_sleep: float = 0.1
) -> int:
    """
    Batch update multiple cells in Google Sheets with a single API call.

    PERFORMANCE: This is 10-50x faster than individual update_cell() calls!
    Google Sheets API allows up to 100,000 cells per batch.

    Args:
        worksheet: gspread Worksheet object
        updates: List of (row, col, value) tuples
                 row and col are 1-based indices
        rate_limit_sleep: Sleep after batch (default 0.1s)

    Returns:
        Number of cells updated

    Example:
        updates = [
            (2, 5, "BUY"),      # Row 2, Col 5 = "BUY"
            (2, 6, "75%"),      # Row 2, Col 6 = "75%"
            (3, 5, "SELL"),     # Row 3, Col 5 = "SELL"
        ]
        batch_update_cells(ws, updates)
    """
    if not updates:
        return 0

    # Convert to gspread Cell objects
    cells = []
    for row, col, value in updates:
        cell = gspread.Cell(row=row, col=col, value=str(value) if value is not None else "")
        cells.append(cell)

    # Single API call for all updates
    worksheet.update_cells(cells, value_input_option='USER_ENTERED')

    # Rate limiting
    if rate_limit_sleep > 0:
        time.sleep(rate_limit_sleep)

    logger.debug(f"Batch updated {len(cells)} cells")
    return len(cells)


def batch_update_row(
    worksheet: gspread.Worksheet,
    row: int,
    col_values: Dict[int, Any],
    rate_limit_sleep: float = 0.1
) -> int:
    """
    Update multiple columns in a single row with batch update.

    Args:
        worksheet: gspread Worksheet object
        row: Row number (1-based)
        col_values: Dict mapping column number to value
                    {5: "BUY", 6: "75%", 7: "Analysis text"}
        rate_limit_sleep: Sleep after batch

    Returns:
        Number of cells updated

    Example:
        batch_update_row(ws, 2, {
            cols.AS: "BUY",
            cols.AT: "85%",
            cols.AU: "Strong bullish signal"
        })
    """
    updates = [(row, col, value) for col, value in col_values.items()]
    return batch_update_cells(worksheet, updates, rate_limit_sleep)


def batch_update_column(
    worksheet: gspread.Worksheet,
    col: int,
    row_values: Dict[int, Any],
    rate_limit_sleep: float = 0.1
) -> int:
    """
    Update multiple rows in a single column with batch update.

    Args:
        worksheet: gspread Worksheet object
        col: Column number (1-based)
        row_values: Dict mapping row number to value
                    {2: "Robot 1 ✅", 3: "Robot 2 ✅"}
        rate_limit_sleep: Sleep after batch

    Returns:
        Number of cells updated
    """
    updates = [(row, col, value) for row, value in row_values.items()]
    return batch_update_cells(worksheet, updates, rate_limit_sleep)


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


# ============================================================================
# BATCH COUNTER SYSTEM FOR ROBOT 1 → ROBOT 3 WORKFLOW
# ============================================================================
# Robot 1 runs every 5 minutes, Robot 3 runs every 30 minutes
# Robot 1 writes "⏳ Beklemede (X/6)" for batches 1-5
# Robot 1 writes "✅ Analiz Hazır" for batch 6
# Robot 3 only processes rows with "✅ Analiz Hazır"
# ============================================================================

BATCH_SIZE = 6  # 6 x 5 minutes = 30 minutes
BATCH_STATUS_WAITING = "⏳ Beklemede"
BATCH_STATUS_READY = "✅ Analiz Hazır"


def get_batch_number(ws: Any, cols: Any) -> int:
    """
    Get current batch number by counting separators since last "Analiz Hazır"

    Args:
        ws: Google Sheets worksheet object
        cols: Column mapping object

    Returns:
        Current batch number (1-6)
    """
    try:
        # Read last 50 rows to find batch status
        all_rows = ws.get_all_values()
        if len(all_rows) <= 1:
            return 1  # First batch

        # Count separators (VERİ TOPLAMA RAPORU) since last "Analiz Hazır"
        count = 0
        for i in range(len(all_rows) - 1, 0, -1):
            row = all_rows[i]

            # Check if this is a separator row
            if len(row) > cols.B - 1:
                market_value = row[cols.B - 1]
                if market_value and ("📊" in market_value or "RAPORU" in market_value):
                    # Check BK column for status (Robot 1 - YENİ SCHEMA)
                    if len(row) > cols.BK - 1:
                        status = row[cols.BK - 1]
                        if BATCH_STATUS_READY in str(status):
                            # Found last "Analiz Hazır", return count + 1
                            return min(count + 1, BATCH_SIZE)
                    count += 1

                    # Safety limit - don't count more than BATCH_SIZE
                    if count >= BATCH_SIZE:
                        return BATCH_SIZE

        # No "Analiz Hazır" found, return count + 1
        return min(count + 1, BATCH_SIZE)

    except Exception as e:
        logger.warning(f"Batch number hesaplanamadı: {e}, varsayılan 1 kullanılıyor")
        return 1


def batch_status_text(batch_number: int) -> str:
    """
    Generate batch status text for Robot 1

    Args:
        batch_number: Current batch number (1-6)

    Returns:
        "⏳ Beklemede (X/6)" for batches 1-5
        "✅ Analiz Hazır" for batch 6
    """
    if batch_number >= BATCH_SIZE:
        return BATCH_STATUS_READY
    else:
        return f"{BATCH_STATUS_WAITING} ({batch_number}/{BATCH_SIZE})"


def is_ready_for_analysis(status: str) -> bool:
    """
    Check if a row is ready for Robot 3 analysis

    Args:
        status: Status text from AU column

    Returns:
        True if row has "✅ Analiz Hazır" status
    """
    return BATCH_STATUS_READY in str(status) if status else False


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

            # Parse SMC indicators (U-AF columns)
            if len(row) > cols.U - 1:
                indicators['fvg_status'] = row[cols.U - 1] if row[cols.U - 1] != "-" else None
            if len(row) > cols.V - 1:
                indicators['fvg_range'] = row[cols.V - 1] if row[cols.V - 1] != "-" else None
            if len(row) > cols.W - 1:
                indicators['liquidity_sweep'] = row[cols.W - 1] if row[cols.W - 1] != "-" else None
            if len(row) > cols.X - 1:
                indicators['sweep_level'] = row[cols.X - 1] if row[cols.X - 1] != "-" else None
            if len(row) > cols.Y - 1:
                indicators['rsi_divergence'] = row[cols.Y - 1] if row[cols.Y - 1] != "-" else None
            if len(row) > cols.Z - 1:
                indicators['structure_break'] = row[cols.Z - 1] if row[cols.Z - 1] != "-" else None
            if len(row) > cols.AA - 1:
                indicators['swing_high'] = parse_float(row[cols.AA - 1])
            if len(row) > cols.AB - 1:
                indicators['swing_low'] = parse_float(row[cols.AB - 1])
            if len(row) > cols.AC - 1:
                indicators['adr_pips'] = row[cols.AC - 1] if row[cols.AC - 1] != "-" else None
            if len(row) > cols.AD - 1:
                indicators['adr_exhaustion'] = row[cols.AD - 1] if row[cols.AD - 1] != "-" else None
            if len(row) > cols.AE - 1:
                indicators['htf_trend'] = row[cols.AE - 1] if row[cols.AE - 1] != "-" else None
            if len(row) > cols.AF - 1:
                indicators['session'] = row[cols.AF - 1] if row[cols.AF - 1] != "-" else None

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


def analyze_temporal_trend(batches: List[Dict]) -> Dict:
    """
    Analyze temporal trend from 6 batches of data (30 minutes)

    This is the SINGLE SOURCE OF TRUTH for temporal trend analysis.
    Used by Robot 3, Robot 5, and Robot 8.

    Args:
        batches: List of batch data (oldest to newest)
                 Each batch: {"price": float, "indicators": dict, ...}

    Returns:
        Dictionary with trend statistics:
        {
            "available": True/False,
            "price_change_pct": float,
            "momentum": str,
            "consistency": str,
            "start_price": float,
            "end_price": float,
            "summary": str  # Human-readable summary
        }
    """
    if not batches or len(batches) < 2:
        return {
            "available": False,
            "price_change_pct": 0,
            "momentum": "YETERSİZ VERİ",
            "consistency": "0/0",
            "summary": "İlk veri - trend analizi yok"
        }

    prices = [b['price'] for b in batches if b.get('price', 0) > 0]
    if len(prices) < 2:
        return {
            "available": False,
            "price_change_pct": 0,
            "momentum": "YETERSİZ VERİ",
            "consistency": "0/0",
            "summary": "Yetersiz fiyat verisi"
        }

    # Calculate price movement
    start_price = prices[0]
    end_price = prices[-1]
    price_change_pct = ((end_price - start_price) / start_price) * 100

    # Calculate momentum (last 3 vs first 3)
    if len(prices) >= 6:
        first_half_avg = sum(prices[:3]) / 3
        second_half_avg = sum(prices[3:]) / 3

        if second_half_avg > first_half_avg * 1.01:
            momentum = "GÜÇLÜ YUKARI ⬆️"
        elif second_half_avg < first_half_avg * 0.99:
            momentum = "GÜÇLÜ AŞAĞI ⬇️"
        else:
            momentum = "NÖTR ➡️"
    else:
        if end_price > start_price:
            momentum = "YUKARI ⬆️"
        elif end_price < start_price:
            momentum = "AŞAĞI ⬇️"
        else:
            momentum = "NÖTR ➡️"

    # Count upward movements
    up_count = sum(1 for i in range(1, len(prices)) if prices[i] > prices[i-1])
    consistency = f"{up_count}/{len(prices)-1}"

    # Human-readable summary
    summary = f"Son 30 dk: Fiyat {price_change_pct:+.2f}%, Momentum: {momentum}, Tutarlılık: {consistency} yukarı"

    return {
        "available": True,
        "price_change_pct": price_change_pct,
        "momentum": momentum,
        "consistency": consistency,
        "start_price": start_price,
        "end_price": end_price,
        "summary": summary
    }
