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
    C = 3   # Fiyat (USD)
    D = 4   # Fiyat (TRY) - 🇹🇷 YENİ!
    E = 5   # Değişim %
    F = 6   # Hacim

    # BÖLÜM 2: TEKNİK GÖSTERGELER (Robot 1)
    G = 7   # RSI
    H = 8   # MACD
    I = 9   # MACD Sinyal
    J = 10  # MACD Histogram
    K = 11  # BB Üst
    L = 12  # BB Orta
    M = 13  # BB Alt
    N = 14  # EMA 9
    O = 15  # EMA 21
    P = 16  # EMA 50
    Q = 17  # EMA 200
    R = 18  # Destek
    S = 19  # Direnç
    T = 20  # Eğilim

    # BÖLÜM 3: ASİSTAN AI (Robot 8)
    U = 21  # Asistan AI Sinyal
    V = 22  # Asistan AI Analizi

    # BÖLÜM 4: ROBOT 3 - AI SİNYALLERİ (her AI için 2 sütun: sinyal + analiz)
    W = 23  # GPT-4 Sinyali
    X = 24  # GPT-4 Analizi
    Y = 25  # Claude Sinyali
    Z = 26  # Claude Analizi
    AA = 27 # Gemini Sinyali
    AB = 28 # Gemini Analizi
    AC = 29 # Grok Sinyali
    AD = 30 # Grok Analizi
    AE = 31 # DeepSeek Sinyali
    AF = 32 # DeepSeek Analizi

    # BÖLÜM 5: ROBOT 7 - KOMUTA MERKEZİ (Meta-Analiz & Telegram Paylaşım)
    AG = 33 # KM Nihai Sinyal (BUY/SELL/HOLD)
    AH = 34 # KM Güven % (0-100)
    AI = 35 # KM Meta-Analiz (Detaylı açıklama - Telegram'da paylaşılacak)
    AJ = 36 # KM Consensus % (AI'lar arası uyum)
    AK = 37 # KM Risk Değerlendirmesi (Düşük/Orta/Yüksek)
    AL = 38 # KM Önerilen Aksiyon (Telegram özeti)

    # BÖLÜM 6: RİSK YÖNETİMİ
    AM = 39 # Giriş Fiyatı
    AN = 40 # Zarar Durdur (Stop Loss)
    AO = 41 # Kar Al 1 (Take Profit 1)
    AP = 42 # Kar Al 2 (Take Profit 2)
    AQ = 43 # Risk/Ödül Oranı
    AR = 44 # Pozisyon Büyüklüğü %

    # BÖLÜM 7: NOTLAR VE UYARILAR
    AS = 45 # Genel Notlar
    AT = 46 # Uyarılar/Hatalar

    # BÖLÜM 8: ROBOT DURUMLARI (Her robot için ayrı sütun - sıralı)
    AU = 47 # Robot 1 Durum (Market Harvester)
    AV = 48 # Robot 2 Durum (News Analyzer)
    AW = 49 # Robot 3 Durum (AI Signal Generator)
    AX = 50 # Robot 4 Durum (Chart Generator)
    AY = 51 # Robot 5 Durum (Telegram Publisher)
    AZ = 52 # Robot 6 Durum (Performance Tracker)
    BA = 53 # Robot 7 Durum (AI Command Center)
    BB = 54 # Robot 8 Durum (Personal AI Analyst)

    # BÖLÜM 9: ROBOT 9 - TP/SL TAKİP (Real-Time Monitoring)
    BC = 55 # TP1 Vuruldu mu? (YES/NO)
    BD = 56 # TP2 Vuruldu mu? (YES/NO)
    BE = 57 # SL Vuruldu mu? (YES/NO)
    BF = 58 # Pozisyon Durumu (OPEN/CLOSED)
    BG = 59 # Robot 9 Durum (TP/SL Monitor)

