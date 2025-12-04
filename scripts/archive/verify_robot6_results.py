# -*- coding: utf-8 -*-
"""
Verify Robot 6 Performance Tracker Results
"""

import asyncio
import logging
from sqlalchemy import select
from core.database import init_database, close_database, get_db_session
from data.models.signals import SignalModel
from data.models.performance import PerformanceModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Robot6Verification")


async def verify_results():
    """Verify Robot 6 results"""
    logger.info("=" * 80)
    logger.info("🔍 VERIFYING ROBOT 6 RESULTS")
    logger.info("=" * 80)

    await init_database()

    async with get_db_session() as session:
        # Get all signals
        result = await session.execute(
            select(SignalModel).order_by(SignalModel.time.desc())
        )
        signals = result.scalars().all()

        logger.info(f"\n📊 SIGNAL OUTCOMES:\n")
        logger.info(f"{'Market':<12} {'Signal':<6} {'Confidence':<11} {'Outcome':<12} {'P&L %':<10}")
        logger.info("-" * 80)

        for sig in signals:
            pnl_str = f"{sig.actual_pnl_percent:+.2f}%" if sig.actual_pnl_percent else "N/A"
            logger.info(
                f"{sig.market:<12} {sig.signal:<6} "
                f"{sig.confidence}%{'':<7} {sig.actual_outcome:<12} {pnl_str:<10}"
            )

        # Get performance metrics
        perf_result = await session.execute(
            select(PerformanceModel).order_by(PerformanceModel.calculated_at.desc()).limit(1)
        )
        performance = perf_result.scalar_one_or_none()

        if performance:
            logger.info(f"\n📈 PERFORMANCE METRICS (Weekly):\n")
            logger.info(f"  Period: {performance.start_date.strftime('%Y-%m-%d')} to {performance.end_date.strftime('%Y-%m-%d')}")
            logger.info(f"  Total Signals: {performance.total_signals}")
            logger.info(f"  Successful: {performance.successful_signals}")
            logger.info(f"  Failed: {performance.failed_signals}")
            logger.info(f"  Pending: {performance.pending_signals}")
            logger.info(f"  Win Rate: {performance.win_rate:.1f}%")
            logger.info(f"  Avg Profit: {performance.avg_profit_percent:+.2f}%")
            logger.info(f"  Avg Loss: {performance.avg_loss_percent:+.2f}%")
            logger.info(f"  Profit Factor: {performance.profit_factor:.2f}")
            logger.info(f"  Best Trade: {performance.best_trade_percent:+.2f}%")
            logger.info(f"  Worst Trade: {performance.worst_trade_percent:+.2f}%")
            logger.info(f"  Max Consecutive Wins: {performance.max_consecutive_wins}")
            logger.info(f"  Max Consecutive Losses: {performance.max_consecutive_losses}")
            logger.info(f"\n💰 PORTFOLIO PERFORMANCE:")
            logger.info(f"  Initial: ${performance.initial_portfolio:,.2f}")
            logger.info(f"  Current: ${performance.current_portfolio:,.2f}")
            logger.info(f"  Total Return: {performance.total_return_percent:+.2f}%")
        else:
            logger.warning("  No performance metrics found in database")

    logger.info("\n" + "=" * 80)
    logger.info("✅ VERIFICATION COMPLETE")
    logger.info("=" * 80)

    await close_database()


if __name__ == "__main__":
    asyncio.run(verify_results())
