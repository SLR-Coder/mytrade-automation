# engines/macro_overlay.py
# -*- coding: utf-8 -*-
"""
Macro Event Overlay Engine
==========================
Event-driven analysis for FX, metals, and indices.
Only activates on important economic calendar days.

Covered instruments:
- FX: EURUSD, GBPUSD, USDJPY
- Metals: XAUUSD, XAGUSD
- Indices: US500, US100, US30, DAX40, FTSE100, JP225

Triggers:
- CPI, NFP, FOMC, GDP releases
- Central bank decisions (ECB, BOJ, BOE)
- Geopolitical events
- Energy reports (EIA)
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger("MacroOverlay")

# Turkey timezone
TURKEY_TZ = pytz.timezone('Europe/Istanbul')

# Macro instruments
MACRO_INSTRUMENTS = {
    "fx": ["EURUSD", "GBPUSD", "USDJPY"],
    "metals": ["XAUUSD", "XAGUSD"],
    "indices": ["US500", "US100", "US30", "DAX40", "FTSE100", "JP225"]
}

# Event importance levels
EVENT_IMPORTANCE = {
    "FOMC": "CRITICAL",
    "NFP": "CRITICAL",
    "CPI": "CRITICAL",
    "GDP": "HIGH",
    "ECB": "HIGH",
    "BOJ": "HIGH",
    "BOE": "HIGH",
    "PMI": "MEDIUM",
    "RETAIL_SALES": "MEDIUM",
    "JOBLESS_CLAIMS": "MEDIUM",
    "FED_SPEAK": "MEDIUM",
    "EIA": "MEDIUM",
    "GEOPOLITICAL": "HIGH"
}

# Asset impact mapping
EVENT_ASSET_IMPACT = {
    "FOMC": {
        "EURUSD": "inverse",   # USD strength = EURUSD down
        "GBPUSD": "inverse",
        "USDJPY": "direct",    # USD strength = USDJPY up
        "XAUUSD": "inverse",   # USD strength = gold down
        "XAGUSD": "inverse",
        "US500": "mixed",      # Depends on nature of decision
        "US100": "mixed",
        "US30": "mixed"
    },
    "NFP": {
        "EURUSD": "inverse",
        "GBPUSD": "inverse",
        "USDJPY": "direct",
        "XAUUSD": "inverse",
        "US500": "mixed",
        "US100": "mixed"
    },
    "CPI": {
        "EURUSD": "inverse",
        "GBPUSD": "inverse",
        "USDJPY": "direct",
        "XAUUSD": "mixed",     # Inflation hedge vs USD strength
        "US500": "inverse",    # Higher CPI = hawkish Fed fear
        "US100": "inverse"
    },
    "ECB": {
        "EURUSD": "direct",    # Hawkish ECB = EUR strength
        "DAX40": "inverse"     # Hawkish = rates up = stocks down
    },
    "BOJ": {
        "USDJPY": "inverse",   # Hawkish BOJ = JPY strength = USDJPY down
        "JP225": "inverse"
    },
    "BOE": {
        "GBPUSD": "direct",
        "FTSE100": "inverse"
    }
}


class MacroOverlay:
    """
    Macro event overlay for non-crypto instruments.
    Only runs on event days.
    """

    def __init__(self):
        self.events_cache = {}
        self.last_calendar_fetch = None

    def is_event_day(self, date: datetime = None) -> bool:
        """
        Check if today is an important event day

        Args:
            date: Date to check (defaults to today)

        Returns:
            True if important events scheduled
        """
        if date is None:
            date = datetime.now(TURKEY_TZ).date()

        events = self.get_events_for_date(date)
        high_importance = [e for e in events if e.get("importance") in ["CRITICAL", "HIGH"]]

        return len(high_importance) > 0

    def get_events_for_date(self, date: datetime = None) -> List[Dict]:
        """
        Get economic events for a date

        Args:
            date: Date to check

        Returns:
            List of events
        """
        # In production, this would fetch from economic calendar API
        # For now, return mock structure

        if date is None:
            date = datetime.now(TURKEY_TZ).date()

        date_str = date.isoformat() if hasattr(date, 'isoformat') else str(date)

        # Check cache
        if date_str in self.events_cache:
            return self.events_cache[date_str]

        # TODO: Integrate with economic calendar API (Investing.com, ForexFactory, etc.)
        # For now, return empty - this should be populated from external source

        return []

    def add_event(self, event: Dict) -> None:
        """
        Add event to calendar (for manual or API-fed events)

        Args:
            event: Event dict with date, type, importance, etc.
        """
        date_str = event.get("date", datetime.now(TURKEY_TZ).date().isoformat())

        if date_str not in self.events_cache:
            self.events_cache[date_str] = []

        self.events_cache[date_str].append(event)

    def get_affected_instruments(self, event_type: str) -> List[str]:
        """
        Get instruments affected by an event type

        Args:
            event_type: Type of event (FOMC, CPI, etc.)

        Returns:
            List of affected instruments
        """
        impact_map = EVENT_ASSET_IMPACT.get(event_type, {})
        return list(impact_map.keys())

    def calculate_event_bias(self, event: Dict, actual: float = None, forecast: float = None) -> Dict:
        """
        Calculate bias from event data

        Args:
            event: Event dict
            actual: Actual value (if released)
            forecast: Forecast value

        Returns:
            Bias analysis
        """
        event_type = event.get("type", "UNKNOWN")
        importance = EVENT_IMPORTANCE.get(event_type, "LOW")

        # If no actual data, return pre-event analysis
        if actual is None:
            return {
                "phase": "PRE_EVENT",
                "event_type": event_type,
                "importance": importance,
                "bias": "NEUTRAL",
                "risk_tone": "CAUTION",
                "message": f"Upcoming {event_type} release - exercise caution"
            }

        # Calculate surprise
        if forecast and forecast != 0:
            surprise = ((actual - forecast) / abs(forecast)) * 100
        else:
            surprise = 0

        # Determine bias based on surprise direction
        # For most US data: better than expected = USD bullish

        if event_type in ["NFP", "GDP", "RETAIL_SALES", "PMI"]:
            # Higher = better for economy/USD
            if surprise > 5:
                usd_bias = "STRONG_BULLISH"
                risk_tone = "RISK_ON"
            elif surprise > 1:
                usd_bias = "BULLISH"
                risk_tone = "RISK_ON"
            elif surprise > -1:
                usd_bias = "NEUTRAL"
                risk_tone = "NEUTRAL"
            elif surprise > -5:
                usd_bias = "BEARISH"
                risk_tone = "RISK_OFF"
            else:
                usd_bias = "STRONG_BEARISH"
                risk_tone = "RISK_OFF"

        elif event_type in ["CPI", "JOBLESS_CLAIMS"]:
            # For CPI: Higher = hawkish = USD bullish but risk off
            # For Jobless: Higher = worse = USD bearish
            if event_type == "JOBLESS_CLAIMS":
                surprise = -surprise  # Invert for jobless claims

            if surprise > 3:
                usd_bias = "BULLISH"
                risk_tone = "RISK_OFF"  # Hawkish
            elif surprise > 0.5:
                usd_bias = "LEAN_BULLISH"
                risk_tone = "CAUTIOUS"
            elif surprise > -0.5:
                usd_bias = "NEUTRAL"
                risk_tone = "NEUTRAL"
            elif surprise > -3:
                usd_bias = "LEAN_BEARISH"
                risk_tone = "RISK_ON"
            else:
                usd_bias = "BEARISH"
                risk_tone = "RISK_ON"

        else:
            usd_bias = "NEUTRAL"
            risk_tone = "NEUTRAL"

        return {
            "phase": "POST_EVENT",
            "event_type": event_type,
            "importance": importance,
            "actual": actual,
            "forecast": forecast,
            "surprise_pct": round(surprise, 2),
            "usd_bias": usd_bias,
            "risk_tone": risk_tone,
            "message": f"{event_type}: Actual {actual} vs Forecast {forecast} ({surprise:+.1f}% surprise)"
        }

    def get_instrument_bias(self, instrument: str, event_bias: Dict) -> Dict:
        """
        Get bias for specific instrument based on event

        Args:
            instrument: Instrument symbol
            event_bias: Event bias from calculate_event_bias

        Returns:
            Instrument-specific bias
        """
        event_type = event_bias.get("event_type")
        usd_bias = event_bias.get("usd_bias", "NEUTRAL")

        # Get impact relationship
        impact_map = EVENT_ASSET_IMPACT.get(event_type, {})
        relationship = impact_map.get(instrument, "neutral")

        # Convert USD bias to instrument bias
        if relationship == "direct":
            instrument_bias = usd_bias
        elif relationship == "inverse":
            # Flip the bias
            bias_flip = {
                "STRONG_BULLISH": "STRONG_BEARISH",
                "BULLISH": "BEARISH",
                "LEAN_BULLISH": "LEAN_BEARISH",
                "NEUTRAL": "NEUTRAL",
                "LEAN_BEARISH": "LEAN_BULLISH",
                "BEARISH": "BULLISH",
                "STRONG_BEARISH": "STRONG_BULLISH"
            }
            instrument_bias = bias_flip.get(usd_bias, "NEUTRAL")
        else:
            instrument_bias = "NEUTRAL"

        return {
            "instrument": instrument,
            "bias": instrument_bias,
            "relationship": relationship,
            "event_type": event_type,
            "risk_tone": event_bias.get("risk_tone"),
            "importance": event_bias.get("importance")
        }

    def generate_event_day_summary(self, date: datetime = None) -> Dict:
        """
        Generate summary for event day

        Args:
            date: Date to summarize

        Returns:
            Event day summary
        """
        if date is None:
            date = datetime.now(TURKEY_TZ)

        events = self.get_events_for_date(date)

        if not events:
            return {
                "is_event_day": False,
                "date": date.isoformat() if hasattr(date, 'isoformat') else str(date),
                "message": "No significant events scheduled"
            }

        # Sort by importance
        sorted_events = sorted(
            events,
            key=lambda x: {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}.get(
                EVENT_IMPORTANCE.get(x.get("type"), "LOW"), 0
            ),
            reverse=True
        )

        # Get all affected instruments
        all_affected = set()
        for event in events:
            all_affected.update(self.get_affected_instruments(event.get("type", "")))

        return {
            "is_event_day": True,
            "date": date.isoformat() if hasattr(date, 'isoformat') else str(date),
            "event_count": len(events),
            "events": sorted_events,
            "highest_importance": sorted_events[0].get("type") if sorted_events else None,
            "affected_instruments": list(all_affected),
            "risk_warning": "High-impact events scheduled - increased volatility expected"
        }

    def format_pre_event_alert(self, event: Dict, minutes_until: int = 30) -> str:
        """
        Format pre-event alert message

        Args:
            event: Event dict
            minutes_until: Minutes until event

        Returns:
            Telegram-formatted alert
        """
        event_type = event.get("type", "UNKNOWN")
        importance = EVENT_IMPORTANCE.get(event_type, "MEDIUM")

        importance_emoji = {
            "CRITICAL": "🚨",
            "HIGH": "⚠️",
            "MEDIUM": "📊",
            "LOW": "ℹ️"
        }.get(importance, "📊")

        affected = self.get_affected_instruments(event_type)

        message = f"{importance_emoji} <b>YAKLAŞAN VERİ: {event_type}</b>\n"
        message += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"⏰ <b>{minutes_until} dakika sonra</b>\n"
        message += f"📈 <b>Önem:</b> {importance}\n"

        if event.get("forecast"):
            message += f"📊 <b>Beklenti:</b> {event.get('forecast')}\n"
        if event.get("previous"):
            message += f"📉 <b>Önceki:</b> {event.get('previous')}\n"

        message += f"\n<b>Etkilenen Enstrümanlar:</b>\n"
        for inst in affected[:6]:
            message += f"• {inst}\n"

        message += f"\n⚠️ Volatilite artabilir - pozisyon boyutunu ayarlayın"

        return message

    def format_post_event_message(self, event: Dict, actual: float, forecast: float) -> str:
        """
        Format post-event analysis message

        Args:
            event: Event dict
            actual: Actual value
            forecast: Forecast value

        Returns:
            Telegram-formatted message
        """
        event_bias = self.calculate_event_bias(event, actual, forecast)

        event_type = event.get("type", "UNKNOWN")
        surprise = event_bias.get("surprise_pct", 0)
        usd_bias = event_bias.get("usd_bias", "NEUTRAL")
        risk_tone = event_bias.get("risk_tone", "NEUTRAL")

        # Emojis
        if surprise > 0:
            surprise_emoji = "📈" if surprise > 3 else "↗️"
        elif surprise < 0:
            surprise_emoji = "📉" if surprise < -3 else "↘️"
        else:
            surprise_emoji = "➡️"

        tone_emoji = {
            "RISK_ON": "🟢",
            "RISK_OFF": "🔴",
            "CAUTIOUS": "🟡",
            "NEUTRAL": "⚪"
        }.get(risk_tone, "⚪")

        message = f"📊 <b>{event_type} SONUÇLARI</b>\n"
        message += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"<b>Gerçekleşen:</b> {actual}\n"
        message += f"<b>Beklenen:</b> {forecast}\n"
        message += f"{surprise_emoji} <b>Sürpriz:</b> {surprise:+.1f}%\n\n"
        message += f"💵 <b>USD Yönü:</b> {usd_bias}\n"
        message += f"{tone_emoji} <b>Risk Tonu:</b> {risk_tone}\n"

        # Add instrument-specific biases
        message += f"\n<b>Enstrüman Etkileri:</b>\n"
        affected = self.get_affected_instruments(event_type)
        for inst in affected[:4]:
            inst_bias = self.get_instrument_bias(inst, event_bias)
            bias_emoji = "📈" if "BULLISH" in inst_bias["bias"] else "📉" if "BEARISH" in inst_bias["bias"] else "➡️"
            message += f"• {inst}: {bias_emoji} {inst_bias['bias']}\n"

        return message
