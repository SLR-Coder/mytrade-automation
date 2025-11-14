# utils/schema.py
# -*- coding: utf-8 -*-
"""
Google Sheets schema utilities
"""

import logging
from typing import List

logger = logging.getLogger("Schema")

class ColumnMapping:
    """Column mapping for Google Sheets"""
    A = 1   # Timestamp
    B = 2   # Market
    C = 3   # Price
    D = 4   # Change %
    E = 5   # Volume
    F = 6   # RSI
    G = 7   # MACD
    H = 8   # MACD Signal
    I = 9   # MACD Histogram
    J = 10  # BB Upper
    K = 11  # BB Middle
    L = 12  # BB Lower
    M = 13  # EMA 9
    N = 14  # EMA 21
    O = 15  # EMA 50
    P = 16  # EMA 200
    Q = 17  # Support
    R = 18  # Resistance
    S = 19  # Trend
    T = 20  # News Summary
    U = 21  # News Sentiment
    V = 22  # GPT-4 Signal
    W = 23  # Claude Signal
    X = 24  # Gemini Signal
    Y = 25  # Final Signal
    Z = 26  # Confidence
    AA = 27 # AI Reasoning
    AB = 28 # Entry Price
    AC = 29 # Stop Loss
    AD = 30 # Take Profit 1
    AE = 31 # Take Profit 2
    AF = 32 # Risk/Reward
    AG = 33 # Position Size
    AH = 34 # Status
    AI = 35 # Notes
    AJ = 36 # Reserved
    AK = 37 # Reserved
    AL = 38 # Reserved

def create_header_row() -> List[str]:
    """
    Create header row for Google Sheets

    Returns:
        List of column headers
    """
    headers = [
        "Timestamp",          # A
        "Market",            # B
        "Price",             # C
        "Change %",          # D
        "Volume",            # E
        "RSI",               # F
        "MACD",              # G
        "MACD Signal",       # H
        "MACD Hist",         # I
        "BB Upper",          # J
        "BB Middle",         # K
        "BB Lower",          # L
        "EMA 9",             # M
        "EMA 21",            # N
        "EMA 50",            # O
        "EMA 200",           # P
        "Support",           # Q
        "Resistance",        # R
        "Trend",             # S
        "News Summary",      # T
        "News Sentiment",    # U
        "GPT-4 Signal",      # V
        "Claude Signal",     # W
        "Gemini Signal",     # X
        "Final Signal",      # Y
        "Confidence %",      # Z
        "AI Reasoning",      # AA
        "Entry Price",       # AB
        "Stop Loss",         # AC
        "Take Profit 1",     # AD
        "Take Profit 2",     # AE
        "Risk/Reward",       # AF
        "Position Size %",   # AG
        "Status",            # AH
        "Notes",             # AI
        "Reserved",          # AJ
        "Reserved",          # AK
        "Reserved"           # AL
    ]
    return headers

def resolve_columns(worksheet) -> ColumnMapping:
    """
    Get column mapping for worksheet

    Args:
        worksheet: Google Sheets worksheet

    Returns:
        ColumnMapping object
    """
    return ColumnMapping()