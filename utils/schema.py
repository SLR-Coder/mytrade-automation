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
    # BÖLÜM 1: PİYASA VERİLERİ (Robot 1)
    A = 1   # Zaman Damgası
    B = 2   # Piyasa
    C = 3   # Fiyat
    D = 4   # Değişim %
    E = 5   # Hacim

    # BÖLÜM 2: TEKNİK GÖSTERGELER (Robot 1)
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

    # BÖLÜM 3: HABER ANALİZİ (Robot 2)
    T = 20  # Haber Özeti
    U = 21  # Haber Duyarlılığı

    # BÖLÜM 4: AI ANALİZLERİ (Robot 3 - 4 AI x 2 kolon)
    V = 22  # DeepSeek Sinyal
    W = 23  # DeepSeek Analiz
    X = 24  # Claude Sinyal
    Y = 25  # Claude Analiz
    Z = 26  # GPT-4 Sinyal
    AA = 27 # GPT-4 Analiz
    AB = 28 # Grok Sinyal
    AC = 29 # Grok Analiz

    # BÖLÜM 5: AI ASİSTAN (Robot 8)
    AD = 30 # Asistan Sinyal
    AE = 31 # Asistan Analiz

    # BÖLÜM 6: KOMUTA MERKEZİ (Robot 7)
    AF = 32 # KM Nihai Sinyal
    AG = 33 # KM Güven %
    AH = 34 # KM Meta-Analiz
    AI = 35 # Consensus %

    # BÖLÜM 7: RİSK YÖNETİMİ
    AJ = 36 # Giriş Fiyatı
    AK = 37 # Stop Loss
    AL = 38 # Take Profit 1
    AM = 39 # Take Profit 2
    AN = 40 # Risk/Ödül

    # BÖLÜM 8: DURUM
    AO = 41 # Robot Durumu
    AP = 42 # Notlar

def create_header_row() -> List[str]:
    """
    Create header row for Google Sheets

    Returns:
        List of column headers
    """
    headers = [
        # BÖLÜM 1-2: Piyasa + Göstergeler (Robot 1)
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

        # BÖLÜM 3: Haber Analizi (Robot 2)
        "Haber Özeti",       # T
        "Haber Duyarlılığı", # U

        # BÖLÜM 4: AI Analizleri (Robot 3 - 4 AI)
        "DeepSeek Sinyal",   # V
        "DeepSeek Analiz",   # W
        "Claude Sinyal",     # X
        "Claude Analiz",     # Y
        "GPT-4 Sinyal",      # Z
        "GPT-4 Analiz",      # AA
        "Grok Sinyal",       # AB
        "Grok Analiz",       # AC

        # BÖLÜM 5: AI Asistan (Robot 8)
        "Asistan Sinyal",    # AD
        "Asistan Analiz",    # AE

        # BÖLÜM 6: Komuta Merkezi (Robot 7)
        "KM Nihai Sinyal",   # AF
        "KM Güven %",        # AG
        "KM Meta-Analiz",    # AH
        "Consensus %",       # AI

        # BÖLÜM 7: Risk Yönetimi
        "Giriş Fiyatı",      # AJ
        "Stop Loss",         # AK
        "Take Profit 1",     # AL
        "Take Profit 2",     # AM
        "Risk/Ödül",         # AN

        # BÖLÜM 8: Durum
        "Robot Durumu",      # AO
        "Notlar",            # AP
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