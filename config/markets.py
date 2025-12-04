# config/markets.py
# -*- coding: utf-8 -*-
"""
Otomasyon için sabit piyasa listesi
5 Kategori = 24 Toplam Piyasa

TwelveData GROW PLAN ($79/ay):
- 377 API credit/dakika (rate limit neredeyse yok)
- Günlük limit YOK
- FOREX: 7 parite (majör + TRY pariteleri) ✅
- CRYPTO: 5 coin (Binance API - daha hızlı) ✅
- INDEX: 5 ETF ✅
- COMMODITY: 2 emtia (XAU/USD, XAG/USD - TwelveData ile) ✅
- STOCK_CFD: 5 hisse ✅
"""

# OTOMASYON İÇİN 24 PİYASA (5 kategori)
MARKETS = {
    "FOREX": [
        "EUR/USD",
        "USD/JPY",
        "GBP/USD",
        "USD/CHF",
        "AUD/USD",
        "USD/TRY",  # Türk Lirası
        "EUR/TRY",  # Euro/Türk Lirası
    ],

    "CRYPTO": [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "XRP/USDT",
        "BNB/USDT",
    ],

    # INDEX: ETF sembolleri (likidite ve spread açısından daha iyi)
    "INDEX": [
        "SPY",      # S&P 500 ETF (SPDR)
        "QQQ",      # Nasdaq 100 ETF (Invesco)
        "DIA",      # Dow Jones ETF (SPDR)
        "EWG",      # Germany/DAX ETF (iShares)
        "EWJ",      # Japan/Nikkei ETF (iShares)
    ],

    # COMMODITY: TwelveData Grow plan ile destekleniyor
    "COMMODITY": [
        "XAU/USD",  # Altın (TwelveData)
        "XAG/USD",  # Gümüş (TwelveData)
    ],

    "STOCK_CFD": [
        "NVDA",     # NVIDIA
        "AAPL",     # Apple
        "TSLA",     # Tesla
        "MSFT",     # Microsoft
        "AMZN",     # Amazon
    ],
}

# Tüm piyasaları tek listede
ALL_MARKETS = []
for category, symbols in MARKETS.items():
    ALL_MARKETS.extend(symbols)

# Kategori başına piyasa sayısı
MARKETS_PER_CATEGORY = 5
TOTAL_MARKETS = len(ALL_MARKETS)

# Piyasa kategorisi mapping
MARKET_CATEGORIES = {}
for category, symbols in MARKETS.items():
    for symbol in symbols:
        MARKET_CATEGORIES[symbol] = category


def get_all_markets():
    """Tüm piyasaları döndür"""
    return ALL_MARKETS.copy()


def get_markets_by_category(category: str):
    """Kategoriye göre piyasaları döndür"""
    return MARKETS.get(category.upper(), []).copy()


def get_market_category(symbol: str):
    """Piyasanın kategorisini döndür"""
    return MARKET_CATEGORIES.get(symbol, "UNKNOWN")


def get_market_info():
    """Piyasa bilgilerini döndür"""
    return {
        "total": TOTAL_MARKETS,
        "categories": len(MARKETS),
        "per_category": MARKETS_PER_CATEGORY,
        "breakdown": {cat: len(syms) for cat, syms in MARKETS.items()}
    }
