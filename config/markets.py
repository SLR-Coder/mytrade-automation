# config/markets.py
# -*- coding: utf-8 -*-
"""
Otomasyon için sabit piyasa listesi
5 Kategori = 25 Toplam Piyasa

TwelveData FREE TIER uyumlu semboller:
- FOREX: 7 parite (majör + TRY pariteleri) ✅
- CRYPTO: 5 coin (Binance API) ✅
- INDEX: 5 ETF (US indeksleri free tier'da çalışmıyor, ETF alternatifleri kullanılıyor)
- COMMODITY: 2 emtia (Altın/Gümüş - metals.live API ile)
- STOCK_CFD: 5 hisse ✅

NOT: TwelveData free tier'da SPX, NDX, DJI gibi US indeks sembolleri
"Grow" planı gerektiriyor. Bu yüzden ETF alternatifleri kullanılıyor.
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

    # INDEX: TwelveData free tier'da çalışan ETF sembolleri
    # Orijinal indeksler (SPX, NDX, DJI, NKY) Grow planı gerektiriyor
    "INDEX": [
        "SPY",      # S&P 500 ETF (SPDR)
        "QQQ",      # Nasdaq 100 ETF (Invesco)
        "DIA",      # Dow Jones ETF (SPDR)
        "EWG",      # Germany/DAX ETF (iShares)
        "EWJ",      # Japan/Nikkei ETF (iShares)
    ],

    # COMMODITY: Sadece metals.live API ile çalışan emtialar
    # Petrol ve doğalgaz TwelveData free tier'da çalışmıyor
    "COMMODITY": [
        "XAU/USD",  # Altın (metals.live API)
        "XAG/USD",  # Gümüş (metals.live API)
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
