# Robot 6: Weekly Telegram Performance Report

## 📋 Amaç

Robot 6, son 7 günde kapatılan pozisyonları analiz eder ve **haftalık performans raporu**nu Telegram'a gönderir.

## 🎯 Özellikler

### 1. **Haftalık Performans Analizi**
- Son 7 günde kapatılan tüm pozisyonları toplar (Google Sheets'ten)
- Kazanç/kayıp istatistikleri hesaplar
- Piyasa bazında detay sunar

### 2. **Telegram Raporu**
Haftalık rapor şu bilgileri içerir:
- **Genel İstatistikler**: Toplam sinyal, kazanan/kaybeden, başarı oranı
- **Net Kazanç**: Toplam pips/yüzde
- **Profit Factor**: Kazançların kayıplara oranı
- **Ortalama Kazanç/Kayıp**: Ortalama trade başına
- **En İyi/Kötü İşlem**: Haftanın en iyi ve en kötü tradeleri
- **Piyasa Bazında Detay**: Her piyasa için ayrı performans
- **Son 5 İşlem**: Kronolojik son 5 kapalı pozisyon

### 3. **Örnek Rapor Formatı**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 HAFTALIK PERFORMANS RAPORU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 Tarih Aralığı:
18.01.2025 - 25.01.2025

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 GENEL İSTATİSTİKLER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Toplam Sinyal: 15 pozisyon
Kazanan: 10 ✅
Kaybeden: 5 ❌

💰 Başarı Oranı: 66.7%
📊 Net Kazanç: +285.5 pips
⚡ Profit Factor: 2.15

Ortalama Kazanç: +42.3 pips
Ortalama Kayıp: -18.7 pips

En İyi İşlem: +85.2 pips 🎯
En Kötü İşlem: -32.5 pips 🚨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 PİYASA BAZINDA DETAYLAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BTC/USDT: +3.85% ✅
  └─ 8 sinyal • %75 başarı

EUR/USD: +45.5 pips ✅
  └─ 4 sinyal • %50 başarı

GBP/USD: +32.0 pips ✅
  └─ 3 sinyal • %67 başarı

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 SON 5 İŞLEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BTC/USDT (LONG) - TP2
  +2.85% ✅

EUR/USD (SHORT) - TP1
  +25.5 pips ✅

GBP/USD (LONG) - SL
  -18.2 pips ❌

BTC/USDT (LONG) - TP1
  +1.45% ✅

EUR/USD (LONG) - TP2
  +38.7 pips ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Bu hafta toplam 15 pozisyon kapatıldı.
🎯 Başarı oranımız: %66.7

Bir sonraki rapora kadar başarılar! 🚀
```

## 🔧 Teknik Detaylar

### Google Sheets Kolonları

Robot 6 aşağıdaki kolonları **okur** (yazma yapmaz):

#### Okuma Kolonları:
- **A**: Timestamp (son 7 gün filtreleme için)
- **B**: Market Symbol
- **AG**: Final Signal (BUY/SELL/HOLD) - Robot 7'den
- **AM**: Entry Price - Robot 3'ten
- **AN**: Stop Loss - Robot 3'ten
- **AO**: Take Profit 1 - Robot 3'ten
- **AP**: Take Profit 2 - Robot 3'ten
- **BC**: TP1_HIT (YES/NO) - Robot 9'dan
- **BD**: TP2_HIT (YES/NO) - Robot 9'dan
- **BE**: SL_HIT (YES/NO) - Robot 9'dan
- **BF**: POSITION_STATUS (OPEN/CLOSED) - Robot 9'dan

#### Yazma Kolonları:
- **AZ**: Robot 6 Status ✅ (sadece status güncellemesi)

### Veri Akışı

```
1. Robot 7 → Final Signal (AG) + Entry/TP/SL (AM-AP)
2. Robot 9 → TP/SL hit tracking (BC-BE) + Position Status (BF)
3. Robot 6 → Google Sheets'ten oku + Haftalık rapor hesapla + Telegram'a gönder
```

### Kapalı Pozisyon Tespiti

Robot 6 sadece **kapalı pozisyonları** raporlar:
```python
# BF kolonu = "CLOSED" olanlar
if position_status != "CLOSED":
    continue  # Açık pozisyonları atla
```

### Çıkış Fiyatı Tespiti

Hangi seviyede kapandığına göre çıkış fiyatını belirler:
```python
if sl_hit == "YES":
    outcome = "SL"
    exit_price = sl_price
elif tp2_hit == "YES":
    outcome = "TP2"
    exit_price = tp2_price
elif tp1_hit == "YES":
    outcome = "TP1"
    exit_price = tp1_price
```

### Kâr/Zarar Hesaplama

#### Forex (pips):
```python
# JPY çiftleri için: 1 pip = 0.01
if "JPY" in market:
    pips = abs(exit - entry) * 100

# Diğer çiftler için: 1 pip = 0.0001
else:
    pips = abs(exit - entry) * 10000
```

#### Crypto (yüzde):
```python
# Yüzde olarak hesapla
pct = ((exit - entry) / entry) * 100
```

### İstatistik Hesaplamaları

```python
stats = {
    "total_trades": len(trades),
    "winning_trades": len([t for t in trades if t["profit"] > 0]),
    "losing_trades": len([t for t in trades if t["profit"] <= 0]),
    "win_rate": (winning_trades / total_trades * 100),
    "total_pips": sum(t["profit"] for t in trades),  # Net
    "avg_win": sum(profits) / len(profits),
    "avg_loss": sum(losses) / len(losses),
    "profit_factor": abs(sum(profits) / sum(losses)),
    "best_trade": max(profits),
    "worst_trade": min(losses),
    "trades_by_market": {...}  # Piyasa bazında detay
}
```

## ⏱️ Zamanlama

**CRON**: Her Pazar günü saat 00:00 (UTC)

```bash
# Cloud Scheduler
0 0 * * 0 /app/scripts/run_weekly_report.sh
```

Alternatif zamanlamalar:
- **Her Cuma 18:00**: `0 18 * * 5` (hafta sonu öncesi)
- **Her Pazar 09:00**: `0 9 * * 0` (hafta başı)
- **Her Pazartesi 00:00**: `0 0 * * 1` (yeni hafta)

## 🔗 Diğer Robotlarla Entegrasyon

### Robot 7 (Command Center):
- Final Signal (AG) → Robot 6 bunu okur
- Entry/TP/SL (AM-AP) → Robot 6 bunu okur

### Robot 9 (TP/SL Monitor):
- TP/SL hit status (BC-BE) → Robot 6 bunu okur
- Position Status (BF) → Robot 6 sadece CLOSED olanları raporlar

**Veri Akışı:**
```
Robot 7 → Sinyal + Risk → Google Sheets
Robot 9 → TP/SL izleme → Google Sheets (hit status + CLOSED)
Robot 6 → Google Sheets'ten oku → Telegram rapor gönder
```

## 🚨 Önemli Notlar

### 1. **Haftalık Periyot**
- Son 7 günü tarar (timestamp'e göre)
- Yalnızca `BF = "CLOSED"` pozisyonları dahil eder
- Açık pozisyonlar raporlanmaz (Robot 9 onları izler)

### 2. **Boş Rapor**
Eğer son 7 günde kapalı pozisyon yoksa:
```
📊 HAFTALIK PERFORMANS RAPORU

Son 7 günde kapalı pozisyon yok.

Yeni fırsatları bekliyoruz! 🎯
```

### 3. **Forex vs Crypto**
- **Forex**: Pips olarak gösterir (örn: +45.5 pips)
- **Crypto**: Yüzde olarak gösterir (örn: +3.85%)

### 4. **Piyasa Bazında Sıralama**
Raporun piyasa detayları bölümünde:
- En karlı piyasa en üstte
- En zararlı piyasa en altta
- Her piyasa için toplam sinyal sayısı ve başarı oranı

## 📊 Örnek Senaryolar

### Senaryo 1: Başarılı Hafta

```
15 trade, 10 kazanan, 5 kaybeden
Win Rate: 66.7%
Net: +285.5 pips
Profit Factor: 2.15
```

### Senaryo 2: Kayıplı Hafta

```
10 trade, 3 kazanan, 7 kaybeden
Win Rate: 30.0%
Net: -125.3 pips
Profit Factor: 0.45
```

### Senaryo 3: Boş Hafta

```
0 trade
Mesaj: "Son 7 günde kapalı pozisyon yok."
```

## 🐛 Hata Ayıklama

### Log Mesajları

```bash
# Başarılı çalışma
📊 ROBOT 6: WEEKLY TELEGRAM REPORT - BAŞLAT
📊 Collecting trades from last 7 days...
  ✅ Found 15 closed trades

📊 HAFTALIK İSTATİSTİKLER:
  Toplam İşlem: 15
  Kazanan: 10 ✅
  Kaybeden: 5 ❌
  Başarı Oranı: 66.7%
  Net Kazanç: +285.5 pips
  Profit Factor: 2.15

  ✅ Haftalık rapor Telegram'a gönderildi
✅ ROBOT 6 TAMAMLANDI
```

### Sorun Giderme

**Sorun**: Rapor boş
```bash
# Kontrol et:
1. Son 7 günde BF = "CLOSED" olan satır var mı?
2. Timestamp formatı doğru mu?
3. Entry/Exit fiyatları parse ediliyor mu?
```

**Sorun**: Telegram'a gönderilmiyor
```bash
# Kontrol et:
1. TELEGRAM_BOT_TOKEN doğru mu?
2. TELEGRAM_CHAT_ID doğru mu?
3. Bot chat'e eklenmiş mi?
```

**Sorun**: Pips yanlış hesaplanıyor
```bash
# Kontrol et:
1. Forex/Crypto tespiti doğru mu? ("/" var mı sembolde?)
2. JPY çifti mi? (100x multiplier)
3. Entry/Exit fiyatları doğru parse edildi mi?
```

## 📈 Metrikler

Robot 6 haftalık olarak şu metrikleri raporlar:
- Toplam işlem sayısı
- Kazanan/kaybeden oranı
- Başarı yüzdesi (win rate)
- Net kazanç/kayıp (pips veya %)
- Profit factor
- Ortalama kazanç/kayıp
- En iyi/kötü işlem
- Piyasa bazında performans

---

**Haftalık performansınızı Telegram'dan takip edin!** 📊📱
