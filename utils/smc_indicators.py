# utils/smc_indicators.py
# -*- coding: utf-8 -*-
"""
SMC (Smart Money Concepts) Göstergeleri

Bu modül profesyonel trading için gelişmiş SMC göstergelerini hesaplar:
- Fair Value Gap (FVG)
- Liquidity Sweep
- RSI Divergence
- Structure Break (CHoCH/BOS)
- ADR (Average Daily Range)
- HTF Trend
- Session Detection
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import pytz

logger = logging.getLogger("SMC-Indicators")


# ═══════════════════════════════════════════════════════════════════
# FAIR VALUE GAP (FVG) TESPİTİ
# ═══════════════════════════════════════════════════════════════════

def detect_fvg(candles: List[Dict], min_gap_pips: float = 3.0) -> Dict:
    """
    Fair Value Gap (FVG) tespit et

    FVG, 3 ardışık mumda oluşan fiyat boşluğudur:
    - Bullish FVG: candle[0].high < candle[2].low (ortada yukarı boşluk)
    - Bearish FVG: candle[0].low > candle[2].high (ortada aşağı boşluk)

    Args:
        candles: Son 3+ mum verisi [oldest, ..., newest]
                 Her mum: {"open": x, "high": x, "low": x, "close": x}
        min_gap_pips: Minimum gap büyüklüğü (pip)

    Returns:
        {
            "detected": True/False,
            "type": "Bullish FVG" / "Bearish FVG" / None,
            "range": "1.0545-1.0552" / None,
            "gap_pips": float
        }
    """
    result = {
        "detected": False,
        "type": None,
        "range": None,
        "gap_pips": 0
    }

    if len(candles) < 3:
        return result

    # Son 3 mum (oldest to newest)
    c1 = candles[-3]  # En eski
    c2 = candles[-2]  # Orta
    c3 = candles[-1]  # En yeni

    try:
        # Bullish FVG: c1.high < c3.low (gap yukarı)
        if c1["high"] < c3["low"]:
            gap = c3["low"] - c1["high"]
            gap_pips = gap * 10000  # Forex için pip hesabı

            if gap_pips >= min_gap_pips:
                result["detected"] = True
                result["type"] = "Bullish FVG"
                result["range"] = f"{c1['high']:.5f}-{c3['low']:.5f}"
                result["gap_pips"] = round(gap_pips, 1)
                return result

        # Bearish FVG: c1.low > c3.high (gap aşağı)
        if c1["low"] > c3["high"]:
            gap = c1["low"] - c3["high"]
            gap_pips = gap * 10000

            if gap_pips >= min_gap_pips:
                result["detected"] = True
                result["type"] = "Bearish FVG"
                result["range"] = f"{c3['high']:.5f}-{c1['low']:.5f}"
                result["gap_pips"] = round(gap_pips, 1)
                return result

    except (KeyError, TypeError) as e:
        logger.warning(f"FVG hesaplama hatası: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════
# LIQUIDITY SWEEP TESPİTİ
# ═══════════════════════════════════════════════════════════════════

def detect_liquidity_sweep(
    candles: List[Dict],
    swing_high: float,
    swing_low: float,
    min_sweep_pips: float = 3.0
) -> Dict:
    """
    Liquidity Sweep tespit et

    Sweep, fiyatın bir pivot seviyesini geçici olarak kırıp geri dönmesidir:
    - Sweep Up: Fiyat swing high'ı kırdı ama mum kapanışı altında
    - Sweep Down: Fiyat swing low'u kırdı ama mum kapanışı üstünde

    Args:
        candles: Son 5+ mum verisi
        swing_high: Son swing high seviyesi
        swing_low: Son swing low seviyesi
        min_sweep_pips: Minimum sweep mesafesi (pip)

    Returns:
        {
            "detected": True/False,
            "type": "Sweep Up" / "Sweep Down" / None,
            "level": float (sweep edilen seviye),
            "sweep_pips": float
        }
    """
    result = {
        "detected": False,
        "type": None,
        "level": None,
        "sweep_pips": 0
    }

    if len(candles) < 2 or not swing_high or not swing_low:
        return result

    # Son mumu kontrol et
    last_candle = candles[-1]

    try:
        # Sweep Up: High > swing_high ama Close < swing_high
        if last_candle["high"] > swing_high and last_candle["close"] < swing_high:
            sweep = last_candle["high"] - swing_high
            sweep_pips = sweep * 10000

            if sweep_pips >= min_sweep_pips:
                result["detected"] = True
                result["type"] = "Sweep Up"
                result["level"] = swing_high
                result["sweep_pips"] = round(sweep_pips, 1)
                return result

        # Sweep Down: Low < swing_low ama Close > swing_low
        if last_candle["low"] < swing_low and last_candle["close"] > swing_low:
            sweep = swing_low - last_candle["low"]
            sweep_pips = sweep * 10000

            if sweep_pips >= min_sweep_pips:
                result["detected"] = True
                result["type"] = "Sweep Down"
                result["level"] = swing_low
                result["sweep_pips"] = round(sweep_pips, 1)
                return result

    except (KeyError, TypeError) as e:
        logger.warning(f"Liquidity Sweep hesaplama hatası: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════
# RSI DIVERGENCE TESPİTİ
# ═══════════════════════════════════════════════════════════════════

def detect_rsi_divergence(
    prices: List[float],
    rsi_values: List[float],
    lookback: int = 10
) -> Dict:
    """
    RSI Divergence tespit et

    - Bullish Divergence: Fiyat lower low yaparken RSI higher low yapıyor
    - Bearish Divergence: Fiyat higher high yaparken RSI lower high yapıyor

    Args:
        prices: Son N fiyat listesi [oldest, ..., newest]
        rsi_values: Son N RSI değeri listesi
        lookback: Kaç mum geriye bakılacak

    Returns:
        {
            "detected": True/False,
            "type": "Bullish Div" / "Bearish Div" / None,
            "strength": "Strong" / "Regular" / "Hidden"
        }
    """
    result = {
        "detected": False,
        "type": None,
        "strength": None
    }

    if len(prices) < lookback or len(rsi_values) < lookback:
        return result

    # Son lookback veriyi al
    prices = prices[-lookback:]
    rsi_values = rsi_values[-lookback:]

    try:
        # Pivot noktaları bul (basit yaklaşım: min/max)
        price_min_idx = prices.index(min(prices))
        price_max_idx = prices.index(max(prices))

        current_price = prices[-1]
        current_rsi = rsi_values[-1]

        # Son pivot ile şimdiyi karşılaştır
        pivot_low_price = min(prices[:-2]) if len(prices) > 2 else prices[0]
        pivot_low_rsi = rsi_values[prices.index(pivot_low_price)] if pivot_low_price in prices else rsi_values[0]

        pivot_high_price = max(prices[:-2]) if len(prices) > 2 else prices[0]
        pivot_high_rsi = rsi_values[prices.index(pivot_high_price)] if pivot_high_price in prices else rsi_values[0]

        # Bullish Divergence: Fiyat lower low, RSI higher low
        if current_price < pivot_low_price and current_rsi > pivot_low_rsi:
            result["detected"] = True
            result["type"] = "Bullish Div"
            result["strength"] = "Regular" if current_rsi < 40 else "Hidden"
            return result

        # Bearish Divergence: Fiyat higher high, RSI lower high
        if current_price > pivot_high_price and current_rsi < pivot_high_rsi:
            result["detected"] = True
            result["type"] = "Bearish Div"
            result["strength"] = "Regular" if current_rsi > 60 else "Hidden"
            return result

    except (ValueError, IndexError) as e:
        logger.warning(f"RSI Divergence hesaplama hatası: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════
# STRUCTURE BREAK TESPİTİ (CHoCH / BOS)
# ═══════════════════════════════════════════════════════════════════

def detect_structure_break(
    candles: List[Dict],
    swing_high: float,
    swing_low: float,
    previous_trend: str = "unknown"
) -> Dict:
    """
    Structure Break tespit et

    - CHoCH (Change of Character): Trend değişimi sinyali
      - CHoCH Up: Downtrend'de swing high kırılması
      - CHoCH Down: Uptrend'de swing low kırılması

    - BOS (Break of Structure): Trend devamı sinyali
      - BOS Up: Uptrend'de swing high kırılması
      - BOS Down: Downtrend'de swing low kırılması

    Args:
        candles: Son 5+ mum verisi
        swing_high: Son swing high
        swing_low: Son swing low
        previous_trend: "uptrend" / "downtrend" / "unknown"

    Returns:
        {
            "detected": True/False,
            "type": "CHoCH Up" / "CHoCH Down" / "BOS Up" / "BOS Down" / None,
            "level": float (kırılan seviye)
        }
    """
    result = {
        "detected": False,
        "type": None,
        "level": None
    }

    if len(candles) < 2 or not swing_high or not swing_low:
        return result

    last_candle = candles[-1]
    prev_candle = candles[-2]

    try:
        # Swing High kırılması (Close üstünde)
        if last_candle["close"] > swing_high and prev_candle["close"] <= swing_high:
            result["detected"] = True
            result["level"] = swing_high

            if previous_trend == "downtrend":
                result["type"] = "CHoCH Up"  # Trend değişimi
            else:
                result["type"] = "BOS Up"    # Trend devamı
            return result

        # Swing Low kırılması (Close altında)
        if last_candle["close"] < swing_low and prev_candle["close"] >= swing_low:
            result["detected"] = True
            result["level"] = swing_low

            if previous_trend == "uptrend":
                result["type"] = "CHoCH Down"  # Trend değişimi
            else:
                result["type"] = "BOS Down"    # Trend devamı
            return result

    except (KeyError, TypeError) as e:
        logger.warning(f"Structure Break hesaplama hatası: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════
# SWING HIGH/LOW HESAPLAMA
# ═══════════════════════════════════════════════════════════════════

def calculate_swing_points(candles: List[Dict], lookback: int = 5) -> Dict:
    """
    Swing High ve Swing Low noktalarını hesapla

    Args:
        candles: Mum verileri listesi
        lookback: Kaç mum geriye bakılacak

    Returns:
        {
            "swing_high": float,
            "swing_low": float,
            "swing_high_idx": int,
            "swing_low_idx": int
        }
    """
    result = {
        "swing_high": None,
        "swing_low": None,
        "swing_high_idx": None,
        "swing_low_idx": None
    }

    if len(candles) < lookback:
        return result

    try:
        highs = [c["high"] for c in candles[-lookback:]]
        lows = [c["low"] for c in candles[-lookback:]]

        result["swing_high"] = max(highs)
        result["swing_low"] = min(lows)
        result["swing_high_idx"] = highs.index(result["swing_high"])
        result["swing_low_idx"] = lows.index(result["swing_low"])

    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"Swing point hesaplama hatası: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════
# ADR (AVERAGE DAILY RANGE) HESAPLAMA
# ═══════════════════════════════════════════════════════════════════

def calculate_adr(
    daily_candles: List[Dict],
    period: int = 14
) -> Dict:
    """
    Average Daily Range (ADR) hesapla

    Args:
        daily_candles: Günlük mum verileri (son 14+ gün)
        period: Ortalama alınacak gün sayısı

    Returns:
        {
            "adr_pips": float (ortalama günlük range),
            "today_range_pips": float (bugünkü range),
            "exhaustion_pct": float (bugün kullanılan ADR yüzdesi),
            "is_exhausted": bool (>90% kullanıldı mı)
        }
    """
    result = {
        "adr_pips": 0,
        "today_range_pips": 0,
        "exhaustion_pct": 0,
        "is_exhausted": False
    }

    if len(daily_candles) < 2:
        return result

    try:
        # Son N günün range'lerini hesapla
        ranges = []
        for candle in daily_candles[-period:]:
            daily_range = candle["high"] - candle["low"]
            ranges.append(daily_range)

        # ADR (ortalama)
        adr = sum(ranges) / len(ranges) if ranges else 0
        adr_pips = adr * 10000  # Forex için

        # Bugünkü range
        today = daily_candles[-1]
        today_range = today["high"] - today["low"]
        today_pips = today_range * 10000

        # Exhaustion yüzdesi
        exhaustion = (today_range / adr * 100) if adr > 0 else 0

        result["adr_pips"] = round(adr_pips, 1)
        result["today_range_pips"] = round(today_pips, 1)
        result["exhaustion_pct"] = round(exhaustion, 1)
        result["is_exhausted"] = exhaustion >= 90

    except (KeyError, TypeError, ZeroDivisionError) as e:
        logger.warning(f"ADR hesaplama hatası: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════
# HTF TREND TESPİTİ
# ═══════════════════════════════════════════════════════════════════

def detect_htf_trend(
    price: float,
    htf_ema_200: float,
    htf_ema_50: Optional[float] = None
) -> Dict:
    """
    Higher Timeframe (1H) trend tespit et

    Args:
        price: Mevcut fiyat
        htf_ema_200: 1H EMA 200 değeri
        htf_ema_50: 1H EMA 50 değeri (opsiyonel)

    Returns:
        {
            "trend": "Uptrend" / "Downtrend" / "Sideways",
            "strength": "Strong" / "Weak",
            "price_vs_ema": "Above" / "Below"
        }
    """
    result = {
        "trend": "Sideways",
        "strength": "Weak",
        "price_vs_ema": "At"
    }

    if not htf_ema_200:
        return result

    try:
        # Fiyat EMA200'e göre nerede?
        pct_diff = ((price - htf_ema_200) / htf_ema_200) * 100

        if pct_diff > 0.5:  # %0.5 üstünde
            result["trend"] = "Uptrend"
            result["price_vs_ema"] = "Above"
            result["strength"] = "Strong" if pct_diff > 1.5 else "Weak"
        elif pct_diff < -0.5:  # %0.5 altında
            result["trend"] = "Downtrend"
            result["price_vs_ema"] = "Below"
            result["strength"] = "Strong" if pct_diff < -1.5 else "Weak"
        else:
            result["trend"] = "Sideways"
            result["price_vs_ema"] = "At"
            result["strength"] = "Weak"

        # EMA50 varsa daha detaylı analiz
        if htf_ema_50:
            if price > htf_ema_50 > htf_ema_200:
                result["strength"] = "Strong"
            elif price < htf_ema_50 < htf_ema_200:
                result["strength"] = "Strong"

    except (TypeError, ZeroDivisionError) as e:
        logger.warning(f"HTF Trend hesaplama hatası: {e}")

    return result


# ═══════════════════════════════════════════════════════════════════
# SESSION TESPİTİ
# ═══════════════════════════════════════════════════════════════════

def detect_session(utc_time: Optional[datetime] = None) -> Dict:
    """
    Aktif trading session'ı tespit et

    Sessions (UTC+3 / Istanbul):
    - Asia: 00:00 - 08:00 (düşük volatilite)
    - London: 08:00 - 12:00 (yüksek volatilite)
    - London-NY Overlap: 13:30 - 17:00 (en yüksek volatilite)
    - New York: 13:30 - 22:00 (yüksek volatilite)

    Args:
        utc_time: UTC zaman (None ise şimdiki zaman)

    Returns:
        {
            "session": "London" / "New York" / "Asia" / "Closed",
            "quality": "High" / "Medium" / "Low",
            "is_overlap": bool
        }
    """
    if utc_time is None:
        utc_time = datetime.now(timezone.utc)

    # Istanbul saatine çevir (UTC+3)
    istanbul_tz = pytz.timezone('Europe/Istanbul')
    istanbul_time = utc_time.astimezone(istanbul_tz)
    hour = istanbul_time.hour

    result = {
        "session": "Closed",
        "quality": "Low",
        "is_overlap": False
    }

    # Session tespiti
    if 0 <= hour < 8:
        result["session"] = "Asia"
        result["quality"] = "Low"
    elif 8 <= hour < 12:
        result["session"] = "London"
        result["quality"] = "High"
    elif 12 <= hour < 13:
        result["session"] = "London"
        result["quality"] = "Medium"
    elif 13 <= hour < 17:
        result["session"] = "London-NY"
        result["quality"] = "High"
        result["is_overlap"] = True
    elif 17 <= hour < 22:
        result["session"] = "New York"
        result["quality"] = "Medium"
    else:
        result["session"] = "Closed"
        result["quality"] = "Low"

    return result


# ═══════════════════════════════════════════════════════════════════
# TÜM SMC GÖSTERGELERİNİ HESAPLA
# ═══════════════════════════════════════════════════════════════════

def calculate_all_smc_indicators(
    candles_5m: List[Dict],
    candles_1h: List[Dict],
    candles_daily: List[Dict],
    rsi_values: List[float],
    current_price: float,
    htf_ema_200: float,
    previous_trend: str = "unknown"
) -> Dict:
    """
    Tüm SMC göstergelerini tek seferde hesapla

    Args:
        candles_5m: 5 dakikalık mumlar (son 20+)
        candles_1h: 1 saatlik mumlar (HTF için)
        candles_daily: Günlük mumlar (ADR için)
        rsi_values: RSI değerleri listesi
        current_price: Mevcut fiyat
        htf_ema_200: 1H EMA200
        previous_trend: Önceki trend

    Returns:
        Tüm SMC göstergeleri dict olarak
    """
    # Swing Points
    swings = calculate_swing_points(candles_5m, lookback=10)
    swing_high = swings["swing_high"]
    swing_low = swings["swing_low"]

    # FVG
    fvg = detect_fvg(candles_5m)

    # Liquidity Sweep
    sweep = detect_liquidity_sweep(candles_5m, swing_high, swing_low)

    # RSI Divergence
    prices = [c["close"] for c in candles_5m] if candles_5m else []
    divergence = detect_rsi_divergence(prices, rsi_values)

    # Structure Break
    structure = detect_structure_break(candles_5m, swing_high, swing_low, previous_trend)

    # ADR
    adr = calculate_adr(candles_daily)

    # HTF Trend
    htf = detect_htf_trend(current_price, htf_ema_200)

    # Session
    session = detect_session()

    return {
        # FVG
        "fvg_status": fvg["type"] if fvg["detected"] else "-",
        "fvg_range": fvg["range"] if fvg["detected"] else "-",

        # Liquidity Sweep
        "sweep_status": sweep["type"] if sweep["detected"] else "-",
        "sweep_level": f"{sweep['level']:.5f}" if sweep["detected"] else "-",

        # RSI Divergence
        "divergence_status": divergence["type"] if divergence["detected"] else "-",

        # Structure Break
        "structure_status": structure["type"] if structure["detected"] else "-",

        # Swing Points
        "swing_high": f"{swing_high:.5f}" if swing_high else "-",
        "swing_low": f"{swing_low:.5f}" if swing_low else "-",

        # ADR
        "adr_pips": f"{adr['adr_pips']:.0f}" if adr["adr_pips"] else "-",
        "adr_exhaustion": f"{adr['exhaustion_pct']:.0f}%" if adr["exhaustion_pct"] else "-",

        # HTF Trend
        "htf_trend": htf["trend"],

        # Session
        "session": session["session"],
        "session_quality": session["quality"]
    }
