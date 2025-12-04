# Robot 9: TP/SL Monitor (Real-Time Tracking)

## 📋 Amaç

Robot 9, açık pozisyonları **gerçek zamanlı** izler ve Take Profit (TP1, TP2) veya Stop Loss (SL) seviyelerine ulaşıldığında **Telegram bildirimi** gönderir.

## 🎯 Özellikler

### 1. **Gerçek Zamanlı İzleme**
- Her 1-5 dakikada bir çalışır
- Açık pozisyonları (BUY/SELL) kontrol eder
- Mevcut fiyatları data provider'lardan çeker

### 2. **Hedef Takibi**
- **TP1 Vuruldu**: İlk kar hedefine ulaşıldığında bildirim
- **TP2 Vuruldu**: İkinci kar hedefine ulaşıldığında bildirim + pozisyon kapatılır
- **SL Vuruldu**: Stop loss seviyesine ulaşıldığında bildirim + pozisyon kapatılır

### 3. **Telegram Bildirimleri**

#### TP Hit Notification:
```
━━━━━━━━━━━━━━━━━━━━━━
🎯 HEDEF VURULDU! 💸
━━━━━━━━━━━━━━━━━━━━━━

Market: BTC/USDT
Pozisyon: LONG
Hedef: TP1 ✅

📊 FİYAT BİLGİSİ:
├─ Giriş: $95,000.00
├─ Hedef: $98,000.00
└─ Şu Anki: $98,150.00

💰 KÂR: +3.16% 🤑

Tebrikler! Hedef başarıyla vuruldu! 🎉
```

#### SL Hit Notification:
```
━━━━━━━━━━━━━━━━━━━━━━
🚨 STOP LOSS VURULDU!
━━━━━━━━━━━━━━━━━━━━━━

Market: BTC/USDT
Pozisyon: LONG

📊 FİYAT BİLGİSİ:
├─ Giriş: $95,000.00
├─ Stop Loss: $93,000.00
└─ Şu Anki: $92,800.00

📉 ZARAR: -2.32% 😔

Pozisyon kapatıldı. Bir sonraki fırsatı kolluyoruz! 💪
```

## 🔧 Teknik Detaylar

### Google Sheets Kolonları

Robot 9 aşağıdaki kolonları kullanır:

#### Giriş Kolonları (Okuma):
- **AG**: Final Signal (BUY/SELL/HOLD) - Robot 7'den
- **AM**: Entry Price (Giriş Fiyatı) - Robot 3'ten
- **AN**: Stop Loss - Robot 3'ten
- **AO**: Take Profit 1 - Robot 3'ten
- **AP**: Take Profit 2 - Robot 3'ten
- **B**: Market Symbol

#### Çıkış Kolonları (Yazma):
- **BC**: TP1_HIT (YES/NO) - TP1 vuruldu mu?
- **BD**: TP2_HIT (YES/NO) - TP2 vuruldu mu?
- **BE**: SL_HIT (YES/NO) - SL vuruldu mu?
- **BF**: POSITION_STATUS (OPEN/CLOSED) - Pozisyon durumu
- **BG**: Robot 9 Status ✅

### Hit Detection Mantığı

#### BUY Pozisyonu için:
```python
# TP1 Hit: Mevcut fiyat >= TP1
if current_price >= tp1_price:
    send_tp1_notification()

# TP2 Hit: Mevcut fiyat >= TP2
if current_price >= tp2_price:
    send_tp2_notification()
    close_position()

# SL Hit: Mevcut fiyat <= SL
if current_price <= sl_price:
    send_sl_notification()
    close_position()
```

#### SELL Pozisyonu için:
```python
# TP1 Hit: Mevcut fiyat <= TP1
if current_price <= tp1_price:
    send_tp1_notification()

# TP2 Hit: Mevcut fiyat <= TP2
if current_price <= tp2_price:
    send_tp2_notification()
    close_position()

# SL Hit: Mevcut fiyat >= SL
if current_price >= sl_price:
    send_sl_notification()
    close_position()
```

### Kâr/Zarar Hesaplama

#### Forex Piyasaları (EUR/USD, GBP/USD, vb.):
```python
# JPY çiftleri için: 1 pip = 0.01
if "JPY" in market:
    pips = abs(current - entry) * 100

# Diğer çiftler için: 1 pip = 0.0001
else:
    pips = abs(current - entry) * 10000
```

#### Kripto Piyasaları (BTC/USDT, ETH/USDT, vb.):
```python
# Yüzde olarak göster
percentage = ((current - entry) / entry) * 100
```

## 🔄 Çalışma Akışı

