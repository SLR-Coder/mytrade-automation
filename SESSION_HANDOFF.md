# Session Handoff - 6 Aralik 2025 (Guncellendi v2)

## SON DURUM - HIZLI OZET

**4 KRITIK IYILESTIRME:**
1. Analysis Pipeline zamanlama sorunu (scheduler)
2. Robotlar timing-dependent'di (artık ROBUST)
3. Separator satırı status takibi (observability)
4. **YENİ:** Cloud Run SIGTERM sorunu (robotlar yarıda kesiliyordu!)

- **Cloud Run URL**: `https://mytrade-automation-310689682340.europe-west1.run.app`
- **Branch**: `claude/review-session-handoff-012ZpGsNTsLeNi7ZdJTtVVJ3`
- **Son Commit**: Fix Cloud Run SIGTERM causing robots to terminate prematurely

---

## BUGUN BULUNAN BUG (6 Aralik 2025)

### Problem: "0 sinyal parsed" - 15+ saat sinyal uretilmedi!

**Kök Neden:** Zamanlama hatasi!

```
YANLIS ZAMANLAMA (eskiden):
:00 → Robot 1 batch 1 "Beklemede (1/6)"
:03 → Analysis Pipeline calisir → son batch = 1/6, TUM SATIRLARI ATLAR!
...
:25 → Robot 1 batch 6 "✅ Analiz Hazır" (ISLENMEYI BEKLIYOR!)
:30 → Robot 1 batch 1 (yeni dongu)
:33 → Analysis Pipeline calisir → son batch = 1/6 (:30'dan), YİNE ATLAR!

Robot 3 "Analiz Hazır" yazildiktan SONRA degil, yeni batch basladiktan SONRA calisiyor!
```

**Cozum:** Analysis Pipeline'i `:03/:33` yerine `:27/:57`'ye tasidik:

```
DOGRU ZAMANLAMA (simdi):
:25 → Robot 1 batch 6 "✅ Analiz Hazır"
:27 → Analysis Pipeline calisir → son batch = 6 "Analiz Hazır", 24 SATIR ISLENIR!
:30 → Robot 1 batch 1 (yeni dongu)
```

---

## GUNCELLENMESI GEREKEN SCHEDULER

**Cloud Shell'de calistir:**

```bash
gcloud scheduler jobs update http analysis-pipeline \
    --location=europe-west1 \
    --schedule="27,57 * * * *" \
    --time-zone="Europe/Istanbul"
```

---

## SCHEDULER JOBS (GUNCELLENMIS)

| Job | Eski Schedule | Yeni Schedule | Aciklama |
|-----|---------------|---------------|----------|
| data-collection | `*/5 * * * *` | (degismedi) | Robot 1 - Her 5 dk |
| tp-sl-monitor | `1-58/3 * * * *` | (degismedi) | Robot 9 - Her 3 dk |
| **analysis-pipeline** | ~~`3,33 * * * *`~~ | **`27,57 * * * *`** | **DUZELTILDI!** |
| news-monitor | `8 * * * *` | (degismedi) | Robot 2 - Her saat :08 |
| daily-reset | `0 3 * * *` | (degismedi) | Full cycle - 03:00 TR |
| performance-tracker | `0 23 * * *` | (degismedi) | Robot 6 - 23:00 TR |
| weekly-report | `0 0 * * 0` | (degismedi) | Pazar 00:00 TR |

---

## BATCH SISTEMI NASIL CALISIYOR

Robot 1 her 5 dakikada calisir ve batch durumu yazar:
- `:00` batch 1 → "Beklemede (1/6)"
- `:05` batch 2 → "Beklemede (2/6)"
- `:10` batch 3 → "Beklemede (3/6)"
- `:15` batch 4 → "Beklemede (4/6)"
- `:20` batch 5 → "Beklemede (5/6)"
- `:25` batch 6 → **"✅ Analiz Hazır"** ← Robot 3 BUNU bekliyor!
- `:30` batch 1 → "Beklemede (1/6)" (yeni dongu)

Robot 3 sadece "✅ Analiz Hazır" olan satirlari isler.
Analysis Pipeline `:27`de calisinca son batch "Analiz Hazır" olur.

---

## BUG 2: CLOUD RUN SIGTERM SORUNU (6 Aralik) - YENİ!

### Problem: Robot 3 yarıda kalıyor, Robot 8 hiç çalışmıyor!

**Loglardan görülen:**
```
09:27:00 - Running Analysis Pipeline: Robots 3,8,7,4,5
09:27:02 - Worker exiting (pid: 2)     ← SADECE 2 SANİYE SONRA!
09:27:03 - Shutting down: Master
```

**Kök Neden:** Cloud Run SIGTERM gönderdiğinde:
1. SIGTERM tüm process'lere gidiyor (gunicorn + subprocess)
2. `main.py`'deki signal handler hemen `shutdown_requested = True` yapıyordu
3. Bu, kalan robotların atlanmasına neden oluyordu!

```python
# SORUNLU KOD (eskiden):
if "3" in robot_select and not shutdown_requested:  # Robot 3 başlar
if "8" in robot_select and not shutdown_requested:  # SIGTERM geldi → ATLANIYOR!
if "7" in robot_select and not shutdown_requested:  # ATLANIYOR!
```

### Çözüm: 3 Kritik Düzeltme

**1. Dockerfile - gunicorn graceful-timeout:**
```dockerfile
CMD ["python", "-m", "gunicorn", ... "--graceful-timeout", "600", ...]
```
Shutdown sırasında worker'ların işlerini bitirmesi için 10 dakika bekler.

