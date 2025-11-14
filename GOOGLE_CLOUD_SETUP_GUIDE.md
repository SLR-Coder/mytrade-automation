# 🚀 MyTrade - Google Cloud Setup Rehberi

Bu dokuman, MyTrade AI Trading Automation sistemini Google Cloud Platform'da sıfırdan kurmanız için adım adım talimatlar içerir.

## 📋 Ön Gereksinimler

1. **Google Cloud Hesabı**: Aktif GCP hesabı ve kredi kartı
2. **Project ID**: `mytrade-automation` (sizin oluşturduğunuz)
3. **Billing**: Aktif faturalandırma hesabı
4. **API Keys**: OpenAI, Anthropic (Claude), Google AI (Gemini), Telegram Bot, vb.

---

## 🎯 ADIM 1: Google Cloud Shell'i Açın

1. Google Cloud Console'a gidin: https://console.cloud.google.com
2. Projenizi seçin: `mytrade-automation`
3. Sağ üstteki **"Activate Cloud Shell"** butonuna tıklayın
4. Terminal açıldığında aşağıdaki komutu çalıştırın:

```bash
gcloud config set project mytrade-automation
```

---

## 🎯 ADIM 2: GitHub'dan Kodu Çekin

Google Cloud Shell terminalinde:

```bash
# GitHub'dan projeyi klonlayın
git clone https://github.com/SLR-Coder/mytrade-automation.git

# Proje dizinine girin
cd mytrade-automation

# Doğru branch'e geçin
git checkout claude/mytrade-automation-setup-01R6EDj3Z18hnkA2C9RqkHei

# Dosyaları kontrol edin
ls -la
```

**Beklenen çıktı**: ai/, core/, robots/, utils/ klasörleri ve main.py dosyasını görmelisiniz.

---

## 🎯 ADIM 3: Google Cloud API'lerini Aktifleştirin

```bash
# Gerekli API'leri aktifleştirin
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  storage-api.googleapis.com \
  sheets.googleapis.com \
  cloudlogging.googleapis.com
```

**Süre**: ~2-3 dakika
**Çıktı**: Her API için "Operation ... finished successfully" mesajları

---

## 🎯 ADIM 4: Service Account Oluşturun

```bash
# Service account oluşturun
gcloud iam service-accounts create mytrade-robot \
  --display-name="MyTrade Automation Robot" \
  --description="Service account for MyTrade trading automation"

# Service account email'ini bir değişkende saklayın
export SA_EMAIL="mytrade-robot@mytrade-automation.iam.gserviceaccount.com"

# Gerekli rolleri verin
gcloud projects add-iam-policy-binding mytrade-automation \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding mytrade-automation \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding mytrade-automation \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding mytrade-automation \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/logging.logWriter"
```

**Doğrulama**: Service account'u kontrol edin:
```bash
gcloud iam service-accounts list
```

---

## 🎯 ADIM 5: Artifact Registry Oluşturun

```bash
# Docker image'larınız için repository oluşturun
gcloud artifacts repositories create mytrade-repo \
  --repository-format=docker \
  --location=europe-west1 \
  --description="Docker repository for MyTrade"
```

**Doğrulama**:
```bash
gcloud artifacts repositories list
```

---

## 🎯 ADIM 6: Cloud Storage Bucket Oluşturun (Grafikler için)

```bash
# Storage bucket oluşturun
gsutil mb -l europe-west1 gs://mytrade-charts-bucket

# Public read erişimi verin (grafiklerin Telegram'da görünmesi için)
gsutil iam ch allUsers:objectViewer gs://mytrade-charts-bucket
```

**Doğrulama**:
```bash
gsutil ls
```

---

## 🎯 ADIM 7: CloudSQL PostgreSQL Veritabanı Oluşturun

