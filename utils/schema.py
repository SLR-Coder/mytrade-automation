# utils/schema.py
# -*- coding: utf-8 -*-
"""
Google Sheets Schema - MyTrade Automation V2.0

YENİ DÜZEN (Aralık 2024):
- Bölüm 1: Robot 1 - Piyasa + Temel Göstergeler (A-T)
- Bölüm 2: Robot 1 - Gelişmiş SMC Göstergeleri (U-AF) ← YENİ
- Bölüm 3: Robot 8 - Kişisel AI (AG-AH)
- Bölüm 4: Robot 3 - AI Sinyalleri (AI-AR)
- Bölüm 5: Robot 7 - Komuta Merkezi (AS-AX)
- Bölüm 6: Risk Yönetimi (AY-BD)
- Bölüm 7: Robot 9 - TP/SL Takip (BE-BH)
- Bölüm 8: Notlar (BI-BJ)
- Bölüm 9: Robot Durumları (BK-BS)
"""

import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    import gspread

logger = logging.getLogger("Schema")


class ColumnMapping:
    """Google Sheets için sütun eşlemesi - YENİ DÜZEN"""

    # ═══════════════════════════════════════════════════════════════════
    # BÖLÜM 1: ROBOT 1 - PİYASA + TEMEL GÖSTERGELER (A-T) - 20 sütun
    # ═══════════════════════════════════════════════════════════════════
    A = 1   # Zaman Damgası
    B = 2   # Piyasa
    C = 3   # Fiyat (USD)
    D = 4   # Fiyat (TRY)
    E = 5   # Değişim %
    F = 6   # Hacim
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

    # ═══════════════════════════════════════════════════════════════════
    # BÖLÜM 2: ROBOT 1 - GELİŞMİŞ SMC GÖSTERGELERİ (U-AF) - 12 sütun ← YENİ
    # ═══════════════════════════════════════════════════════════════════
    U = 21  # FVG Durumu (Bullish FVG / Bearish FVG / -)
    V = 22  # FVG Aralığı (örn: 1.0545-1.0552)
    W = 23  # Liquidity Sweep (Sweep Up / Sweep Down / -)
    X = 24  # Sweep Seviyesi (sweep edilen pivot fiyatı)
    Y = 25  # RSI Divergence (Bullish Div / Bearish Div / -)
    Z = 26  # Structure Break (CHoCH Up / CHoCH Down / BOS Up / BOS Down / -)
    AA = 27 # Son Swing High
    AB = 28 # Son Swing Low
    AC = 29 # ADR (Average Daily Range - pip)
    AD = 30 # ADR Kullanım % (Exhaustion)
    AE = 31 # HTF Trend (1H: Uptrend / Downtrend / Sideways)
    AF = 32 # Session (London / New York / Asia)

    # ═══════════════════════════════════════════════════════════════════
    # BÖLÜM 3: ROBOT 8 - KİŞİSEL AI ANALİZİ (AG-AH) - 2 sütun
    # ═══════════════════════════════════════════════════════════════════
    AG = 33 # Asistan AI Sinyal (BUY/SELL/HOLD + %)
    AH = 34 # Asistan AI Analizi (Detaylı açıklama)

    # ═══════════════════════════════════════════════════════════════════
    # BÖLÜM 4: ROBOT 3 - AI SİNYALLERİ (AI-AR) - 10 sütun (5 AI x 2)
    # ═══════════════════════════════════════════════════════════════════
    AI = 35 # GPT-4 Sinyali
    AJ = 36 # GPT-4 Analizi
    AK = 37 # Claude Sinyali
    AL = 38 # Claude Analizi
    AM = 39 # Gemini Sinyali (Robot 3'teki Gemini, Robot 8'den farklı)
    AN = 40 # Gemini Analizi
    AO = 41 # Grok Sinyali
    AP = 42 # Grok Analizi
    AQ = 43 # DeepSeek Sinyali
    AR = 44 # DeepSeek Analizi

    # ═══════════════════════════════════════════════════════════════════
    # BÖLÜM 5: ROBOT 7 - KOMUTA MERKEZİ (AS-AX) - 6 sütun
    # ═══════════════════════════════════════════════════════════════════
    AS = 45 # KM Nihai Sinyal (BUY/SELL/HOLD)
    AT = 46 # KM Güven % (0-100)
    AU = 47 # KM Meta-Analiz (Detaylı açıklama)
    AV = 48 # KM Consensus % (AI'lar arası uyum)
    AW = 49 # KM Risk Değerlendirmesi (LOW/MEDIUM/HIGH)
    AX = 50 # KM Önerilen Aksiyon (ENTER/WAIT/AVOID)

    # ═══════════════════════════════════════════════════════════════════
    # BÖLÜM 6: RİSK YÖNETİMİ (AY-BD) - 6 sütun
    # ═══════════════════════════════════════════════════════════════════
    AY = 51 # Giriş Fiyatı (Entry Price)
    AZ = 52 # Stop Loss
    BA = 53 # Take Profit 1
    BB = 54 # Take Profit 2
    BC = 55 # Risk/Ödül Oranı (R:R)
    BD = 56 # Pozisyon Büyüklüğü %

    # ═══════════════════════════════════════════════════════════════════
    # BÖLÜM 7: ROBOT 9 - TP/SL TAKİP (BE-BH) - 4 sütun
    # ═══════════════════════════════════════════════════════════════════
    BE = 57 # TP1 Vuruldu mu? (YES/NO/-)
    BF = 58 # TP2 Vuruldu mu? (YES/NO/-)
    BG = 59 # SL Vuruldu mu? (YES/NO/-)
    BH = 60 # Pozisyon Durumu (OPEN/CLOSED/PARTIAL)

    # ═══════════════════════════════════════════════════════════════════
    # BÖLÜM 8: NOTLAR VE UYARILAR (BI-BJ) - 2 sütun
    # ═══════════════════════════════════════════════════════════════════
    BI = 61 # Genel Notlar
    BJ = 62 # Uyarılar/Hatalar

    # ═══════════════════════════════════════════════════════════════════
    # BÖLÜM 9: TÜM ROBOT DURUMLARI (BK-BS) - 9 sütun
    # ═══════════════════════════════════════════════════════════════════
    BK = 63 # Robot 1 Durum (Market Harvester)
    BL = 64 # Robot 2 Durum (News Analyzer)
    BM = 65 # Robot 3 Durum (AI Signal Generator)
    BN = 66 # Robot 4 Durum (Chart Generator)
    BO = 67 # Robot 5 Durum (Telegram Publisher)
    BP = 68 # Robot 6 Durum (Performance Tracker)
    BQ = 69 # Robot 7 Durum (AI Command Center)
    BR = 70 # Robot 8 Durum (Personal AI Analyst)
    BS = 71 # Robot 9 Durum (TP/SL Monitor)

    # ═══════════════════════════════════════════════════════════════════
    # YARDIMCI METODLAR
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def get_robot_status_column(cls, robot_no: int) -> int:
        """Robot numarasına göre durum sütununu döndür"""
        status_columns = {
            1: cls.BK,  # 63
            2: cls.BL,  # 64
            3: cls.BM,  # 65
            4: cls.BN,  # 66
            5: cls.BO,  # 67
            6: cls.BP,  # 68
            7: cls.BQ,  # 69
            8: cls.BR,  # 70
            9: cls.BS,  # 71
        }
        return status_columns.get(robot_no, cls.BK)

    @classmethod
    def get_ai_columns(cls, ai_name: str) -> tuple:
        """AI adına göre sinyal ve analiz sütunlarını döndür"""
        ai_columns = {
            "gpt4": (cls.AI, cls.AJ),      # 35, 36
            "claude": (cls.AK, cls.AL),    # 37, 38
            "gemini": (cls.AM, cls.AN),    # 39, 40
            "grok": (cls.AO, cls.AP),      # 41, 42
            "deepseek": (cls.AQ, cls.AR),  # 43, 44
        }
        return ai_columns.get(ai_name.lower(), (cls.AI, cls.AJ))