**2. main.py - SIGTERM handling:**
```python
def signal_handler(signum, frame):
    if signum == signal.SIGINT:
        # Ctrl+C - hemen dur
        shutdown_requested = True
    elif signum == signal.SIGTERM:
        # Cloud Run shutdown - DURMA, devam et!
        sigterm_received = True
        logger.warning("SIGTERM alındı ama işe devam ediyorum...")
```
SIGTERM artık robotları durdurmaz, sadece loglar.

**3. server.py - Concurrent request koruması:**
```python
if analysis_pipeline_running:
    return 429  # Too Many Requests - reddedildi
analysis_pipeline_running = True
```
Aynı anda birden fazla Analysis Pipeline çalışmasını önler.

---

## BUG 3: ROBOTLAR TIMING-DEPENDENT'DI (6 Aralik)

### Problem: Robot 1 gecikince tum sistem duruyordu

Robotlar sadece "son batch"e bakiyordu:
- Robot 3/8: Son separator'dan sonraki satirlara bakiyordu
- Robot 1 gecikince veya zamanlama kayinca, "Analiz Hazir" satirlari atlaniyordu

### Cozum: ROBUST yaklasim - Zamanlama bagimsiz

Yeni fonksiyonlar eklendi (`utils/common.py`):

```python
# Robot 3 ve 8 icin:
get_unprocessed_ready_rows(ws, cols, robot_status_col, robot_name)
# → Son 500 satirda "Analiz Hazir" OLAN ve islenMEMIS satirlari bulur

# Robot 7 icin:
get_rows_ready_for_command_center(ws, cols)
# → Robot 3 VE Robot 8 tamamlanmis satirlari bulur
```

**Avantajlar:**
- Zamanlama bagimsiz: Robot 1 gecikse bile calısır
- Self-healing: Kacirilan batch'ler sonraki calısmada islenir
- Duplikasyon yok: Robot status'u kontrol eder

---

## YENI: SEPARATOR SATIRI STATUS TAKIBI (6 Aralik)

### Problem: Robot calisti mi calismadi mi anlasilmiyordu

Eskiden robot 0 satir islerse hicbir iz birakmiyordu. Robot calismis ama bisey islememis mi, yoksa hic calismamis mi anlasilmiyordu.

### Cozum: update_separator_status() fonksiyonu

Artik her robot calismasi sonunda separator satirina durum yazıyor:

```
"Robot 3 ✅ (24)" = Robot 3 calisti ve 24 satir isledi
"Robot 3 ✅ (0)"  = Robot 3 calisti ama islenecek satir bulamadi
(bos)            = Robot 3 hic calismadi
```

**Eklenen fonksiyonlar (`utils/common.py`):**
```python
status_text_with_count(robot_no, ok, count)
update_separator_status(ws, cols, robot_no, processed_count)
```

**Guncellenen robotlar:**
- Robot 3 (ai_signal_generator.py)
- Robot 4 (chart_generator.py)
- Robot 5 (telegram_publisher.py)
- Robot 7 (ai_command_center.py)
- Robot 8 (personal_ai_analyst.py)

**Avantajlar:**
- Observability: Her robotun calismasi takip edilebilir
- Debugging: Hangi robot ne zaman calisti gorulebilir
- Transparency: 0 satir islemek artik bir sorun degil, gorunur

---

## ONCEKI GUNLER (5 Aralik)

### Cloud Run Deployment
- Memory: 2Gi, CPU: 2, Timeout: 600s
- Min instances: 1 (cold start yok)
- server.py ile HTTP endpoint'ler

### Duzeltilen Hatalar
1. Secret Manager izinleri - TWELVE_DATA_API_KEY izni verildi
2. Scheduler URL'leri - Eski URL'den yeni URL'ye guncellendi
3. Robot 2 async fix - `run_async_robot` -> `run_sync_robot`
4. Telegram spam kaldirildi - Sadece HATA durumunda bildirim

---

## ONEMLI DOSYALAR

| Dosya | Aciklama |
|-------|----------|
| `server.py` | HTTP endpoint'ler |
| `main.py` | Robot runner |
| `scheduler_config_v3.yaml` | **GUNCELLENDI** - Akilli zamanlama |
| `robots/ai_signal_generator.py` | Robot 3 - BK="Analiz Hazır" kontrol eder |
| `utils/common.py` | `get_batch_number()`, `is_ready_for_analysis()` |

---

## TEST ICIN

```bash
# 1. Scheduler'i guncelle
gcloud scheduler jobs update http analysis-pipeline \
    --location=europe-west1 \
    --schedule="27,57 * * * *" \
    --time-zone="Europe/Istanbul"

# 2. Manuel test (simdi calistir)
curl -X POST https://mytrade-automation-310689682340.europe-west1.run.app/analysis-pipeline

# 3. Loglari kontrol et
gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"Robot 3"' --limit=30 --format='table(timestamp,textPayload)'

# 4. Sinyal sayisini kontrol et
gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"Parsed"' --limit=10
```

---

## GIT BILGILERI

```bash
# Branch
git checkout claude/review-session-handoff-012ZpGsNTsLeNi7ZdJTtVVJ3

# Son degisiklikleri cek
git pull origin claude/review-session-handoff-012ZpGsNTsLeNi7ZdJTtVVJ3
```

---

*Son guncelleme: 6 Aralik 2025 (SIGTERM fix eklendi)*