```bash
# PostgreSQL instance oluşturun (bu 5-10 dakika sürebilir)
gcloud sql instances create mytrade-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=europe-west1 \
  --root-password="ChangeThisPassword123!" \
  --storage-type=SSD \
  --storage-size=10GB \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04

# Database oluşturun
gcloud sql databases create mytrade \
  --instance=mytrade-db

# PostgreSQL kullanıcısı oluşturun
gcloud sql users create mytrade_user \
  --instance=mytrade-db \
  --password="ChangeThisUserPassword456!"
```

**ÖNEMLİ**: Yukarıdaki şifreleri güvenli, güçlü şifrelerle değiştirin!

**Doğrulama**:
```bash
gcloud sql instances list
gcloud sql databases list --instance=mytrade-db
```

---

## 🎯 ADIM 8: Google Sheets Oluşturun

1. Google Sheets'e gidin: https://sheets.google.com
2. **"Blank"** (Boş) spreadsheet oluşturun
3. İsim verin: "MyTrade Dashboard"
4. URL'den **SHEET_ID**'yi kopyalayın:
   ```
   https://docs.google.com/spreadsheets/d/[BU_KISIM_SHEET_ID]/edit
   ```
5. **Share** butonuna tıklayın ve service account email'ini ekleyin:
   ```
   mytrade-robot@mytrade-automation.iam.gserviceaccount.com
   ```
   - **Editor** yetkisi verin

**SHEET_ID'yi kaydedin**: Bir sonraki adımda kullanacaksınız!

---

## 🎯 ADIM 9: Secret Manager'a API Anahtarlarınızı Ekleyin

Google Cloud Shell'de her secret için bu komutu çalıştırın:

```bash
# GOOGLE_SHEET_ID (yukarıda kopyaladığınız ID)
echo -n "BURAYA_SHEET_ID_YAPIŞTIRIN" | gcloud secrets create GOOGLE_SHEET_ID --data-file=-

# OpenAI API Key
echo -n "BURAYA_OPENAI_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-

# Anthropic (Claude) API Key
echo -n "BURAYA_ANTHROPIC_KEY" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-

# Google Gemini API Key
echo -n "BURAYA_GEMINI_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-

# Telegram Bot Token
echo -n "BURAYA_TELEGRAM_BOT_TOKEN" | gcloud secrets create TELEGRAM_BOT_TOKEN --data-file=-

# Telegram Chat ID
echo -n "BURAYA_TELEGRAM_CHAT_ID" | gcloud secrets create TELEGRAM_CHAT_ID --data-file=-

# Polygon.io API Key (Forex verisi için)
echo -n "BURAYA_POLYGON_KEY" | gcloud secrets create POLYGON_API_KEY --data-file=-

# Alpha Vantage API Key (Yedek veri kaynağı)
echo -n "BURAYA_ALPHA_VANTAGE_KEY" | gcloud secrets create ALPHA_VANTAGE_KEY --data-file=-
```

**Doğrulama**:
```bash
gcloud secrets list
```

**Çıktı**: 8 secret görmelisiniz.

---

## 🎯 ADIM 10: Docker Image'ı Build Edin ve Deploy Edin

```bash
# Cloud Build ile Docker image'ı oluşturun
gcloud builds submit --config cloudbuild.yaml --substitutions=_PROJECT_ID=mytrade-automation
```

**Süre**: ~10-15 dakika (ilk build uzun sürer çünkü TA-Lib compile edilir)

**Çıktı**: "SUCCESS" mesajı görmelisiniz.

---

## 🎯 ADIM 11: Cloud Run Job'u Manuel Test Edin

```bash
# Job'u manuel çalıştırın
gcloud run jobs execute mytrade-automation-job \
  --region=europe-west1 \
  --wait
```

**Süre**: ~2-5 dakika
**Beklenen sonuç**: Job başarıyla tamamlanmalı (exit code 0)

**Logları kontrol edin**:
```bash
gcloud logging read "resource.type=cloud_run_job" \
  --limit 50 \
  --format "table(timestamp, jsonPayload.message)"
```

