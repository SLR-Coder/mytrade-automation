# utils/telegram_notifier.py
# -*- coding: utf-8 -*-
"""
Telegram notification utilities
"""

import os
import logging
import asyncio
from typing import Optional
from telegram import Bot
from telegram.constants import ParseMode
from utils.secrets import get_secret

logger = logging.getLogger("TelegramNotifier")

async def send_telegram_message(message: str, chat_id: str = None, bot_token: str = None) -> bool:
    """
    Send message to Telegram

    Args:
        message: Message to send
        chat_id: Optional chat ID (uses env var if not provided)
        bot_token: Optional bot token (uses env var if not provided)

    Returns:
        Success status
    """
    try:
        token = bot_token or get_secret("TELEGRAM_BOT_TOKEN", required=False)
        chat = chat_id or get_secret("TELEGRAM_CHAT_ID", required=False)

        if not token or not chat:
            logger.warning("Telegram credentials not configured")
            return False

        bot = Bot(token=token)
        await bot.send_message(
            chat_id=chat,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

        logger.info("Telegram message sent successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

async def send_error_notification(
    robot_name: str,
    error: str,
    attempt: int = 1,
    max_retries: int = 3
) -> bool:
    """
    Send error notification to Telegram ADMIN (private chat)

    Args:
        robot_name: Name of the robot that failed
        error: Error message
        attempt: Current attempt number
        max_retries: Maximum retry attempts

    Returns:
        Success status
    """
    from utils.telegram_formatter import format_error_notification

    message = format_error_notification(robot_name, error, attempt, max_retries)

    # Send to ADMIN private chat, not public channel
    admin_chat_id = get_secret("TELEGRAM_ADMIN_CHAT_ID", required=False)
    return await send_telegram_message(message, chat_id=admin_chat_id)

async def send_status_notification(status: str) -> bool:
    """
    Send status notification to Telegram ADMIN (private chat)

    Args:
        status: Status message

    Returns:
        Success status
    """
    message = f"ℹ️ <b>System Status</b>\n\n{status}"

    # Send to ADMIN private chat, not public channel
    admin_chat_id = get_secret("TELEGRAM_ADMIN_CHAT_ID", required=False)
    return await send_telegram_message(message, chat_id=admin_chat_id)