def create_header_row() -> List[str]:
    """
    Google Sheets için başlık satırı oluştur

    Returns:
        71 sütunluk başlık listesi
    """
    headers = [
        # ═══════════════════════════════════════════════════════════════
        # BÖLÜM 1: ROBOT 1 - PİYASA + TEMEL GÖSTERGELER (A-T)
        # ═══════════════════════════════════════════════════════════════
        "Zaman Damgası",           # A (1)
        "Piyasa",                  # B (2)
        "Fiyat USD",               # C (3)
        "Fiyat TRY",               # D (4)
        "Değişim %",               # E (5)
        "Hacim",                   # F (6)
        "RSI",                     # G (7)
        "MACD",                    # H (8)
        "MACD Sinyal",             # I (9)
        "MACD Histogram",          # J (10)
        "BB Üst",                  # K (11)
        "BB Orta",                 # L (12)
        "BB Alt",                  # M (13)
        "EMA 9",                   # N (14)
        "EMA 21",                  # O (15)
        "EMA 50",                  # P (16)
        "EMA 200",                 # Q (17)
        "Destek",                  # R (18)
        "Direnç",                  # S (19)
        "Eğilim",                  # T (20)

        # ═══════════════════════════════════════════════════════════════
        # BÖLÜM 2: ROBOT 1 - GELİŞMİŞ SMC GÖSTERGELERİ (U-AF) ← YENİ
        # ═══════════════════════════════════════════════════════════════
        "FVG Durumu",              # U (21)
        "FVG Aralığı",             # V (22)
        "Liquidity Sweep",         # W (23)
        "Sweep Seviyesi",          # X (24)
        "RSI Divergence",          # Y (25)
        "Structure Break",         # Z (26)
        "Swing High",              # AA (27)
        "Swing Low",               # AB (28)
        "ADR (pip)",               # AC (29)
        "ADR Kullanım %",          # AD (30)
        "HTF Trend (1H)",          # AE (31)
        "Session",                 # AF (32)

        # ═══════════════════════════════════════════════════════════════
        # BÖLÜM 3: ROBOT 8 - KİŞİSEL AI (AG-AH)
        # ═══════════════════════════════════════════════════════════════
        "🤖 Asistan AI Sinyal",    # AG (33)
        "📝 Asistan AI Analizi",   # AH (34)

        # ═══════════════════════════════════════════════════════════════
        # BÖLÜM 4: ROBOT 3 - AI SİNYALLERİ (AI-AR)
        # ═══════════════════════════════════════════════════════════════
        "GPT-4 Sinyal",            # AI (35)
        "GPT-4 Analiz",            # AJ (36)
        "Claude Sinyal",           # AK (37)
        "Claude Analiz",           # AL (38)
        "Gemini Sinyal",           # AM (39)
        "Gemini Analiz",           # AN (40)
        "Grok Sinyal",             # AO (41)
        "Grok Analiz",             # AP (42)
        "DeepSeek Sinyal",         # AQ (43)
        "DeepSeek Analiz",         # AR (44)

        # ═══════════════════════════════════════════════════════════════
        # BÖLÜM 5: ROBOT 7 - KOMUTA MERKEZİ (AS-AX)
        # ═══════════════════════════════════════════════════════════════
        "🎯 KM Nihai Sinyal",      # AS (45)
        "📊 KM Güven %",           # AT (46)
        "📝 KM Meta-Analiz",       # AU (47)
        "🤝 KM Consensus %",       # AV (48)
        "⚠️ KM Risk",              # AW (49)
        "💡 KM Aksiyon",           # AX (50)

        # ═══════════════════════════════════════════════════════════════
        # BÖLÜM 6: RİSK YÖNETİMİ (AY-BD)
        # ═══════════════════════════════════════════════════════════════
        "💰 Entry Price",          # AY (51)
        "🛑 Stop Loss",            # AZ (52)
        "🎯 Take Profit 1",        # BA (53)
        "🚀 Take Profit 2",        # BB (54)
        "📈 Risk/Ödül",            # BC (55)
        "📊 Pozisyon %",           # BD (56)

        # ═══════════════════════════════════════════════════════════════
        # BÖLÜM 7: ROBOT 9 - TP/SL TAKİP (BE-BH)
        # ═══════════════════════════════════════════════════════════════
        "🎯 TP1 Hit?",             # BE (57)
        "🚀 TP2 Hit?",             # BF (58)
        "🛑 SL Hit?",              # BG (59)
        "📊 Pozisyon Durumu",      # BH (60)

        # ═══════════════════════════════════════════════════════════════
        # BÖLÜM 8: NOTLAR (BI-BJ)
        # ═══════════════════════════════════════════════════════════════
        "📝 Notlar",               # BI (61)
        "⚠️ Uyarılar",             # BJ (62)

        # ═══════════════════════════════════════════════════════════════
        # BÖLÜM 9: ROBOT DURUMLARI (BK-BS)
        # ═══════════════════════════════════════════════════════════════
        "Robot 1 ✓",               # BK (63)
        "Robot 2 ✓",               # BL (64)
        "Robot 3 ✓",               # BM (65)
        "Robot 4 ✓",               # BN (66)
        "Robot 5 ✓",               # BO (67)
        "Robot 6 ✓",               # BP (68)
        "Robot 7 ✓",               # BQ (69)
        "Robot 8 ✓",               # BR (70)
        "Robot 9 ✓",               # BS (71)
    ]
    return headers