1. **Google Sheets'i Oku**: Tüm satırları çek
2. **Açık Pozisyonları Filtrele**:
   - Final Signal = BUY veya SELL
   - Entry Price mevcut
   - Position Status ≠ CLOSED
3. **Her Pozisyon için**:
   - Mevcut fiyatı çek (data provider'dan)
   - TP1/TP2/SL seviyelerini kontrol et
   - Hit varsa:
     - Telegram bildirimi gönder
     - Google Sheets'i güncelle
     - Kâr/zarar hesapla ve göster
4. **Robot 9 Status Güncelle**: BG kolonu ✅

## ⏱️ Zamanlama

**CRON**: `*/3 * * * *` (Her 3 dakikada bir)

```bash
# Cloud Scheduler
0 */3 * * * /app/scripts/run_tp_monitor.sh
```

Robot 9, diğer robotlardan **bağımsız** çalışır:
- **Robot 1**: Her 5 dk (veri toplama)
- **Pipeline (3,8,7,4,6,5)**: Her 30 dk (analiz + paylaşım)
- **Robot 2**: Her 5 dk (haber izleme)
- **Robot 9**: Her 3 dk (TP/SL takip) ← YENİ!

## 🚨 Önemli Notlar

### 1. **Duplicate Notification Prevention**
Robot 9, aynı hedef için birden fazla bildirim göndermez:
```python
# TP1 zaten vurulduysa, tekrar bildirim gönderme
if tp1_hit == "YES":
    skip_tp1_check()
```

### 2. **Position Closure**
- **TP2 vurulduğunda**: Pozisyon otomatik CLOSED olarak işaretlenir
- **SL vurulduğunda**: Pozisyon otomatik CLOSED olarak işaretlenir
- **TP1 vurulduğunda**: Pozisyon açık kalır (TP2 için bekler)

### 3. **Rate Limiting**
Google Sheets API rate limit'lerini aşmamak için:
```python
time.sleep(SHEETS_RATE_LIMIT_SLEEP)  # 0.5 saniye
```

### 4. **Data Provider Fallback**
Fiyat alınamadığında:
```python
if not current_price:
    logger.warning("⚠️ Fiyat alınamadı, atlanıyor...")
    continue
```

## 📊 Örnek Senaryo

### Senaryo: BTC/USDT Long Pozisyonu

1. **T=0**: Robot 7 BUY sinyali verir
   - Entry: $95,000
   - TP1: $98,000 (+3.16%)
   - TP2: $101,000 (+6.32%)
   - SL: $93,000 (-2.11%)

2. **T=10 dk**: Robot 9 çalışır
   - Mevcut fiyat: $96,500
   - Henüz hiçbir hedef vurulmadı ✅

3. **T=20 dk**: Robot 9 çalışır
   - Mevcut fiyat: $98,150
   - **TP1 VURULDU!** 🎯
   - Telegram bildirimi: "+3.16% kâr 🤑"
   - BC kolonu: "YES"
   - Pozisyon hala OPEN (TP2 için bekliyor)

4. **T=30 dk**: Robot 9 çalışır
   - Mevcut fiyat: $101,200
   - **TP2 VURULDU!** 🚀
   - Telegram bildirimi: "+6.53% kâr 🎉"
   - BD kolonu: "YES"
   - BF kolonu: "CLOSED"
   - Pozisyon kapatıldı ✅

## 🐛 Hata Ayıklama

### Log Mesajları

```bash
# Başarılı çalışma
🎯 ROBOT 9: TP/SL MONITOR - BAŞLAT
📊 3 açık pozisyon bulundu
🔍 Kontrol: BTC/USDT (BUY)
  Şu anki fiyat: $98,150.00
  🎯 TP1 VURULDU! Kâr: +315.8 pips (+3.16%)
  ✅ TP1 bildirimi gönderildi
✅ ROBOT 9 TAMAMLANDI
```

### Sorun Giderme

**Sorun**: Bildirim gelmiyor
```bash
# Kontrol et:
1. Telegram token ve chat_id doğru mu?
2. Position Status = OPEN mi?
3. Entry/TP/SL değerleri var mı?
```

**Sorun**: Fiyat alınamıyor
```bash
# Kontrol et:
1. Data provider API çalışıyor mu?
2. Market sembolü doğru formatta mı? (BTC/USDT)
3. API rate limit aşıldı mı?
```

## 📈 Metrikler

Robot 9 aşağıdaki metrikleri takip eder:
- İzlenen pozisyon sayısı
- Gönderilen bildirim sayısı
- Kapatılan pozisyon sayısı
- Ortalama kâr/zarar (Robot 6'da hesaplanır)

---

**Robot 9 ile artık hiçbir hedef kaçmayacak!** 🎯🚀
