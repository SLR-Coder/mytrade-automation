# utils/schema.py
# -*- coding: utf-8 -*-
"""
Google Sheets schema utilities
"""

import logging
from typing import List

logger = logging.getLogger("Schema")

class ColumnMapping:
    """Google Sheets için sütun eşlemesi"""
    A = 1   # Zaman Damgası
    B = 2   # Piyasa
    C = 3   # Fiyat
    D = 4   # Değişim %
    E = 5   # Hacim
    F = 6   # RSI
    G = 7   # MACD
    H = 8   # MACD Sinyal
    I = 9   # MACD Histogram
    J = 10  # BB Üst
    K = 11  # BB Orta
    L = 12  # BB Alt
    M = 13  # EMA 9
    N = 14  # EMA 21
    O = 15  # EMA 50
    P = 16  # EMA 200
    Q = 17  # Destek
    R = 18  # Direnç
    S = 19  # Eğilim
    T = 20  # Haber Özeti
    U = 21  # Haber Duyarlılığı
    V = 22  # GPT-4 Sinyali
    W = 23  # Claude Sinyali
    X = 24  # Gemini Sinyali
    Y = 25  # Nihai Sinyal
    Z = 26  # Güven
    AA = 27 # AI Gerekçesi
    AB = 28 # Giriş Fiyatı
    AC = 29 # Zarar Durdur
    AD = 30 # Kar Al 1
    AE = 31 # Kar Al 2
    AF = 32 # Risk/Ödül
    AG = 33 # Pozisyon Büyüklüğü
    AH = 34 # Durum
    AI = 35 # Notlar
    AJ = 36 # Qwen Sinyali
    AK = 37 # DeepSeek Sinyali
    AL = 38 # Grok Sinyali
    AM = 39 # Asistan AI Önerisi
    AN = 40 # Komuta Merkezi Kararı
    AO = 41 # Komuta Merkezi Gerekçesi
    AP = 42 # Consensus Skoru
    AQ = 43 # Yedek
    AR = 44 # Yedek
    AS = 45 # Yedek

def create_header_row() -> List[str]:
    """
    Create header row for Google Sheets

    Returns:
        List of column headers
    """
    headers = [
        "Zaman Damgası",     # A
        "Piyasa",            # B
        "Fiyat",             # C
        "Değişim %",         # D
        "Hacim",             # E
        "RSI",               # F
        "MACD",              # G
        "MACD Sinyal",       # H
        "MACD Hist",         # I
        "BB Üst",            # J
        "BB Orta",           # K
        "BB Alt",            # L
        "EMA 9",             # M
        "EMA 21",            # N
        "EMA 50",            # O
        "EMA 200",           # P
        "Destek",            # Q
        "Direnç",            # R
        "Eğilim",            # S
        "Haber Özeti",       # T
        "Haber Duyarlılığı", # U
        "GPT-4 Sinyali",     # V
        "Claude Sinyali",    # W
        "Gemini Sinyali",    # X
        "Nihai Sinyal",      # Y
        "Güven %",           # Z
        "AI Gerekçesi",      # AA
        "Giriş Fiyatı",      # AB
        "Zarar Durdur",      # AC
        "Kar Al 1",          # AD
        "Kar Al 2",          # AE
        "Risk/Ödül",         # AF
        "Pozisyon Büyüklüğü %", # AG
        "Durum",             # AH
        "Notlar",            # AI
        "Qwen Sinyali",      # AJ
        "DeepSeek Sinyali",  # AK
        "Grok Sinyali",      # AL
        "Asistan AI",        # AM
        "Komuta Merkezi",    # AN
        "KM Gerekçesi",      # AO
        "Consensus %",       # AP
        "Yedek",             # AQ
        "Yedek",             # AR
        "Yedek"              # AS
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