# utils/monitoring.py
# -*- coding: utf-8 -*-
"""
Robot Monitoring Dashboard for Google Sheets
Provides visibility into robot execution status
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
import pytz

logger = logging.getLogger("Monitoring")

# Monitoring sheet tab name
MONITOR_TAB = "RobotMonitor"

# Column indices for monitoring sheet (1-based)
MONITOR_COLS = {
    "batch_id": 1,      # A: Batch ID (2025-12-06_10:30)
    "timestamp": 2,     # B: Timestamp
    "r1_status": 3,     # C: Robot 1 Status
    "r1_detail": 4,     # D: Robot 1 Detail
    "r2_status": 5,     # E: Robot 2 Status
    "r2_detail": 6,     # F: Robot 2 Detail
    "r3_status": 7,     # G: Robot 3 Status
    "r3_detail": 8,     # H: Robot 3 Detail
    "r8_status": 9,     # I: Robot 8 Status
    "r8_detail": 10,    # J: Robot 8 Detail
    "r7_status": 11,    # K: Robot 7 Status
    "r7_detail": 12,    # L: Robot 7 Detail
    "r4_status": 13,    # M: Robot 4 Status
    "r4_detail": 14,    # N: Robot 4 Detail
    "r5_status": 15,    # O: Robot 5 Status
    "r5_detail": 16,    # P: Robot 5 Detail
    "r9_status": 17,    # Q: Robot 9 Status
    "r9_detail": 18,    # R: Robot 9 Detail
    "total": 19,        # S: Total Status (e.g., "5/7 ✅")
    "errors": 20,       # T: Errors summary
}

# Status icons
STATUS_OK = "✅"
STATUS_ERROR = "❌"
STATUS_WARNING = "⚠️"
STATUS_RUNNING = "⏳"
STATUS_PENDING = "⏸️"
STATUS_SKIP = "➖"


def get_turkey_time() -> datetime:
    """Get current time in Turkey timezone"""
    turkey_tz = pytz.timezone('Europe/Istanbul')
    return datetime.now(turkey_tz)


def generate_batch_id() -> str:
    """Generate batch ID based on current 30-minute window"""
    now = get_turkey_time()
    minute = 0 if now.minute < 30 else 30
    return now.strftime(f"%Y-%m-%d_%H:{minute:02d}")


def format_status(success: bool, count: int, detail: str = "") -> tuple:
    """
    Format robot status for monitoring sheet

    Returns:
        (status_icon, detail_text)
    """
    if success:
        icon = f"{STATUS_OK} {count}"
    elif count == 0:
        icon = f"{STATUS_WARNING} 0"
    else:
        icon = f"{STATUS_ERROR} {count}"

    return icon, detail


def get_or_create_monitor_sheet(gc, sheet_id: str):
    """
    Get or create the RobotMonitor tab

    Args:
        gc: gspread client
        sheet_id: Spreadsheet ID

    Returns:
        Worksheet object
    """
    try:
        spreadsheet = gc.open_by_key(sheet_id)

        # Try to get existing tab
        try:
            ws = spreadsheet.worksheet(MONITOR_TAB)
            logger.info(f"Found existing {MONITOR_TAB} tab")
            return ws
        except:
            pass

        # Create new tab
        ws = spreadsheet.add_worksheet(title=MONITOR_TAB, rows=1000, cols=25)

        # Add header row
        headers = [
            "Batch ID", "Timestamp",
            "R1 Status", "R1 Detail",
            "R2 Status", "R2 Detail",
            "R3 Status", "R3 Detail",
            "R8 Status", "R8 Detail",
            "R7 Status", "R7 Detail",
            "R4 Status", "R4 Detail",
            "R5 Status", "R5 Detail",
            "R9 Status", "R9 Detail",
            "Total", "Errors"
        ]
        ws.append_row(headers)

        logger.info(f"Created new {MONITOR_TAB} tab with headers")
        return ws

    except Exception as e:
        logger.error(f"Error getting/creating monitor sheet: {e}")
        raise


def find_batch_row(ws, batch_id: str) -> Optional[int]:
    """
    Find the row number for a specific batch ID

    Returns:
        Row number (1-based) or None if not found
    """
    try:
        # Get all batch IDs (column A)
        batch_ids = ws.col_values(MONITOR_COLS["batch_id"])

        for i, bid in enumerate(batch_ids):
            if bid == batch_id:
                return i + 1  # 1-based row number

        return None
    except Exception as e:
        logger.error(f"Error finding batch row: {e}")
        return None


def update_robot_status(
    gc,
    sheet_id: str,
    robot_number: int,
    success: bool,
    count: int,
    detail: str = "",
    error: str = ""
) -> bool:
    """
    Update robot status in the monitoring sheet

    Args:
        gc: gspread client
        sheet_id: Spreadsheet ID
        robot_number: Robot number (1-9)
        success: Whether robot succeeded
        count: Number of items processed
        detail: Detail message (e.g., "24 markets collected")
        error: Error message if failed

    Returns:
        Success boolean
    """
    try:
        ws = get_or_create_monitor_sheet(gc, sheet_id)
        batch_id = generate_batch_id()
        now = get_turkey_time()

        # Find or create row for this batch
        row_num = find_batch_row(ws, batch_id)

        if row_num is None:
            # Create new row
            new_row = [""] * 20
            new_row[MONITOR_COLS["batch_id"] - 1] = batch_id
            new_row[MONITOR_COLS["timestamp"] - 1] = now.strftime("%H:%M:%S")
            ws.append_row(new_row)

            # Get the new row number
            row_num = len(ws.col_values(MONITOR_COLS["batch_id"]))

        # Determine status column based on robot number
        status_col_map = {
            1: "r1_status", 2: "r2_status", 3: "r3_status",
            4: "r4_status", 5: "r5_status", 7: "r7_status",
            8: "r8_status", 9: "r9_status"
        }
        detail_col_map = {
            1: "r1_detail", 2: "r2_detail", 3: "r3_detail",
            4: "r4_detail", 5: "r5_detail", 7: "r7_detail",
            8: "r8_detail", 9: "r9_detail"
        }

        if robot_number not in status_col_map:
            logger.error(f"Invalid robot number: {robot_number}")
            return False

        status_col = MONITOR_COLS[status_col_map[robot_number]]
        detail_col = MONITOR_COLS[detail_col_map[robot_number]]

        # Format status
        if success:
            status_text = f"{STATUS_OK} {count}"
        elif error:
            status_text = f"{STATUS_ERROR} {count}"
        else:
            status_text = f"{STATUS_WARNING} {count}"

        # Build detail text
        if error:
            detail_text = f"❌ {error[:50]}"
        elif detail:
            detail_text = detail[:50]
        elif count == 0:
            detail_text = "Veri bulunamadı"
        else:
            detail_text = f"{count} işlendi"

        # Update cells
        ws.update_cell(row_num, status_col, status_text)
        ws.update_cell(row_num, detail_col, detail_text)

        # Update timestamp
        ws.update_cell(row_num, MONITOR_COLS["timestamp"], now.strftime("%H:%M:%S"))

        # Update total count
        update_total_status(ws, row_num)

        logger.info(f"Updated Robot {robot_number} status: {status_text} - {detail_text}")
        return True

    except Exception as e:
        logger.error(f"Error updating robot status: {e}")
        return False


def update_total_status(ws, row_num: int):
    """Update the total status column for a row"""
    try:
        # Get all status cells for this row
        row_data = ws.row_values(row_num)

        success_count = 0
        total_count = 0
        errors = []

        # Check each robot status (columns C, E, G, I, K, M, O, Q)
        status_cols = [
            MONITOR_COLS["r1_status"],
            MONITOR_COLS["r2_status"],
            MONITOR_COLS["r3_status"],
            MONITOR_COLS["r8_status"],
            MONITOR_COLS["r7_status"],
            MONITOR_COLS["r4_status"],
            MONITOR_COLS["r5_status"],
            MONITOR_COLS["r9_status"],
        ]

        for col in status_cols:
            if col <= len(row_data) and row_data[col - 1]:
                total_count += 1
                if STATUS_OK in row_data[col - 1]:
                    success_count += 1
                elif STATUS_ERROR in row_data[col - 1]:
                    # Get robot number from column
                    robot_names = {
                        MONITOR_COLS["r1_status"]: "R1",
                        MONITOR_COLS["r2_status"]: "R2",
                        MONITOR_COLS["r3_status"]: "R3",
                        MONITOR_COLS["r8_status"]: "R8",
                        MONITOR_COLS["r7_status"]: "R7",
                        MONITOR_COLS["r4_status"]: "R4",
                        MONITOR_COLS["r5_status"]: "R5",
                        MONITOR_COLS["r9_status"]: "R9",
                    }
                    errors.append(robot_names.get(col, f"R{col}"))

        # Format total
        if total_count == 0:
            total_text = STATUS_PENDING
        elif success_count == total_count:
            total_text = f"{STATUS_OK} {success_count}/{total_count}"
        else:
            total_text = f"{STATUS_WARNING} {success_count}/{total_count}"

        # Format errors
        error_text = ", ".join(errors) if errors else ""

        ws.update_cell(row_num, MONITOR_COLS["total"], total_text)
        ws.update_cell(row_num, MONITOR_COLS["errors"], error_text)

    except Exception as e:
        logger.error(f"Error updating total status: {e}")


def log_robot_start(
    gc,
    sheet_id: str,
    robot_number: int
) -> bool:
    """Log that a robot has started running"""
    try:
        ws = get_or_create_monitor_sheet(gc, sheet_id)
        batch_id = generate_batch_id()
        now = get_turkey_time()

        # Find or create row for this batch
        row_num = find_batch_row(ws, batch_id)

        if row_num is None:
            # Create new row
            new_row = [""] * 20
            new_row[MONITOR_COLS["batch_id"] - 1] = batch_id
            new_row[MONITOR_COLS["timestamp"] - 1] = now.strftime("%H:%M:%S")
            ws.append_row(new_row)
            row_num = len(ws.col_values(MONITOR_COLS["batch_id"]))

        # Determine status column
        status_col_map = {
            1: "r1_status", 2: "r2_status", 3: "r3_status",
            4: "r4_status", 5: "r5_status", 7: "r7_status",
            8: "r8_status", 9: "r9_status"
        }

        if robot_number in status_col_map:
            status_col = MONITOR_COLS[status_col_map[robot_number]]
            ws.update_cell(row_num, status_col, STATUS_RUNNING)

        return True

    except Exception as e:
        logger.error(f"Error logging robot start: {e}")
        return False
