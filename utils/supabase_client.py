# utils/supabase_client.py
# -*- coding: utf-8 -*-
"""
Supabase client for MyTrade automation
Provides database operations for all robots
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

logger = logging.getLogger("Supabase")

# Lazy initialization
_supabase_client = None


def get_supabase():
    """Get or create Supabase client (singleton pattern)"""
    global _supabase_client

    if _supabase_client is None:
        from supabase import create_client, Client
        from utils.secrets import get_secret

        url = get_secret("SUPABASE_URL", required=True)
        key = get_secret("SUPABASE_SERVICE_ROLE_KEY", required=True)

        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialized")

    return _supabase_client


def generate_batch_id() -> str:
    """Generate batch ID based on current 30-minute window

    Format: 2025-12-06_14:00 or 2025-12-06_14:30
    """
    now = datetime.now()
    minute = 0 if now.minute < 30 else 30
    return now.strftime(f"%Y-%m-%d_%H:{minute:02d}")


def get_batch_sequence() -> int:
    """Get current batch sequence (1-6) within 30-minute window

    :00-:04 → 1
    :05-:09 → 2
    :10-:14 → 3
    :15-:19 → 4
    :20-:24 → 5
    :25-:29 → 6
    :30-:34 → 1
    ...
    """
    now = datetime.now()
    minute_in_window = now.minute % 30
    return (minute_in_window // 5) + 1


def get_processing_status(batch_sequence: int) -> str:
    """Get processing status based on batch sequence

    Sequence 1-5: pending (waiting for more data)
    Sequence 6: ready_for_analysis (30 min data complete)
    """
    return "ready_for_analysis" if batch_sequence == 6 else "pending"


# ============================================
# ROBOT 1: Market Harvester
# ============================================

def insert_signal(data: Dict[str, Any]) -> Optional[Dict]:
    """Insert a new signal row (Robot 1)

    Args:
        data: Signal data including market, price, indicators, etc.

    Returns:
        Inserted row or None on error
    """
    try:
        supabase = get_supabase()

        # Add batch_id if not provided
        if "batch_id" not in data:
            data["batch_id"] = generate_batch_id()

        # Convert Decimal to float for JSON serialization
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)

        result = supabase.table("signals").insert(data).execute()

        if result.data:
            logger.info(f"Inserted signal: {data.get('market')} batch={data.get('batch_id')}")
            return result.data[0]
        return None

    except Exception as e:
        # Handle duplicate - update instead
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            logger.info(f"Signal exists, updating: {data.get('market')}")
            return update_signal_by_batch(
                data.get("batch_id"),
                data.get("market"),
                data
            )
        logger.error(f"Error inserting signal: {e}")
        return None


def insert_signals_batch(signals: List[Dict[str, Any]]) -> int:
    """Insert multiple signals at once (Robot 1)

    Args:
        signals: List of signal data dictionaries

    Returns:
        Number of successfully inserted signals
    """
    try:
        supabase = get_supabase()
        batch_id = generate_batch_id()
        batch_sequence = get_batch_sequence()

        # Prepare all signals
        for signal in signals:
            if "batch_id" not in signal:
                signal["batch_id"] = batch_id
            if "batch_sequence" not in signal:
                signal["batch_sequence"] = batch_sequence
            # Convert Decimal to float
            for key, value in signal.items():
                if isinstance(value, Decimal):
                    signal[key] = float(value)

        # Use upsert to handle duplicates (batch_id + batch_sequence + market)
        result = supabase.table("signals").upsert(
            signals,
            on_conflict="batch_id,batch_sequence,market"
        ).execute()

        count = len(result.data) if result.data else 0
        logger.info(f"Inserted/updated {count} signals for batch {batch_id} seq {batch_sequence}")
        return count

    except Exception as e:
        logger.error(f"Error batch inserting signals: {e}")
        return 0


# ============================================
# ROBOT 2: News Analyzer
# ============================================

def insert_news(data: Dict[str, Any]) -> Optional[Dict]:
    """Insert a news item (Robot 2)"""
    try:
        supabase = get_supabase()
        result = supabase.table("news").insert(data).execute()

        if result.data:
            logger.info(f"Inserted news: {data.get('title', '')[:50]}...")
            return result.data[0]
        return None

    except Exception as e:
        if "duplicate key" in str(e).lower():
            logger.debug(f"News already exists: {data.get('title', '')[:30]}...")
            return None
        logger.error(f"Error inserting news: {e}")
        return None


def get_recent_news_titles(limit: int = 100) -> List[str]:
    """Get recent news titles for duplicate checking"""
    try:
        supabase = get_supabase()
        result = supabase.table("news").select("title").order(
            "created_at", desc=True
        ).limit(limit).execute()

        return [row["title"] for row in result.data] if result.data else []

    except Exception as e:
        logger.error(f"Error getting news titles: {e}")
        return []


def mark_news_sent(news_id: int, message_id: str) -> bool:
    """Mark news as sent to Telegram"""
    try:
        supabase = get_supabase()
        supabase.table("news").update({
            "telegram_sent": True,
            "telegram_message_id": message_id
        }).eq("id", news_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error marking news sent: {e}")
        return False


# ============================================
# ROBOT 3, 8: AI Analysis (Polling Mode)
# ============================================

def get_batches_ready_for_analysis() -> List[str]:
    """Get batch_ids that are ready for analysis (have sequence 6)

    Returns:
        List of batch_ids ready for Robot 3/8
    """
    try:
        supabase = get_supabase()

        # Find batches with sequence 6 (complete 30-min data)
        result = supabase.table("signals").select("batch_id").eq(
            "batch_sequence", 6
        ).eq(
            "processing_status", "ready_for_analysis"
        ).execute()

        if not result.data:
            return []

        # Get unique batch_ids
        batch_ids = list(set(row["batch_id"] for row in result.data))
        logger.info(f"Found {len(batch_ids)} batches ready for analysis")
        return batch_ids

    except Exception as e:
        logger.error(f"Error getting ready batches: {e}")
        return []


def get_market_history(batch_id: str, market: str) -> List[Dict]:
    """Get all 6 sequences for a market within a batch (30-min trend data)

    Args:
        batch_id: Batch ID (e.g., "2025-12-06_14:00")
        market: Market symbol (e.g., "BTC/USDT")

    Returns:
        List of 6 signal rows ordered by sequence
    """
    try:
        supabase = get_supabase()

        result = supabase.table("signals").select("*").eq(
            "batch_id", batch_id
        ).eq(
            "market", market
        ).order("batch_sequence").execute()

        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Error getting market history: {e}")
        return []


def get_markets_in_batch(batch_id: str) -> List[str]:
    """Get all unique markets in a batch

    Args:
        batch_id: Batch ID

    Returns:
        List of market symbols
    """
    try:
        supabase = get_supabase()

        result = supabase.table("signals").select("market").eq(
            "batch_id", batch_id
        ).eq("batch_sequence", 6).execute()

        if not result.data:
            return []

        return list(set(row["market"] for row in result.data))

    except Exception as e:
        logger.error(f"Error getting markets in batch: {e}")
        return []


def get_unanalyzed_batches(robot_number: int) -> List[Dict]:
    """Get batches ready for analysis but not yet processed by this robot

    Args:
        robot_number: Robot number (3 or 8)

    Returns:
        List of {batch_id, markets} dicts
    """
    try:
        supabase = get_supabase()
        status_column = f"robot{robot_number}_status"

        # Find sequence 6 rows that are ready but not analyzed
        result = supabase.table("signals").select("batch_id, market").eq(
            "batch_sequence", 6
        ).eq(
            "processing_status", "ready_for_analysis"
        ).is_(status_column, "null").execute()

        if not result.data:
            return []

        # Group by batch_id
        batches = {}
        for row in result.data:
            bid = row["batch_id"]
            if bid not in batches:
                batches[bid] = []
            batches[bid].append(row["market"])

        return [{"batch_id": bid, "markets": markets} for bid, markets in batches.items()]

    except Exception as e:
        logger.error(f"Error getting unanalyzed batches: {e}")
        return []


def update_batch_analysis(batch_id: str, market: str, robot_number: int, data: Dict) -> bool:
    """Update all 6 sequences for a market with analysis results

    Args:
        batch_id: Batch ID
        market: Market symbol
        robot_number: Robot number (3 or 8)
        data: Analysis results

    Returns:
        Success boolean
    """
    try:
        supabase = get_supabase()

        # Add status
        data[f"robot{robot_number}_status"] = "completed"
        data[f"robot{robot_number}_completed_at"] = datetime.now().isoformat()

        # Update all sequences for this market in this batch
        supabase.table("signals").update(data).eq(
            "batch_id", batch_id
        ).eq("market", market).execute()

        logger.info(f"Robot {robot_number} updated {market} in batch {batch_id}")
        return True

    except Exception as e:
        logger.error(f"Error updating batch analysis: {e}")
        return False


def get_pending_for_robot(robot_number: int, limit: int = 50) -> List[Dict]:
    """Get signals pending for a specific robot

    Args:
        robot_number: Robot number (3, 8, 7, 4, 5)
        limit: Max rows to return

    Returns:
        List of pending signal rows
    """
    try:
        supabase = get_supabase()
        status_column = f"robot{robot_number}_status"

        # Build query based on robot dependencies
        query = supabase.table("signals").select("*")

        # Robot 3 & 8: Need robot1 completed
        if robot_number in [3, 8]:
            query = query.eq("robot1_status", "completed")

        # Robot 7: Needs robot3 AND robot8 completed
        elif robot_number == 7:
            query = query.eq("robot3_status", "completed").eq("robot8_status", "completed")

        # Robot 4: Needs robot7 completed AND has signal
        elif robot_number == 4:
            query = query.eq("robot7_status", "completed").neq("final_signal", None)

        # Robot 5: Needs robot4 completed (chart ready)
        elif robot_number == 5:
            query = query.eq("robot4_status", "completed")

        # Filter for pending status
        query = query.is_(status_column, "null")

        result = query.order("created_at", desc=True).limit(limit).execute()

        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Error getting pending for robot {robot_number}: {e}")
        return []


def update_robot_status(
    signal_id: int,
    robot_number: int,
    data: Dict[str, Any],
    status: str = "completed"
) -> bool:
    """Update signal with robot's analysis results

    Args:
        signal_id: Signal row ID
        robot_number: Robot number
        data: Analysis results to save
        status: Status to set (default: completed)

    Returns:
        Success boolean
    """
    try:
        supabase = get_supabase()

        # Add status and timestamp
        data[f"robot{robot_number}_status"] = status
        data[f"robot{robot_number}_completed_at"] = datetime.now().isoformat()

        # Convert Decimal to float
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)

        supabase.table("signals").update(data).eq("id", signal_id).execute()
        logger.info(f"Robot {robot_number} updated signal {signal_id}: {status}")
        return True

    except Exception as e:
        logger.error(f"Error updating robot {robot_number} status: {e}")
        return False


def update_signal_by_batch(batch_id: str, market: str, data: Dict[str, Any]) -> Optional[Dict]:
    """Update signal by batch_id and market"""
    try:
        supabase = get_supabase()

        # Convert Decimal to float
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)

        result = supabase.table("signals").update(data).eq(
            "batch_id", batch_id
        ).eq("market", market).execute()

        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Error updating signal by batch: {e}")
        return None


# ============================================
# ROBOT 5: Telegram Publisher
# ============================================

def get_signals_to_publish(limit: int = 20) -> List[Dict]:
    """Get signals ready for Telegram publishing"""
    try:
        supabase = get_supabase()

        result = supabase.table("signals").select("*").eq(
            "robot4_status", "completed"
        ).is_("robot5_status", "null").neq(
            "final_signal", None
        ).order("created_at", desc=True).limit(limit).execute()

        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Error getting signals to publish: {e}")
        return []


def mark_signal_published(signal_id: int, message_id: str) -> bool:
    """Mark signal as published to Telegram"""
    return update_robot_status(signal_id, 5, {
        "telegram_message_id": message_id
    })


# ============================================
# ROBOT 9: TP/SL Monitor
# ============================================

def get_open_positions() -> List[Dict]:
    """Get signals with open positions to monitor"""
    try:
        supabase = get_supabase()

        result = supabase.table("signals").select("*").eq(
            "robot5_status", "completed"
        ).in_("position_status", ["PENDING", "OPEN", "TP1_HIT"]).execute()

        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Error getting open positions: {e}")
        return []


def update_position_status(signal_id: int, status: str, hit_time: Optional[datetime] = None) -> bool:
    """Update position status (TP1_HIT, TP2_HIT, SL_HIT, etc.)"""
    try:
        supabase = get_supabase()

        data = {
            "position_status": status,
            "robot9_last_check": datetime.now().isoformat()
        }

        # Add hit timestamp
        if hit_time and status == "TP1_HIT":
            data["tp1_hit_at"] = hit_time.isoformat()
        elif hit_time and status == "TP2_HIT":
            data["tp2_hit_at"] = hit_time.isoformat()
        elif hit_time and status == "SL_HIT":
            data["sl_hit_at"] = hit_time.isoformat()

        supabase.table("signals").update(data).eq("id", signal_id).execute()
        logger.info(f"Position {signal_id} status: {status}")
        return True

    except Exception as e:
        logger.error(f"Error updating position status: {e}")
        return False


# ============================================
# UTILITY FUNCTIONS
# ============================================

def get_batch_summary(batch_id: str) -> Dict[str, Any]:
    """Get summary of a batch's processing status"""
    try:
        supabase = get_supabase()

        result = supabase.table("signals").select("*").eq("batch_id", batch_id).execute()

        if not result.data:
            return {"batch_id": batch_id, "total": 0}

        signals = result.data
        return {
            "batch_id": batch_id,
            "total": len(signals),
            "robot1_done": sum(1 for s in signals if s.get("robot1_status") == "completed"),
            "robot3_done": sum(1 for s in signals if s.get("robot3_status") == "completed"),
            "robot8_done": sum(1 for s in signals if s.get("robot8_status") == "completed"),
            "robot7_done": sum(1 for s in signals if s.get("robot7_status") == "completed"),
            "robot4_done": sum(1 for s in signals if s.get("robot4_status") == "completed"),
            "robot5_done": sum(1 for s in signals if s.get("robot5_status") == "completed"),
        }

    except Exception as e:
        logger.error(f"Error getting batch summary: {e}")
        return {"batch_id": batch_id, "error": str(e)}


def test_connection() -> bool:
    """Test Supabase connection"""
    try:
        supabase = get_supabase()
        # Simple query to test connection
        result = supabase.table("signals").select("id").limit(1).execute()
        logger.info("Supabase connection test: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"Supabase connection test FAILED: {e}")
        return False
