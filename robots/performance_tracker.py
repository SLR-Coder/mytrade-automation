# -*- coding: utf-8 -*-
"""
Robot 6: Performance Tracker
Tracks signal success and calculates performance metrics
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from typing import Dict, Optional

from core.database import get_db_session, init_database, close_database
from data.models.signals import SignalModel
from data.models.performance import PerformanceModel
from data.models.market_data import MarketDataModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot-6-PerformanceTracker")


class PerformanceTracker:
    """Track and calculate signal performance metrics"""

    def __init__(self):
        """Initialize performance tracker"""
        logger.info("PerformanceTracker initialized")

    async def update_signal_outcomes(self):
        """
        Update signal outcomes by checking if TP or SL was hit

        This is a simplified version - checks current price vs TP/SL
        """
        logger.info("📊 Updating signal outcomes...")

        updated_count = 0

        async with get_db_session() as session:
            # Get pending signals
            result = await session.execute(
                select(SignalModel)
                .where(SignalModel.actual_outcome == "pending")
                .order_by(SignalModel.time.desc())
                .limit(100)  # Process last 100 pending signals
            )

            signals = result.scalars().all()

            logger.info(f"Found {len(signals)} pending signals to check")

            for signal in signals:
                try:
                    # Get latest market data for this market
                    market_result = await session.execute(
                        select(MarketDataModel)
                        .where(MarketDataModel.market == signal.market)
                        .order_by(MarketDataModel.time.desc())
                        .limit(1)
                    )

                    market_data = market_result.scalar_one_or_none()

                    if not market_data:
                        continue

                    current_price = float(market_data.close)
                    entry_price = signal.entry_price
                    stop_loss = signal.stop_loss
                    tp1 = signal.take_profit_1
                    tp2 = signal.take_profit_2

                    # Check outcomes
                    if signal.signal == "BUY":
                        if stop_loss and current_price <= stop_loss:
                            signal.actual_outcome = "hit_sl"
                            signal.actual_pnl_percent = ((current_price - entry_price) / entry_price) * 100
                            signal.closed_at = market_data.time
                            updated_count += 1
                        elif tp2 and current_price >= tp2:
                            signal.actual_outcome = "hit_tp2"
                            signal.actual_pnl_percent = ((current_price - entry_price) / entry_price) * 100
                            signal.closed_at = market_data.time
                            updated_count += 1
                        elif tp1 and current_price >= tp1:
                            signal.actual_outcome = "hit_tp1"
                            signal.actual_pnl_percent = ((current_price - entry_price) / entry_price) * 100
                            signal.closed_at = market_data.time
                            updated_count += 1

                    elif signal.signal == "SELL":
                        if stop_loss and current_price >= stop_loss:
                            signal.actual_outcome = "hit_sl"
                            signal.actual_pnl_percent = ((entry_price - current_price) / entry_price) * 100
                            signal.closed_at = market_data.time
                            updated_count += 1
                        elif tp2 and current_price <= tp2:
                            signal.actual_outcome = "hit_tp2"
                            signal.actual_pnl_percent = ((entry_price - current_price) / entry_price) * 100
                            signal.closed_at = market_data.time
                            updated_count += 1
                        elif tp1 and current_price <= tp1:
                            signal.actual_outcome = "hit_tp1"
                            signal.actual_pnl_percent = ((entry_price - current_price) / entry_price) * 100
                            signal.closed_at = market_data.time
                            updated_count += 1

                except Exception as e:
                    logger.error(f"Error processing signal {signal.id}: {e}")
                    continue

        logger.info(f"✓ Updated {updated_count} signal outcomes")
        return updated_count

    async def calculate_period_performance(
        self,
        period: str = "weekly",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Calculate performance metrics for a period

        Args:
            period: "daily", "weekly", "monthly"
            start_date: Period start (default: auto-calculate)
            end_date: Period end (default: now)

        Returns:
            Performance metrics dict
        """
        logger.info(f"📈 Calculating {period} performance...")

        if end_date is None:
            end_date = datetime.utcnow()

        if start_date is None:
            if period == "daily":
                start_date = end_date - timedelta(days=1)
            elif period == "weekly":
                start_date = end_date - timedelta(days=7)
            elif period == "monthly":
                start_date = end_date - timedelta(days=30)

        async with get_db_session() as session:
            # Get signals in period
            result = await session.execute(
                select(SignalModel)
                .where(and_(
                    SignalModel.time >= start_date,
                    SignalModel.time <= end_date,
                    SignalModel.signal.in_(["BUY", "SELL"])  # Exclude HOLD
                ))
            )

            signals = result.scalars().all()

            total_signals = len(signals)
            successful_signals = len([s for s in signals if s.actual_outcome in ["hit_tp1", "hit_tp2"]])
            failed_signals = len([s for s in signals if s.actual_outcome == "hit_sl"])
            pending_signals = len([s for s in signals if s.actual_outcome == "pending"])

            # Calculate metrics
            win_rate = (successful_signals / total_signals * 100) if total_signals > 0 else 0.0

            # Calculate P&L
            profits = [s.actual_pnl_percent for s in signals if s.actual_pnl_percent and s.actual_pnl_percent > 0]
            losses = [s.actual_pnl_percent for s in signals if s.actual_pnl_percent and s.actual_pnl_percent < 0]

            avg_profit = (sum(profits) / len(profits)) if profits else 0.0
            avg_loss = (sum(losses) / len(losses)) if losses else 0.0

            profit_factor = abs(sum(profits) / sum(losses)) if losses and sum(losses) != 0 else 0.0

            best_trade = max(profits) if profits else 0.0
            worst_trade = min(losses) if losses else 0.0

            # Calculate consecutive streaks
            consecutive_wins = 0
            consecutive_losses = 0
            max_consecutive_wins = 0
            max_consecutive_losses = 0

            for signal in sorted(signals, key=lambda x: x.time):
                if signal.actual_outcome in ["hit_tp1", "hit_tp2"]:
                    consecutive_wins += 1
                    consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                elif signal.actual_outcome == "hit_sl":
                    consecutive_losses += 1
                    consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

            # Simulated portfolio (start with $10,000)
            initial_portfolio = 10000.0
            current_portfolio = initial_portfolio

            for signal in signals:
                if signal.actual_pnl_percent:
                    position_size = signal.position_size_percent or 2.0
                    trade_amount = current_portfolio * (position_size / 100)
                    pnl = trade_amount * (signal.actual_pnl_percent / 100)
                    current_portfolio += pnl

            total_return = ((current_portfolio - initial_portfolio) / initial_portfolio) * 100

            metrics = {
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
                "total_signals": total_signals,
                "successful_signals": successful_signals,
                "failed_signals": failed_signals,
                "pending_signals": pending_signals,
                "win_rate": win_rate,
                "avg_profit_percent": avg_profit,
                "avg_loss_percent": avg_loss,
                "profit_factor": profit_factor,
                "max_consecutive_wins": max_consecutive_wins,
                "max_consecutive_losses": max_consecutive_losses,
                "best_trade_percent": best_trade,
                "worst_trade_percent": worst_trade,
                "initial_portfolio": initial_portfolio,
                "current_portfolio": current_portfolio,
                "total_return_percent": total_return
            }

            logger.info(
                f"✓ Performance: {total_signals} signals, "
                f"{win_rate:.1f}% win rate, "
                f"{total_return:+.2f}% return"
            )

            return metrics

    async def save_performance_to_db(self, metrics: Dict):
        """Save performance metrics to database"""
        try:
            async with get_db_session() as session:
                performance = PerformanceModel(
                    calculated_at=datetime.utcnow(),
                    period=metrics["period"],
                    start_date=metrics["start_date"],
                    end_date=metrics["end_date"],
                    total_signals=metrics["total_signals"],
                    successful_signals=metrics["successful_signals"],
                    failed_signals=metrics["failed_signals"],
                    pending_signals=metrics["pending_signals"],
                    win_rate=metrics["win_rate"],
                    avg_profit_percent=metrics["avg_profit_percent"],
                    avg_loss_percent=metrics["avg_loss_percent"],
                    profit_factor=metrics["profit_factor"],
                    max_consecutive_wins=metrics["max_consecutive_wins"],
                    max_consecutive_losses=metrics["max_consecutive_losses"],
                    best_trade_percent=metrics["best_trade_percent"],
                    worst_trade_percent=metrics["worst_trade_percent"],
                    initial_portfolio=metrics["initial_portfolio"],
                    current_portfolio=metrics["current_portfolio"],
                    total_return_percent=metrics["total_return_percent"]
                )

                session.add(performance)

            logger.info(f"✓ Saved {metrics['period']} performance to database")

        except Exception as e:
            logger.error(f"Failed to save performance: {e}")


async def run():
    """Main execution function for Robot 6"""
    logger.info("=" * 60)
    logger.info("ROBOT 6: PERFORMANCE TRACKER - STARTING")
    logger.info("=" * 60)

    try:
        # Initialize database
        await init_database()

        # Initialize tracker
        tracker = PerformanceTracker()

        # Update signal outcomes
        updated = await tracker.update_signal_outcomes()

        # Calculate weekly performance
        weekly_metrics = await tracker.calculate_period_performance(period="weekly")
        await tracker.save_performance_to_db(weekly_metrics)

        # Summary
        logger.info("=" * 60)
        logger.info(f"✅ ROBOT 6 COMPLETED!")
        logger.info(f"  Signals updated: {updated}")
        logger.info(f"  Weekly win rate: {weekly_metrics['win_rate']:.1f}%")
        logger.info(f"  Weekly return: {weekly_metrics['total_return_percent']:+.2f}%")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ ROBOT 6 FAILED: {e}", exc_info=True)
        raise
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(run())