def resolve_columns(worksheet: "gspread.Worksheet") -> ColumnMapping:
    """
    Worksheet için sütun mapping'i döndür

    Args:
        worksheet: Google Sheets worksheet objesi

    Returns:
        ColumnMapping instance
    """
    return ColumnMapping()


# ═══════════════════════════════════════════════════════════════════
# SÜTUN GRUPLARI (Toplu işlemler için)
# ═══════════════════════════════════════════════════════════════════

# Robot 1 temel gösterge sütunları
ROBOT1_BASIC_COLS = list(range(1, 21))  # A-T (1-20)

# Robot 1 SMC gösterge sütunları
ROBOT1_SMC_COLS = list(range(21, 33))   # U-AF (21-32)

# Robot 8 sütunları
ROBOT8_COLS = [33, 34]  # AG-AH

# Robot 3 AI sütunları
ROBOT3_AI_COLS = list(range(35, 45))    # AI-AR (35-44)

# Robot 7 Komuta Merkezi sütunları
ROBOT7_COLS = list(range(45, 51))       # AS-AX (45-50)

# Risk Yönetimi sütunları
RISK_COLS = list(range(51, 57))         # AY-BD (51-56)

# Robot 9 TP/SL sütunları
ROBOT9_COLS = list(range(57, 61))       # BE-BH (57-60)

# Not sütunları
NOTE_COLS = [61, 62]                    # BI-BJ

# Robot durum sütunları
STATUS_COLS = list(range(63, 72))       # BK-BS (63-71)
