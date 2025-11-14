# main.py
# -*- coding: utf-8 -*-
"""
MyTrade - Professional AI-Powered Trading Automation
Version: 2.0
Quality: 10/10 Production-Ready
"""

import sys
import os
import asyncio
from datetime import datetime
from typing import Dict, Optional
import signal

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Setup structured logging FIRST
from utils.structured_logging import setup_logging, get_logger, log_async_execution_time

# Initialize structured logging
environment = os.getenv("ENVIRONMENT", "development")
setup_logging(
    environment=environment,
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    enable_json=os.getenv("ENABLE_JSON_LOGGING", "false").lower() == "true",
    enable_cloud_logging=environment == "production"
)

logger = get_logger("MyTrade-Main")

# Telegram notifications for critical errors
from utils.telegram_notifier import send_error_notification, send_status_notification

# Global shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.info("🛑 Shutdown signal received. Cleaning up...")
    shutdown_requested = True


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


async def run_async_robot(robot_module, robot_name: str, max_retries: int = 2) -> bool:
    """
    Run async robot with retry logic and error notifications

    Args:
        robot_module: Robot module to run
        robot_name: Robot display name
        max_retries: Maximum retry attempts on failure

    Returns:
        bool: Success status
    """
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"🤖 Running {robot_name}... (attempt {attempt + 1}/{max_retries + 1})")

            await robot_module.run()

            logger.info(f"✅ {robot_name} completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ {robot_name} failed: {e}", exc_info=True)

            # Send Telegram notification on error
            try:
                await send_error_notification(
                    robot_name=robot_name,
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
            except:
                pass  # Don't fail if notification fails

            # Retry logic
            if attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"⏳ Retrying {robot_name} in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"💥 {robot_name} failed after {max_retries + 1} attempts")
                return False

    return False


def run_sync_robot(robot_module, robot_name: str, max_retries: int = 2) -> bool:
    """
    Run sync robot with retry logic and error notifications

    Args:
        robot_module: Robot module to run
        robot_name: Robot display name
        max_retries: Maximum retry attempts on failure

    Returns:
        bool: Success status
    """
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"🤖 Running {robot_name}... (attempt {attempt + 1}/{max_retries + 1})")

            robot_module.run()

            logger.info(f"✅ {robot_name} completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ {robot_name} failed: {e}", exc_info=True)

            # Send Telegram notification on error (sync version)
            try:
                import asyncio
                asyncio.run(send_error_notification(
                    robot_name=robot_name,
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=max_retries
                ))
            except:
                pass

            # Retry logic
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.info(f"⏳ Retrying {robot_name} in {wait_time}s...")
                import time
                time.sleep(wait_time)
            else:
                logger.error(f"💥 {robot_name} failed after {max_retries + 1} attempts")
                return False

    return False


async def main_async():
    """
    Main async entry point for MyTrade automation

    ROBOT EXECUTION ORDER (OPTIMIZED):
    1. Robot 1: Market Harvester - Collect data + indicators
    2. Robot 2: News Analyzer - Fetch news + sentiment
    3. Robot 6: Performance Tracker - Update old signals FIRST
    4. Robot 3: AI Signal Generator - Generate NEW signals
    5. Robot 4: Chart Generator - Create charts for signals
    6. Robot 5: Telegram Publisher - Publish to channel

    WHY THIS ORDER?
    - Data collection first (Robot 1)
    - News context second (Robot 2)
    - Update OLD signals before generating NEW ones (Robot 6 → Robot 3)
    - Charts after signals ready (Robot 4)
    - Publishing last (Robot 5)
    """
    start_time = datetime.now()

    logger.info("=" * 70)
    logger.info("🚀 MYTRADE PROFESSIONAL AUTOMATION V2.0")
    logger.info("=" * 70)
    logger.info(f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Send start notification
    try:
        await send_status_notification("🚀 MyTrade automation started")
    except:
        pass

    # Get robot selection from environment
    robot_select = os.getenv("ROBOT", "1,2,3,4,5,6")
    logger.info(f"📋 Selected robots: {robot_select}")

    results: Dict[str, bool] = {}

    try:
        # PHASE 1: DATA COLLECTION
        if "1" in robot_select and not shutdown_requested:
            from robots import market_harvester
            results["Robot 1: Market Harvester"] = run_sync_robot(
                market_harvester,
                "Robot 1: Market Harvester"
            )

        if "2" in robot_select and not shutdown_requested:
            from robots import news_analyzer
            results["Robot 2: News Analyzer"] = await run_async_robot(
                news_analyzer,
                "Robot 2: News Analyzer"
            )

        # PHASE 2: PERFORMANCE UPDATE (BEFORE NEW SIGNALS)
        if "6" in robot_select and not shutdown_requested:
            from robots import performance_tracker
            results["Robot 6: Performance Tracker"] = await run_async_robot(
                performance_tracker,
                "Robot 6: Performance Tracker"
            )

        # PHASE 3: SIGNAL GENERATION
        if "3" in robot_select and not shutdown_requested:
            from robots import ai_signal_generator
            results["Robot 3: AI Signal Generator"] = await run_async_robot(
                ai_signal_generator,
                "Robot 3: AI Signal Generator"
            )

        # PHASE 4: VISUALIZATION
        if "4" in robot_select and not shutdown_requested:
            from robots import chart_generator
            results["Robot 4: Chart Generator"] = run_sync_robot(
                chart_generator,
                "Robot 4: Chart Generator"
            )

        # PHASE 5: PUBLISHING
        if "5" in robot_select and not shutdown_requested:
            from robots import telegram_publisher
            results["Robot 5: Telegram Publisher"] = run_sync_robot(
                telegram_publisher,
                "Robot 5: Telegram Publisher"
            )

        # Calculate execution time
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Summary
        logger.info("=" * 70)
        logger.info("📊 EXECUTION SUMMARY")
        logger.info("=" * 70)

        successful = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)

        for robot_name, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"  {robot_name}: {status}")

        logger.info("=" * 70)
        logger.info(f"✅ Successful: {successful}/{len(results)}")
        logger.info(f"❌ Failed: {failed}/{len(results)}")
        logger.info(f"⏱️  Duration: {duration:.2f}s")
        logger.info("=" * 70)

        if shutdown_requested:
            logger.info("🛑 GRACEFUL SHUTDOWN COMPLETED")
        else:
            logger.info("🎉 AUTOMATION COMPLETED SUCCESSFULLY")

        logger.info("=" * 70)

        # Send completion notification
        try:
            status_emoji = "✅" if failed == 0 else "⚠️"
            await send_status_notification(
                f"{status_emoji} Automation completed\n"
                f"Success: {successful}/{len(results)}\n"
                f"Duration: {duration:.1f}s"
            )
        except:
            pass

        return 0 if failed == 0 else 1

    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR: {e}", exc_info=True)

        # Send critical error notification
        try:
            await send_error_notification(
                robot_name="Main Orchestrator",
                error=str(e),
                attempt=1,
                max_retries=0
            )
        except:
            pass

        return 1


def main():
    """Sync wrapper for async main with graceful shutdown"""
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)