---

## 🎯 ADIM 12: Cloud Scheduler Jobs Oluşturun

```bash
# SAATLİK GÜNCELLEME (Her saat başı, Robot 1,5)
gcloud scheduler jobs create http mytrade-hourly \
  --location=europe-west1 \
  --schedule="0 * * * *" \
  --time-zone="Europe/Istanbul" \
  --uri="https://run.googleapis.com/v1/namespaces/mytrade-automation/jobs/mytrade-automation-job:run" \
  --http-method=POST \
  --oauth-service-account-email=mytrade-robot@mytrade-automation.iam.gserviceaccount.com \
  --message-body='{"overrides": {"containerOverrides": [{"env": [{"name": "ROBOT", "value": "1,5"}]}]}}'

# LONDRA ÖNCESİ (10:00 Turkey, Hafta içi)
gcloud scheduler jobs create http mytrade-pre-london \
  --location=europe-west1 \
  --schedule="0 10 * * MON-FRI" \
  --time-zone="Europe/Istanbul" \
  --uri="https://run.googleapis.com/v1/namespaces/mytrade-automation/jobs/mytrade-automation-job:run" \
  --http-method=POST \
  --oauth-service-account-email=mytrade-robot@mytrade-automation.iam.gserviceaccount.com \
  --message-body='{"overrides": {"containerOverrides": [{"env": [{"name": "ROBOT", "value": "1,2,3,4,5,6"}, {"name": "MIN_CONFIDENCE", "value": "60"}]}]}}'

# LONDRA AÇILIŞ (11:00 Turkey, Hafta içi)
gcloud scheduler jobs create http mytrade-london-open \
  --location=europe-west1 \
  --schedule="0 11 * * MON-FRI" \
  --time-zone="Europe/Istanbul" \
  --uri="https://run.googleapis.com/v1/namespaces/mytrade-automation/jobs/mytrade-automation-job:run" \
  --http-method=POST \
  --oauth-service-account-email=mytrade-robot@mytrade-automation.iam.gserviceaccount.com \
  --message-body='{"overrides": {"containerOverrides": [{"env": [{"name": "ROBOT", "value": "1,2,3,4,5,6"}, {"name": "MIN_CONFIDENCE", "value": "65"}]}]}}'

# NEW YORK ÖNCESİ (15:00 Turkey, Hafta içi)
gcloud scheduler jobs create http mytrade-pre-newyork \
  --location=europe-west1 \
  --schedule="0 15 * * MON-FRI" \
  --time-zone="Europe/Istanbul" \
  --uri="https://run.googleapis.com/v1/namespaces/mytrade-automation/jobs/mytrade-automation-job:run" \
  --http-method=POST \
  --oauth-service-account-email=mytrade-robot@mytrade-automation.iam.gserviceaccount.com \
  --message-body='{"overrides": {"containerOverrides": [{"env": [{"name": "ROBOT", "value": "1,2,3,4,5,6"}, {"name": "MIN_CONFIDENCE", "value": "60"}]}]}}'

# NEW YORK AÇILIŞ (16:00 Turkey, Hafta içi)
gcloud scheduler jobs create http mytrade-newyork-open \
  --location=europe-west1 \
  --schedule="0 16 * * MON-FRI" \
  --time-zone="Europe/Istanbul" \
  --uri="https://run.googleapis.com/v1/namespaces/mytrade-automation/jobs/mytrade-automation-job:run" \
  --http-method=POST \
  --oauth-service-account-email=mytrade-robot@mytrade-automation.iam.gserviceaccount.com \
  --message-body='{"overrides": {"containerOverrides": [{"env": [{"name": "ROBOT", "value": "1,2,3,4,5,6"}, {"name": "MIN_CONFIDENCE", "value": "70"}]}]}}'

# YÜKSEK VOLATİLİTE (17:00 Turkey, Hafta içi - Londra+NY çakışması)
gcloud scheduler jobs create http mytrade-peak-volatility \
  --location=europe-west1 \
  --schedule="0 17 * * MON-FRI" \
  --time-zone="Europe/Istanbul" \
  --uri="https://run.googleapis.com/v1/namespaces/mytrade-automation/jobs/mytrade-automation-job:run" \
  --http-method=POST \
  --oauth-service-account-email=mytrade-robot@mytrade-automation.iam.gserviceaccount.com \
  --message-body='{"overrides": {"containerOverrides": [{"env": [{"name": "ROBOT", "value": "1,2,3,4,5,6"}, {"name": "MIN_CONFIDENCE", "value": "65"}]}]}}'

# GÜNLÜK ÖZET (20:00 Turkey, Her gün)
gcloud scheduler jobs create http mytrade-daily-summary \
  --location=europe-west1 \
  --schedule="0 20 * * *" \
  --time-zone="Europe/Istanbul" \
  --uri="https://run.googleapis.com/v1/namespaces/mytrade-automation/jobs/mytrade-automation-job:run" \
  --http-method=POST \
  --oauth-service-account-email=mytrade-robot@mytrade-automation.iam.gserviceaccount.com \
  --message-body='{"overrides": {"containerOverrides": [{"env": [{"name": "ROBOT", "value": "1,2,3,4,5,6"}]}]}}'

# HAFTALIK ÖZET (Cuma 21:00 Turkey)
gcloud scheduler jobs create http mytrade-weekly-summary \
  --location=europe-west1 \
  --schedule="0 21 * * FRI" \
  --time-zone="Europe/Istanbul" \
  --uri="https://run.googleapis.com/v1/namespaces/mytrade-automation/jobs/mytrade-automation-job:run" \
  --http-method=POST \
  --oauth-service-account-email=mytrade-robot@mytrade-automation.iam.gserviceaccount.com \
  --message-body='{"overrides": {"containerOverrides": [{"env": [{"name": "ROBOT", "value": "1,2,3,4,5,6"}]}]}}'

# SAĞLIK KONTROLÜ (Her 5 dakikada)
gcloud scheduler jobs create http mytrade-health-check \
  --location=europe-west1 \
  --schedule="*/5 * * * *" \
  --time-zone="Europe/Istanbul" \
  --uri="https://run.googleapis.com/v1/namespaces/mytrade-automation/jobs/mytrade-automation-job:run" \
  --http-method=POST \
  --oauth-service-account-email=mytrade-robot@mytrade-automation.iam.gserviceaccount.com \
  --message-body='{"overrides": {"containerOverrides": [{"env": [{"name": "ROBOT", "value": "6"}]}]}}'
```