def create_header_row() -> List[str]:
    """
    Create header row for Google Sheets

    Returns:
        List of column headers
    """
    headers = [
        # BÖLÜM 1-2: Piyasa + Göstergeler (Robot 1)
        "Zaman Damgası (Timestamp)",     # A
        "Piyasa (Market)",                # B
        "Fiyat USD (Price USD)",          # C
        "Fiyat TRY (Price TRY)",          # D
        "Değişim % (Change %)",           # E
        "Hacim (Volume)",                 # F
        "RSI",                            # G
        "MACD",                           # H
        "MACD Sinyal (MACD Signal)",     # I
        "MACD Hist (MACD Histogram)",    # J
        "BB Üst (BB Upper)",              # K
        "BB Orta (BB Middle)",            # L
        "BB Alt (BB Lower)",              # M
        "EMA 9",                          # N
        "EMA 21",                         # O
        "EMA 50",                         # P
        "EMA 200",                        # Q
        "Destek (Support)",               # R
        "Direnç (Resistance)",            # S
        "Eğilim (Trend)",                 # T

        # BÖLÜM 3: Asistan AI (Robot 8)
        "Asistan AI Sinyal (Assistant AI Signal)",     # U
        "Asistan AI Analizi (Assistant AI Analysis)",  # V

        # BÖLÜM 4: Robot 3 - AI Sinyalleri (5 AI x 2 sütun)
        "GPT-4 Sinyal (GPT-4 Signal)",              # W
        "GPT-4 Analiz (GPT-4 Analysis)",            # X
        "Claude Sinyal (Claude Signal)",            # Y
        "Claude Analiz (Claude Analysis)",          # Z
        "Gemini Sinyal (Gemini Signal)",            # AA
        "Gemini Analiz (Gemini Analysis)",          # AB
        "Grok Sinyal (Grok Signal)",                # AC
        "Grok Analiz (Grok Analysis)",              # AD
        "DeepSeek Sinyal (DeepSeek Signal)",        # AE
        "DeepSeek Analiz (DeepSeek Analysis)",      # AF

        # BÖLÜM 5: Robot 7 - Komuta Merkezi (Telegram İçeriği)
        "🎯 KM Nihai Sinyal (Final Signal)",           # AG
        "📊 KM Güven % (Confidence %)",                # AH
        "📝 KM Meta-Analiz (Meta-Analysis)",           # AI
        "🤝 KM Consensus % (AI Consensus %)",          # AJ
        "⚠️ KM Risk (Risk Level)",                     # AK
        "💡 KM Önerilen Aksiyon (Recommended Action)", # AL

        # BÖLÜM 6: Risk Yönetimi
        "💰 Giriş Fiyatı (Entry Price)",        # AM
        "🛑 Stop Loss",                          # AN
        "🎯 Take Profit 1",                      # AO
        "🚀 Take Profit 2",                      # AP
        "📈 Risk/Ödül (Risk/Reward)",           # AQ
        "📊 Pozisyon % (Position Size %)",      # AR

        # BÖLÜM 7: Notlar ve Uyarılar
        "📝 Notlar (Notes)",                     # AS
        "⚠️ Uyarılar (Warnings)",                # AT

        # BÖLÜM 8: Robot Durumları (Sıralı - 1'den 8'e)
        "✅ Robot 1 (Market Harvester)",         # AU
        "✅ Robot 2 (News Analyzer)",            # AV
        "✅ Robot 3 (AI Signal Generator)",      # AW
        "✅ Robot 4 (Chart Generator)",          # AX
        "✅ Robot 5 (Telegram Publisher)",       # AY
        "✅ Robot 6 (Performance Tracker)",      # AZ
        "✅ Robot 7 (AI Command Center)",        # BA
        "✅ Robot 8 (Personal AI Analyst)",      # BB

        # BÖLÜM 9: Robot 9 - TP/SL Takip
        "🎯 TP1 Vuruldu? (TP1 Hit?)",            # BC
        "🚀 TP2 Vuruldu? (TP2 Hit?)",            # BD
        "🛑 SL Vuruldu? (SL Hit?)",              # BE
        "📊 Pozisyon Durumu (Position Status)",  # BF
        "✅ Robot 9 (TP/SL Monitor)",            # BG
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