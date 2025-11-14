#!/usr/bin/env python3
# health_check.py
"""
Standalone Health Check Script
Can be run independently or scheduled via Cloud Scheduler
"""

import asyncio
import logging
import sys

from utils.health_check import run_health_check

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HealthCheckScript")


async def main():
    """Run health check and exit with appropriate code"""
    logger.info("Starting health check...")

    try:
        results = await run_health_check(send_alerts=True)

        # Check if any critical issues
        critical_components = [
            name for name, status in results.items()
            if status.status == "CRITICAL"
        ]

        if critical_components:
            logger.error(f"❌ Health check FAILED: {len(critical_components)} critical issues")
            logger.error(f"Critical components: {', '.join(critical_components)}")
            sys.exit(1)
        else:
            logger.info("✓ Health check PASSED")
            sys.exit(0)

    except Exception as e:
        logger.error(f"❌ Health check script failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())