**Doğrulama**:
```bash
gcloud scheduler jobs list --location=europe-west1
```

**Çıktı**: 9 job görmelisiniz.

---

## 🎯 ADIM 13: İlk Scheduler Job'u Test Edin

```bash
# Manuel olarak bir job'u tetikleyin
gcloud scheduler jobs run mytrade-hourly --location=europe-west1

# Logları izleyin
gcloud logging read "resource.type=cloud_run_job" \
  --limit 20 \
  --format "table(timestamp, jsonPayload.message)"
```

**Beklenen sonuç**:
- Telegram botunuzda mesaj almalısınız
- Google Sheets'te veriler görünmeli
- Loglar başarıyı göstermeli

---

## 🎯 ADIM 14: Monitoring ve Alerting Kurun (Opsiyonel ama Önerilen)

```bash
# Uptime check oluşturun (job'un düzenli çalıştığını kontrol eder)
gcloud monitoring uptime create mytrade-health \
  --resource-type=uptime-url \
  --http-check \
  --check-interval=300 \
  --timeout=60 \
  --url="https://mytrade-automation-job-RANDOM-ew.a.run.app/health"
```

---

## ✅ KURULUM TAMAMLANDI!

### 🎊 Tebrikler! MyTrade sisteminiz artık çalışıyor!

