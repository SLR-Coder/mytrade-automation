# 🚀 MyTrade Automation - Production Deployment Guide

Bu kılavuz, MyTrade Automation sistemini Google Cloud Platform'a deploy etmek için adım adım talimatlar içerir.

## 📋 İçindekiler

1. [Gereksinimler](#gereksinimler)
2. [Cloud Run Deployment](#cloud-run-deployment)
3. [Cloud Scheduler Setup](#cloud-scheduler-setup)
4. [Secrets Configuration](#secrets-configuration)
5. [Testing & Validation](#testing--validation)
6. [Monitoring & Logs](#monitoring--logs)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Gereksinimler

### 1. Google Cloud Project

```bash
# GCloud CLI yükleyin
curl https://sdk.cloud.google.com | bash
exec -l $SHELL  # Shell'i yeniden başlatın

# Giriş yapın
gcloud auth login

# Proje oluşturun veya seçin
gcloud config set project YOUR_PROJECT_ID
```

### 2. Gerekli API'leri Etkinleştirin

```bash
# Cloud Run
gcloud services enable run.googleapis.com

# Cloud Scheduler
gcloud services enable cloudscheduler.googleapis.com

# Secret Manager
gcloud services enable secretmanager.googleapis.com

# Container Registry
gcloud services enable containerregistry.googleapis.com

# Cloud Build (optional)
gcloud services enable cloudbuild.googleapis.com
```

### 3. Secrets Ayarlayın

```bash
# Google Sheets Spreadsheet ID
echo -n "YOUR_SPREADSHEET_ID" | gcloud secrets create GOOGLE_SHEETS_SPREADSHEET_ID --data-file=-

# Google Service Account (JSON dosyasından)
gcloud secrets create GOOGLE_SERVICE_ACCOUNT_JSON --data-file=path/to/service-account.json

# Telegram Bot Token
echo -n "YOUR_BOT_TOKEN" | gcloud secrets create TELEGRAM_BOT_TOKEN --data-file=-

# Telegram Chat ID
echo -n "YOUR_CHAT_ID" | gcloud secrets create TELEGRAM_CHAT_ID --data-file=-

# AI API Keys
echo -n "YOUR_OPENAI_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-
echo -n "YOUR_ANTHROPIC_KEY" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
echo -n "YOUR_GEMINI_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
echo -n "YOUR_XAI_KEY" | gcloud secrets create XAI_API_KEY --data-file=-
echo -n "YOUR_DEEPSEEK_KEY" | gcloud secrets create DEEPSEEK_API_KEY --data-file=-

# Data Provider API Keys (optional)
echo -n "YOUR_ALPHA_VANTAGE_KEY" | gcloud secrets create ALPHA_VANTAGE_API_KEY --data-file=-
echo -n "YOUR_POLYGON_KEY" | gcloud secrets create POLYGON_API_KEY --data-file=-
echo -n "YOUR_TWELVEDATA_KEY" | gcloud secrets create TWELVEDATA_API_KEY --data-file=-
```

---

## 🐳 Cloud Run Deployment

### 1. Dockerfile Hazırlama

Proje zaten bir `Dockerfile` içeriyor. Kontrol edin:

```bash
cat Dockerfile
```

### 2. Container Image Build

```bash
# Project ID'nizi alın
PROJECT_ID=$(gcloud config get-value project)

# Image build edin
gcloud builds submit --tag gcr.io/$PROJECT_ID/mytrade-automation

# Veya local Docker ile:
docker build -t gcr.io/$PROJECT_ID/mytrade-automation .
docker push gcr.io/$PROJECT_ID/mytrade-automation
```

### 3. Cloud Run Service Deploy

```bash
# Cloud Run service deploy edin
gcloud run deploy mytrade-automation \
  --image gcr.io/$PROJECT_ID/mytrade-automation \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 600s \
  --max-instances 10 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="GOOGLE_SHEETS_SPREADSHEET_ID=GOOGLE_SHEETS_SPREADSHEET_ID:latest,\
GOOGLE_SERVICE_ACCOUNT_JSON=GOOGLE_SERVICE_ACCOUNT_JSON:latest,\
TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest,\
TELEGRAM_CHAT_ID=TELEGRAM_CHAT_ID:latest,\
OPENAI_API_KEY=OPENAI_API_KEY:latest,\
ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,\
GEMINI_API_KEY=GEMINI_API_KEY:latest,\
XAI_API_KEY=XAI_API_KEY:latest,\
DEEPSEEK_API_KEY=DEEPSEEK_API_KEY:latest"

# Service URL'yi alın
SERVICE_URL=$(gcloud run services describe mytrade-automation --region us-central1 --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"
```

### 4. Service Account Permissions

```bash
# Cloud Run service account'a Secret Manager erişimi verin
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

---

## ⏰ Cloud Scheduler Setup

### Scheduler Jobs Oluşturma

Her robot için scheduler job oluşturun:

```bash
# Service URL'yi alın
SERVICE_URL=$(gcloud run services describe mytrade-automation --region us-central1 --format 'value(status.url)')

# 1. Data Collection (Robot 1) - Her 5 dakikada
gcloud scheduler jobs create http data-collection \
  --location=us-central1 \
  --schedule="*/5 * * * *" \
  --uri="$SERVICE_URL/run_script?script=run_data_collector.sh" \
  --http-method=POST \
  --time-zone="UTC" \
  --description="Robot 1: Data collection every 5 minutes" \
  --attempt-deadline=600s

# 2. News Monitor (Robot 2) - Her 5 dakikada
gcloud scheduler jobs create http news-monitor \
  --location=us-central1 \
  --schedule="*/5 * * * *" \
  --uri="$SERVICE_URL/run_script?script=run_news_monitor.sh" \
  --http-method=POST \
  --time-zone="UTC" \
  --description="Robot 2: News monitoring every 5 minutes" \
  --attempt-deadline=600s

# 3. Analysis Pipeline (Robots 3,8,7,4,6,5) - Her 30 dakikada
gcloud scheduler jobs create http analysis-pipeline \
  --location=us-central1 \
  --schedule="*/30 * * * *" \
  --uri="$SERVICE_URL/run_script?script=run_analysis_pipeline.sh" \
  --http-method=POST \
  --time-zone="UTC" \
  --description="Full 30-min analysis pipeline" \
  --attempt-deadline=600s

# 4. TP/SL Monitor (Robot 9) - Her 3 dakikada
gcloud scheduler jobs create http tp-sl-monitor \
  --location=us-central1 \
  --schedule="*/3 * * * *" \
  --uri="$SERVICE_URL/run_script?script=run_tp_monitor.sh" \
  --http-method=POST \
  --time-zone="UTC" \
  --description="Robot 9: TP/SL real-time tracking" \
  --attempt-deadline=600s

# 5. Weekly Report (Robot 6) - Her Pazar saat 00:00 UTC
gcloud scheduler jobs create http weekly-report \
  --location=us-central1 \
  --schedule="0 0 * * 0" \
  --uri="$SERVICE_URL/run_script?script=run_weekly_report.sh" \
  --http-method=POST \
  --time-zone="UTC" \
  --description="Robot 6: Weekly Telegram report" \
  --attempt-deadline=600s
```

### Scheduler Jobs Listeleme

```bash
# Tüm scheduler jobs'ları listeleyin
gcloud scheduler jobs list --location=us-central1
```

### Scheduler Job Güncelleme

```bash
# Schedule değiştirmek için
gcloud scheduler jobs update http JOB_NAME \
  --location=us-central1 \
  --schedule="NEW_SCHEDULE"

# URI değiştirmek için
gcloud scheduler jobs update http JOB_NAME \
  --location=us-central1 \
  --uri="NEW_URI"
```

### Scheduler Job Silme

```bash
gcloud scheduler jobs delete JOB_NAME --location=us-central1
```

---

## 🔐 Secrets Configuration

### Secret Manager'da Secret Oluşturma

```bash
# Yeni secret oluşturma
echo -n "SECRET_VALUE" | gcloud secrets create SECRET_NAME --data-file=-

# Secret güncelleme
echo -n "NEW_VALUE" | gcloud secrets versions add SECRET_NAME --data-file=-

# Secret'ı Cloud Run'a bağlama
gcloud run services update mytrade-automation \
  --region us-central1 \
  --update-secrets="SECRET_NAME=SECRET_NAME:latest"
```

### Gerekli Secrets Listesi

| Secret Name | Açıklama | Gerekli Mi? |
|-------------|----------|-------------|
| `GOOGLE_SHEETS_SPREADSHEET_ID` | Google Sheets ID | ✅ Evet |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service Account JSON | ✅ Evet |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | ✅ Evet |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | ✅ Evet |
| `OPENAI_API_KEY` | OpenAI GPT-4 API Key | ✅ Evet |
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key | ✅ Evet |
| `GEMINI_API_KEY` | Google Gemini API Key | ✅ Evet |
| `XAI_API_KEY` | xAI Grok API Key | ✅ Evet |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | ✅ Evet |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage (Forex data) | ⚠️ İsteğe bağlı |
| `POLYGON_API_KEY` | Polygon.io (Market data) | ⚠️ İsteğe bağlı |
| `TWELVEDATA_API_KEY` | TwelveData (Market data) | ⚠️ İsteğe bağlı |

---

## ✅ Testing & Validation

### 1. Local Testing (Production ortamını taklit edin)

```bash
# Secrets'ı environment variable olarak ayarlayın
export GOOGLE_SHEETS_SPREADSHEET_ID="your_id"
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
# ... diğer secrets

# Her robotu test edin
bash scripts/run_data_collector.sh
bash scripts/run_news_monitor.sh
bash scripts/run_analysis_pipeline.sh
bash scripts/run_tp_monitor.sh
bash scripts/run_weekly_report.sh
```

### 2. Cloud Run Service Test

```bash
# Service URL'yi alın
SERVICE_URL=$(gcloud run services describe mytrade-automation --region us-central1 --format 'value(status.url)')

# Manuel olarak script çalıştırın
curl -X POST "$SERVICE_URL/run_script?script=run_data_collector.sh"
curl -X POST "$SERVICE_URL/run_script?script=run_analysis_pipeline.sh"
```

### 3. Scheduler Job Test

```bash
# Job'ı manuel olarak tetikleyin
gcloud scheduler jobs run data-collection --location=us-central1
gcloud scheduler jobs run analysis-pipeline --location=us-central1

# Job durumunu kontrol edin
gcloud scheduler jobs describe data-collection --location=us-central1
```

### 4. Google Sheets Validation

1. Google Sheets'i açın
2. Son satırlara bakın - yeni veri eklenmiş mi?
3. Robot status sütunlarını kontrol edin (AU-BB, BG):
   - Robot 1 ✅
   - Robot 3 ✅
   - Robot 7 ✅
   - Robot 9 ✅
4. Entry/TP/SL sütunlarını kontrol edin (AM-AQ)
5. TP/SL hit status sütunlarını kontrol edin (BC-BF)

### 5. Telegram Validation

1. Telegram kanalınızı açın
2. Sinyal mesajları geliyor mu?
3. TP/SL bildirimleri geliyor mu?
4. Haftalık rapor geldi mi? (Pazar günü)

---

## 📊 Monitoring & Logs

### Cloud Run Logs

```bash
# Tüm logları görüntüleyin
gcloud run services logs read mytrade-automation --region us-central1 --limit=100

# Son 1 saatin logları
gcloud run services logs read mytrade-automation --region us-central1 --since=1h

# Hata loglarını filtreleyin
gcloud run services logs read mytrade-automation --region us-central1 --filter="severity=ERROR"

# Belirli bir robot için filtreleme
gcloud run services logs read mytrade-automation --region us-central1 --filter="textPayload:Robot-3"
```

### Scheduler Job Logs

```bash
# Job execution history
gcloud scheduler jobs describe data-collection --location=us-central1

# Last execution result
gcloud scheduler jobs list --location=us-central1 --format="table(name, schedule, lastAttemptTime, state)"
```

### Cloud Logging (Advanced)

```bash
# Cloud Console'da Logs Explorer açın
# https://console.cloud.google.com/logs

# Örnek query:
resource.type="cloud_run_revision"
resource.labels.service_name="mytrade-automation"
severity>=WARNING

# Robot bazında filtreleme:
textPayload=~"Robot-9.*BAŞARISIZ"
```

### Monitoring Dashboard

```bash
# Cloud Console'da Monitoring Dashboard oluşturun
# https://console.cloud.google.com/monitoring

# Önemli metrikler:
# - Cloud Run instance count
# - Request count
# - Request latency
# - Error rate
# - Memory usage
# - CPU usage
```

---

## 🐛 Troubleshooting

### Problem 1: Scheduler Job Çalışmıyor

**Semptomlar:**
- Scheduler job "FAILED" durumunda
- Google Sheets güncellenmiyor
- Telegram mesajı gelmiyor

**Çözümler:**

```bash
# 1. Job state'i kontrol edin
gcloud scheduler jobs describe JOB_NAME --location=us-central1

# 2. Cloud Run service'in çalışır durumda olduğundan emin olun
gcloud run services describe mytrade-automation --region us-central1

# 3. Service URL'nin doğru olduğundan emin olun
SERVICE_URL=$(gcloud run services describe mytrade-automation --region us-central1 --format 'value(status.url)')
echo $SERVICE_URL

# 4. Job'ı manuel test edin
gcloud scheduler jobs run JOB_NAME --location=us-central1

# 5. Logları kontrol edin
gcloud run services logs read mytrade-automation --region us-central1 --limit=50
```

### Problem 2: Secret Erişim Hatası

**Hata:**
```
PermissionDenied: Permission 'secretmanager.versions.access' denied
```

**Çözüm:**

```bash
# Service account'a Secret Manager erişimi verin
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")
SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

### Problem 3: Google Sheets API Hatası

**Hata:**
```
gspread.exceptions.APIError: PERMISSION_DENIED
```

**Çözüm:**

1. Service Account email'ini kopyalayın:
   ```bash
   cat service-account.json | grep "client_email"
   ```

2. Google Sheets'i açın
3. "Share" butonuna tıklayın
4. Service Account email'ini ekleyin (Editor yetkisi ile)
5. "Send" butonuna tıklayın

### Problem 4: Telegram Bot Mesaj Göndermiyor

**Hata:**
```
telegram.error.Unauthorized: Forbidden: bot was blocked by the user
```

**Çözüm:**

1. Telegram'da bot'u arayın: `@YOUR_BOT_USERNAME`
2. `/start` komutunu gönderin
3. Chat ID'yi doğrulayın:
   ```bash
   curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates"
   ```

### Problem 5: AI API Rate Limit

**Hata:**
```
openai.error.RateLimitError: Rate limit exceeded
```

**Çözümler:**

1. **Robot 3'te AI sayısını azaltın** (geçici):
   - `robots/ai_signal_generator.py` dosyasını düzenleyin
   - Sadece 2-3 AI kullanın (örn: GPT-4, Claude, Gemini)

2. **Rate limit'i artırın**:
   - OpenAI/Anthropic/Gemini dashboard'larında tier upgrade yapın

3. **Retry logic ekleyin** (zaten var):
   - AI wrapper'lar otomatik retry yapar

### Problem 6: Memory Limit Exceeded

**Hata:**
```
Cloud Run error: Memory limit exceeded
```

**Çözüm:**

```bash
# Cloud Run memory'yi artırın
gcloud run services update mytrade-automation \
  --region us-central1 \
  --memory 4Gi

# Veya CPU'yu artırın
gcloud run services update mytrade-automation \
  --region us-central1 \
  --cpu 2
```

---

## 📈 Production Checklist

Deploy öncesi kontrol listesi:

- [ ] Tüm secrets oluşturuldu ve test edildi
- [ ] Google Sheets service account'a share edildi
- [ ] Telegram bot test edildi
- [ ] Cloud Run service deploy edildi ve çalışıyor
- [ ] Scheduler jobs oluşturuldu (5 adet)
- [ ] Local'de tüm scriptler test edildi
- [ ] Cloud Run üzerinde manuel test yapıldı
- [ ] İlk scheduler execution başarılı oldu
- [ ] Google Sheets güncellemeleri doğrulandı
- [ ] Telegram mesajları geldi
- [ ] Monitoring dashboard kuruldu
- [ ] Log alertleri ayarlandı (opsiyonel)
- [ ] Cost budget alertleri ayarlandı
- [ ] Backup planı hazır (Google Sheets export)

---

## 💰 Cost Estimation

### Monthly Costs (Approximate)

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Scheduler | 5 jobs | $0.30 |
| Cloud Run | ~33,000 executions/month | $10-30 |
| Secret Manager | 10 secrets | $0.20 |
| AI APIs (OpenAI, Claude, etc.) | ~14,400 requests/month | $50-150 |
| Google Sheets API | Unlimited (free) | $0 |
| Telegram Bot API | Unlimited (free) | $0 |
| **TOTAL** | | **$60-180/month** |

### Cost Optimization Tips

1. **AI API Usage'ı Azaltın:**
   - Sadece 2-3 AI kullanın (GPT-4, Claude, Gemini)
   - Robot 8'i devre dışı bırakın (opsiyonel)

2. **Scheduler Frequency'yi Azaltın:**
   - Analysis pipeline: 30 min → 60 min
   - TP/SL monitor: 3 min → 5 min

3. **Cloud Run Memory'yi Optimize Edin:**
   - 2Gi → 1Gi (test ederek)

4. **Free Tier AI APIs Kullanın:**
   - Gemini 1.5 Flash (free tier)
   - DeepSeek (ucuz)

---

## 🎯 Next Steps

Deploy başarılı olduktan sonra:

1. **İlk 24 Saat:** Logları yakından izleyin
2. **İlk Hafta:** Performance metriklerini gözlemleyin
3. **İlk Ay:** Cost'u analiz edin ve optimize edin
4. **Devam Eden:** Weekly report'ları gözden geçirin

**Başarılar! 🚀**

---

## 📞 Support

Sorun yaşarsanız:

1. Önce bu kılavuzdaki Troubleshooting bölümünü kontrol edin
2. Cloud Run loglarını inceleyin
3. Google Sheets'i manuel kontrol edin
4. GitHub Issues'da soru açın
