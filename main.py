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
from utils.telegram_notifier import send_error_notification, send_status_notification, send_robot_progress

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

    Note: Only sends Telegram notification on FAILURE (no spam for start/complete)
    """
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"🤖 {robot_name} çalıştırılıyor... (deneme {attempt + 1}/{max_retries + 1})")

            await robot_module.run()

            logger.info(f"✅ {robot_name} başarıyla tamamlandı")
            return True

        except Exception as e:
            logger.error(f"❌ {robot_name} başarısız: {e}", exc_info=True)

            # Only send Telegram notification on FINAL failure (no spam)
            if attempt >= max_retries:
                try:
                    await send_robot_progress(robot_name, "FAILED", f"Hata: {str(e)[:100]}")
                except:
                    pass
                logger.error(f"💥 {robot_name} {max_retries + 1} denemeden sonra başarısız oldu")
                return False

            # Retry logic
            wait_time = 2 ** attempt  # Exponential backoff
            logger.info(f"⏳ {robot_name} {wait_time}s içinde tekrar deneniyor...")
            await asyncio.sleep(wait_time)

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

    Note: Only sends Telegram notification on FAILURE (no spam for start/complete)
    """
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"🤖 {robot_name} çalıştırılıyor... (deneme {attempt + 1}/{max_retries + 1})")

            robot_module.run()

            logger.info(f"✅ {robot_name} başarıyla tamamlandı")
            return True

        except Exception as e:
            logger.error(f"❌ {robot_name} başarısız: {e}", exc_info=True)

            # Only send Telegram notification on FINAL failure (no spam)
            if attempt >= max_retries:
                try:
                    import asyncio
                    coro = send_robot_progress(robot_name, "FAILED", f"Hata: {str(e)[:100]}")
                    asyncio.run(coro)
                except Exception:
                    try:
                        coro.close()
                    except:
                        pass
                logger.error(f"💥 {robot_name} {max_retries + 1} denemeden sonra başarısız oldu")
                return False

            # Retry logic
            wait_time = 2 ** attempt
            logger.info(f"⏳ {robot_name} {wait_time}s içinde tekrar deneniyor...")
            import time
            time.sleep(wait_time)

    return False