### 📊 Ne Beklemelisiniz:

1. **Saatlik**: Her saat başı piyasa güncellemesi (Telegram)
2. **Londra Açılış** (11:00 TR): Tam AI analizi + sinyaller
3. **New York Açılış** (16:00 TR): Tam AI analizi + sinyaller
4. **Günlük Özet** (20:00 TR): Performans raporu
5. **Haftalık Özet** (Cuma 21:00 TR): Haftalık performans

### 🔍 Monitoring:

**Cloud Console'da kontrol edin**:
- **Cloud Run Jobs**: https://console.cloud.google.com/run/jobs?project=mytrade-automation
- **Cloud Scheduler**: https://console.cloud.google.com/cloudscheduler?project=mytrade-automation
- **Logs**: https://console.cloud.google.com/logs?project=mytrade-automation
- **Secret Manager**: https://console.cloud.google.com/security/secret-manager?project=mytrade-automation
- **CloudSQL**: https://console.cloud.google.com/sql/instances?project=mytrade-automation

### 🐛 Sorun Giderme:

**Job çalışmıyor?**
```bash
# Logları kontrol edin
gcloud logging read "resource.type=cloud_run_job" --limit 50

# Job execution history
gcloud run jobs executions list --job mytrade-automation-job --region europe-west1
```

**Telegram mesajları gelmiyor?**
- Telegram Bot Token doğru mu?
- Chat ID doğru mu?
- Secret Manager'da doğru kaydedilmiş mi?

**Google Sheets güncellenmiyor?**
- Sheet ID doğru mu?
- Service account Sheet'e editor olarak eklenmiş mi?
- Sheets API aktif mi?

**Database hataları?**
- CloudSQL instance çalışıyor mu?
- Database ve user oluşturulmuş mu?
- Service account CloudSQL Client rolüne sahip mi?

### 💰 Maliyet Tahmini (Aylık):

- **Cloud Run**: ~$5-10 (saatte 1 job, günde ~24 execution)
- **CloudSQL** (db-f1-micro): ~$7-10
- **Cloud Storage**: ~$1 (grafikler)
- **Secret Manager**: ~$1
- **Cloud Scheduler**: Ücretsiz (ilk 3 job)
- **API Maliyetleri**:
  - OpenAI GPT-4: ~$20-50 (aylık token kullanımına göre)
  - Anthropic Claude: ~$20-50
  - Google Gemini: Ücretsiz (monthly quota dahilinde)
  - Polygon.io: $199/ay (Premium plan)
  - Alpha Vantage: $49/ay (Premium plan)
  - Binance: Ücretsiz
  - Telegram: Ücretsiz

**TOPLAM**: ~$300-400/ay (premium API'ler dahil)

**Maliyet Azaltma İpuçları**:
1. Alpha Vantage yerine ücretsiz alternatifler kullanın
2. Polygon.io yerine daha ucuz forex API'leri deneyin
3. Saatlik job'u kaldırın, sadece önemli seansları çalıştırın
4. CloudSQL yerine Cloud Run'da SQLite kullanın (performans düşer)

---

## 📚 Ek Kaynaklar:

- **Google Cloud Run Docs**: https://cloud.google.com/run/docs
- **Cloud Scheduler**: https://cloud.google.com/scheduler/docs
- **CloudSQL**: https://cloud.google.com/sql/docs
- **Secret Manager**: https://cloud.google.com/secret-manager/docs

---

## 🆘 Destek:

Sorun yaşıyorsanız:
1. Logları kontrol edin (yukarıdaki komutlarla)
2. README.md dosyasını okuyun
3. COMPLETE_SOURCE_CODE_ANALYSIS.md'de mimariyi inceleyin
4. GitHub Issues'da sorunuzu paylaşın

---

**Mutlu ticaret! 🚀📈💰**
