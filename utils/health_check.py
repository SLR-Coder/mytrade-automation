# -*- coding: utf-8 -*-
"""
Health Check System
Monitors all critical components and sends alerts
"""

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from utils.secrets import get_secret
from utils.telegram_notifier import send_health_alert

logger = logging.getLogger("HealthCheck")


@dataclass
class HealthStatus:
    """Health status for a component"""
    component: str
    status: str  # HEALTHY, WARNING, CRITICAL
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None


class HealthChecker:
    """
    Comprehensive health check system

    Monitors:
    - Database connectivity (CloudSQL/SQLite)
    - Google Sheets API
    - AI APIs (OpenAI, Claude, Gemini)
    - Telegram Bot API
    - Market data APIs (Binance, Polygon, Alpha Vantage)
    """

    def __init__(self, send_alerts: bool = True):
        """
        Initialize health checker

        Args:
            send_alerts: Whether to send Telegram alerts on issues
        """
        self.send_alerts = send_alerts
        self.results: Dict[str, HealthStatus] = {}

    async def check_all(self) -> Dict[str, HealthStatus]:
        """
        Run all health checks in parallel

        Returns:
            Dictionary of component health statuses
        """
        logger.info("Running comprehensive health checks...")

        # Run all checks in parallel
        checks = [
            self.check_database(),
            self.check_google_sheets(),
            self.check_openai(),
            self.check_claude(),
            self.check_gemini(),
            self.check_telegram(),
            self.check_binance(),
        ]

        results = await asyncio.gather(*checks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
            elif isinstance(result, HealthStatus):
                self.results[result.component] = result

        # Send alerts for critical issues
        if self.send_alerts:
            await self._send_alerts()

        # Log summary
        self._log_summary()

        return self.results

    async def check_database(self) -> HealthStatus:
        """Check database connectivity"""
        component = "Database"
        start_time = datetime.now()

        try:
            from core.database import get_db_session

            async with get_db_session() as session:
                # Simple query to test connection
                result = await session.execute("SELECT 1")
                row = result.fetchone()

                if row and row[0] == 1:
                    response_time = (datetime.now() - start_time).total_seconds()
                    logger.info(f"✓ {component}: HEALTHY ({response_time:.2f}s)")

                    return HealthStatus(
                        component=component,
                        status="HEALTHY",
                        response_time=response_time,
                        timestamp=datetime.now()
                    )
                else:
                    raise Exception("Query returned unexpected result")

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"✗ {component}: CRITICAL - {e}")

            return HealthStatus(
                component=component,
                status="CRITICAL",
                response_time=response_time,
                error_message=str(e),
                timestamp=datetime.now()
            )

    async def check_google_sheets(self) -> HealthStatus:
        """Check Google Sheets API connectivity"""
        component = "Google Sheets"
        start_time = datetime.now()

        try:
            from utils.auth import get_gspread_client

            sheet_id = get_secret("GOOGLE_SHEET_ID", required=False)
            if not sheet_id:
                return HealthStatus(
                    component=component,
                    status="WARNING",
                    error_message="GOOGLE_SHEET_ID not configured",
                    timestamp=datetime.now()
                )

            gc = get_gspread_client()
            sheet = gc.open_by_key(sheet_id)
            ws = sheet.get_worksheet(0)

            # Test read access
            _ = ws.row_count

            response_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✓ {component}: HEALTHY ({response_time:.2f}s)")

            return HealthStatus(
                component=component,
                status="HEALTHY",
                response_time=response_time,
                timestamp=datetime.now()
            )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"✗ {component}: CRITICAL - {e}")

            return HealthStatus(
                component=component,
                status="CRITICAL",
                response_time=response_time,
                error_message=str(e),
                timestamp=datetime.now()
            )

    async def check_openai(self) -> HealthStatus:
        """Check OpenAI API"""
        component = "OpenAI API"
        start_time = datetime.now()

        try:
            api_key = get_secret("OPENAI_API_KEY", required=False)
            if not api_key:
                return HealthStatus(
                    component=component,
                    status="WARNING",
                    error_message="API key not configured",
                    timestamp=datetime.now()
                )

            import openai
            client = openai.OpenAI(api_key=api_key)

            # Test with simple completion
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )

            if response.choices:
                response_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✓ {component}: HEALTHY ({response_time:.2f}s)")

                return HealthStatus(
                    component=component,
                    status="HEALTHY",
                    response_time=response_time,
                    timestamp=datetime.now()
                )
            else:
                raise Exception("No response from API")

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"✗ {component}: WARNING - {e}")

            return HealthStatus(
                component=component,
                status="WARNING",
                response_time=response_time,
                error_message=str(e),
                timestamp=datetime.now()
            )

    async def check_claude(self) -> HealthStatus:
        """Check Claude API"""
        component = "Claude API"
        start_time = datetime.now()

        try:
            api_key = get_secret("ANTHROPIC_API_KEY", required=False)
            if not api_key:
                return HealthStatus(
                    component=component,
                    status="WARNING",
                    error_message="API key not configured",
                    timestamp=datetime.now()
                )

            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            # Test with simple completion
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=5,
                messages=[{"role": "user", "content": "test"}]
            )

            if response.content:
                response_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✓ {component}: HEALTHY ({response_time:.2f}s)")

                return HealthStatus(
                    component=component,
                    status="HEALTHY",
                    response_time=response_time,
                    timestamp=datetime.now()
                )
            else:
                raise Exception("No response from API")

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"✗ {component}: WARNING - {e}")

            return HealthStatus(
                component=component,
                status="WARNING",
                response_time=response_time,
                error_message=str(e),
                timestamp=datetime.now()
            )

    async def check_gemini(self) -> HealthStatus:
        """Check Gemini API"""
        component = "Gemini API"
        start_time = datetime.now()

        try:
            api_key = get_secret("GEMINI_API_KEY", required=False)
            if not api_key:
                return HealthStatus(
                    component=component,
                    status="WARNING",
                    error_message="API key not configured",
                    timestamp=datetime.now()
                )

            import google.generativeai as genai
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("test", generation_config={"max_output_tokens": 5})

            if response.text:
                response_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✓ {component}: HEALTHY ({response_time:.2f}s)")

                return HealthStatus(
                    component=component,
                    status="HEALTHY",
                    response_time=response_time,
                    timestamp=datetime.now()
                )
            else:
                raise Exception("No response from API")

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"✗ {component}: WARNING - {e}")

            return HealthStatus(
                component=component,
                status="WARNING",
                response_time=response_time,
                error_message=str(e),
                timestamp=datetime.now()
            )

    async def check_telegram(self) -> HealthStatus:
        """Check Telegram Bot API"""
        component = "Telegram Bot"
        start_time = datetime.now()

        try:
            from telegram import Bot

            bot_token = get_secret("TELEGRAM_BOT_TOKEN", required=False)
            if not bot_token:
                return HealthStatus(
                    component=component,
                    status="WARNING",
                    error_message="Bot token not configured",
                    timestamp=datetime.now()
                )

            bot = Bot(token=bot_token)
            bot_info = await bot.get_me()

            if bot_info:
                response_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✓ {component}: HEALTHY ({response_time:.2f}s) - @{bot_info.username}")

                return HealthStatus(
                    component=component,
                    status="HEALTHY",
                    response_time=response_time,
                    timestamp=datetime.now()
                )
            else:
                raise Exception("No bot info returned")

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"✗ {component}: CRITICAL - {e}")

            return HealthStatus(
                component=component,
                status="CRITICAL",
                response_time=response_time,
                error_message=str(e),
                timestamp=datetime.now()
            )

    async def check_binance(self) -> HealthStatus:
        """Check Binance API"""
        component = "Binance API"
        start_time = datetime.now()

        try:
            import ccxt

            exchange = ccxt.binance()
            ticker = await asyncio.to_thread(exchange.fetch_ticker, 'BTC/USDT')

            if ticker and 'last' in ticker:
                response_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✓ {component}: HEALTHY ({response_time:.2f}s)")

                return HealthStatus(
                    component=component,
                    status="HEALTHY",
                    response_time=response_time,
                    timestamp=datetime.now()
                )
            else:
                raise Exception("No ticker data returned")

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"✗ {component}: WARNING - {e}")

            return HealthStatus(
                component=component,
                status="WARNING",
                response_time=response_time,
                error_message=str(e),
                timestamp=datetime.now()
            )

    async def _send_alerts(self):
        """Send Telegram alerts for critical/warning issues"""
        critical_components = [
            name for name, status in self.results.items()
            if status.status == "CRITICAL"
        ]

        warning_components = [
            name for name, status in self.results.items()
            if status.status == "WARNING"
        ]

        if critical_components:
            for component in critical_components:
                status = self.results[component]
                await send_health_alert(
                    component=component,
                    status="CRITICAL",
                    details=status.error_message
                )

        elif warning_components:
            # Only send warning alert if there are warnings but no critical issues
            for component in warning_components:
                status = self.results[component]
                await send_health_alert(
                    component=component,
                    status="WARNING",
                    details=status.error_message
                )

    def _log_summary(self):
        """Log health check summary"""
        healthy_count = sum(1 for s in self.results.values() if s.status == "HEALTHY")
        warning_count = sum(1 for s in self.results.values() if s.status == "WARNING")
        critical_count = sum(1 for s in self.results.values() if s.status == "CRITICAL")

        logger.info("=" * 60)
        logger.info("HEALTH CHECK SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✓ Healthy: {healthy_count}")
        logger.info(f"⚠ Warning: {warning_count}")
        logger.info(f"✗ Critical: {critical_count}")
        logger.info("=" * 60)


# Convenience function for quick health checks
async def run_health_check(send_alerts: bool = True) -> Dict[str, HealthStatus]:
    """
    Run comprehensive health check

    Args:
        send_alerts: Whether to send Telegram alerts

    Returns:
        Dictionary of component health statuses
    """
    checker = HealthChecker(send_alerts=send_alerts)
    return await checker.check_all()


if __name__ == "__main__":
    # Run health check
    import asyncio
    asyncio.run(run_health_check())