async def main_async():
    """
    Main async entry point for MyTrade automation

    ROBOT EXECUTION ORDER (OPTIMIZED):
    1. Robot 1: Market Harvester - Collect data + indicators
    2. Robot 2: News Analyzer - Fetch news + sentiment
    3. Robot 3: AI Signal Generator - 4 AI analyses (DeepSeek, Claude, GPT-4, Grok)
    4. Robot 8: Personal AI Analyst - User's custom AI analysis
    5. Robot 7: AI Command Center - Meta-analysis (reads Robot 3 + Robot 8)
    6. Robot 4: Chart Generator - Create charts for signals
    7. Robot 5: Telegram Publisher - Publish to channel
    8. Robot 6: Performance Tracker - Track published signals
    9. Robot 9: TP/SL Monitor - Real-time position monitoring (EN SON)

    WHY THIS ORDER?
    - Data collection first (Robot 1)
    - News context second (Robot 2)
    - Robot 3: 4 AI detailed analyses → columns V-AC
    - Robot 8: User's personal AI → columns AD-AE
    - Robot 7: Reads ALL AIs (3+8) and does meta-analysis → columns AF-AI
    - Charts after signals ready (Robot 4)
    - Publishing (Robot 5)
    - Performance tracking after publishing (Robot 6)
    - TP/SL monitoring LAST - checks if targets hit (Robot 9)
    """
    start_time = datetime.now()

    logger.info("=" * 70)
    logger.info("🚀 MYTRADE PROFESYONEL OTOMASYON V2.0")
    logger.info("=" * 70)
    logger.info(f"⏰ Başlangıç: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # NOTE: Start notification removed to reduce Telegram spam
    # Only send notifications on FAILURE

    # Get robot selection from command-line args or environment
    if len(sys.argv) > 1:
        # Command-line argument takes precedence
        robot_select = sys.argv[1]
        logger.info(f"📋 Komut satırından seçili robotlar: {robot_select}")
    else:
        # Fallback to environment variable
        robot_select = os.getenv("ROBOT", "1,2,3,4,5,6,7,8,9")
        logger.info(f"📋 Environment'tan seçili robotlar: {robot_select}")

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
            results["Robot 2: News Analyzer"] = run_sync_robot(
                news_analyzer,
                "Robot 2: News Analyzer"
            )

        # PHASE 2: AI SIGNAL GENERATION (Robot 3 + Robot 8 + Robot 7)
        if "3" in robot_select and not shutdown_requested:
            from robots import ai_signal_generator
            results["Robot 3: AI Signal Generator"] = await run_async_robot(
                ai_signal_generator,
                "Robot 3: AI Signal Generator"
            )

        if "8" in robot_select and not shutdown_requested:
            from robots import personal_ai_analyst
            results["Robot 8: Personal AI Analyst"] = run_sync_robot(
                personal_ai_analyst,
                "Robot 8: Personal AI Analyst"
            )

        if "7" in robot_select and not shutdown_requested:
            from robots import ai_command_center
            results["Robot 7: AI Command Center"] = run_sync_robot(
                ai_command_center,
                "Robot 7: AI Command Center"
            )

        # PHASE 3: VISUALIZATION
        if "4" in robot_select and not shutdown_requested:
            from robots import chart_generator
            results["Robot 4: Chart Generator"] = run_sync_robot(
                chart_generator,
                "Robot 4: Chart Generator"
            )

        # PHASE 4: PUBLISHING
        if "5" in robot_select and not shutdown_requested:
            from robots import telegram_publisher
            results["Robot 5: Telegram Publisher"] = run_sync_robot(
                telegram_publisher,
                "Robot 5: Telegram Publisher"
            )

        # PHASE 5: PERFORMANCE TRACKING
        if "6" in robot_select and not shutdown_requested:
            from robots import performance_tracker
            results["Robot 6: Performance Tracker"] = await run_async_robot(
                performance_tracker,
                "Robot 6: Performance Tracker"
            )

        # PHASE 6: TP/SL MONITORING (EN SON - TP1/TP2/SL seviyelerini kontrol eder)
        if "9" in robot_select and not shutdown_requested:
            from robots import tp_monitor
            results["Robot 9: TP/SL Monitor"] = run_sync_robot(
                tp_monitor,
                "Robot 9: TP/SL Monitor"
            )

        # Calculate execution time
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Summary
        logger.info("=" * 70)
        logger.info("📊 ÇALIŞTIRMA ÖZETİ")
        logger.info("=" * 70)

        successful = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)

        for robot_name, success in results.items():
            status = "✅ BAŞARILI" if success else "❌ BAŞARISIZ"
            logger.info(f"  {robot_name}: {status}")

        logger.info("=" * 70)
        logger.info(f"✅ Başarılı: {successful}/{len(results)}")
        logger.info(f"❌ Başarısız: {failed}/{len(results)}")
        logger.info(f"⏱️  Süre: {duration:.2f}s")
        logger.info("=" * 70)

        if shutdown_requested:
            logger.info("🛑 ZARIF KAPATMA TAMAMLANDI")
        else:
            logger.info("🎉 OTOMASYON BAŞARIYLA TAMAMLANDI")

        logger.info("=" * 70)

        # NOTE: Completion notification removed to reduce Telegram spam
        # Only send notifications on FAILURE

        return 0 if failed == 0 else 1

    except Exception as e:
        logger.error(f"💥 KRİTİK HATA: {e}", exc_info=True)

        # Send critical error notification
        try:
            await send_error_notification(
                robot_name="Ana Orkestratör",
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