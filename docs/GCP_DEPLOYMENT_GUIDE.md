# 🚀 MyTrade GCP Cloud Run Deployment Guide

Complete step-by-step guide to deploy MyTrade automation system to Google Cloud Platform.

---

## 📋 Prerequisites

- Google Cloud Account
- gcloud CLI installed
- Project with billing enabled
- Domain for custom URL (optional)

---

## 🎯 STEP 1: GCP Project Setup

### 1.1 Create GCP Project

```bash
# Set variables
export PROJECT_ID="mytrade-production"
export REGION="europe-west1"
export SERVICE_ACCOUNT="mytrade-sa"

# Create project
gcloud projects create $PROJECT_ID --name="MyTrade Production"

# Set default project
gcloud config set project $PROJECT_ID

# Link billing account (replace with your billing account ID)
gcloud beta billing projects link $PROJECT_ID \
  --billing-account=YOUR_BILLING_ACCOUNT_ID
```

### 1.2 Enable Required APIs

```bash
# Enable APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  sheets.googleapis.com
```

---

## 🔐 STEP 2: Service Account Setup

### 2.1 Create Service Account

```bash
# Create service account
gcloud iam service-accounts create $SERVICE_ACCOUNT \
  --display-name="MyTrade Service Account" \
  --description="Service account for MyTrade automation"

# Get service account email
export SA_EMAIL="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Service Account Email: $SA_EMAIL"
```

### 2.2 Grant Permissions

```bash
# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudbuild.builds.builder"
```

### 2.3 Create Service Account Key

```bash
# Create and download key
gcloud iam service-accounts keys create ~/mytrade-key.json \
  --iam-account=$SA_EMAIL

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=~/mytrade-key.json
```

---

## 🗄️ STEP 3: Secret Manager Configuration

### 3.1 Create Secrets

```bash
# Google Sheets ID
echo -n "YOUR_GOOGLE_SHEETS_SPREADSHEET_ID" | \
  gcloud secrets create GOOGLE_SHEETS_SPREADSHEET_ID --data-file=-

# Telegram Bot Token
echo -n "YOUR_TELEGRAM_BOT_TOKEN" | \
  gcloud secrets create TELEGRAM_BOT_TOKEN --data-file=-

# Telegram Chat ID
echo -n "YOUR_TELEGRAM_CHAT_ID" | \
  gcloud secrets create TELEGRAM_CHAT_ID --data-file=-

# OpenAI API Key
echo -n "YOUR_OPENAI_API_KEY" | \
  gcloud secrets create OPENAI_API_KEY --data-file=-

# Anthropic (Claude) API Key
echo -n "YOUR_ANTHROPIC_API_KEY" | \
  gcloud secrets create ANTHROPIC_API_KEY --data-file=-

# Google Gemini API Key
echo -n "YOUR_GEMINI_API_KEY" | \
  gcloud secrets create GEMINI_API_KEY --data-file=-

# XAI (Grok) API Key
echo -n "YOUR_XAI_API_KEY" | \
  gcloud secrets create XAI_API_KEY --data-file=-

# DeepSeek API Key
echo -n "YOUR_DEEPSEEK_API_KEY" | \
  gcloud secrets create DEEPSEEK_API_KEY --data-file=-

# TwelveData API Key (for market data)
echo -n "YOUR_TWELVEDATA_API_KEY" | \
  gcloud secrets create TWELVEDATA_API_KEY --data-file=-

# NewsAPI Key (optional)
echo -n "YOUR_NEWSAPI_KEY" | \
  gcloud secrets create NEWSAPI_KEY --data-file=-
```

### 3.2 Verify Secrets

```bash
# List all secrets
gcloud secrets list

# Test secret access
gcloud secrets versions access latest --secret="GOOGLE_SHEETS_SPREADSHEET_ID"
```

---

## 📦 STEP 4: Artifact Registry Setup

### 4.1 Create Docker Repository

```bash
# Create repository
gcloud artifacts repositories create mytrade-repo \
  --repository-format=docker \
  --location=$REGION \
  --description="MyTrade Docker repository"

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

---

## 🏗️ STEP 5: Build and Deploy Container

### 5.1 Build with Cloud Build

```bash
# Navigate to project directory
cd /home/user/mytrade-automation

# Submit build to Cloud Build
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_REGION=$REGION

# Monitor build
gcloud builds list --limit=5
```

### 5.2 Deploy to Cloud Run

```bash
# Deploy main orchestrator
gcloud run deploy mytrade-orchestrator \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/mytrade-repo/mytrade:latest \
  --platform=managed \
  --region=$REGION \
  --service-account=$SA_EMAIL \
  --no-allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=10 \
  --set-secrets=GOOGLE_SHEETS_SPREADSHEET_ID=GOOGLE_SHEETS_SPREADSHEET_ID:latest,\
TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest,\
TELEGRAM_CHAT_ID=TELEGRAM_CHAT_ID:latest,\
OPENAI_API_KEY=OPENAI_API_KEY:latest,\
ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,\
GEMINI_API_KEY=GEMINI_API_KEY:latest,\
XAI_API_KEY=XAI_API_KEY:latest,\
DEEPSEEK_API_KEY=DEEPSEEK_API_KEY:latest,\
TWELVEDATA_API_KEY=TWELVEDATA_API_KEY:latest,\
NEWSAPI_KEY=NEWSAPI_KEY:latest

# Get service URL
export SERVICE_URL=$(gcloud run services describe mytrade-orchestrator \
  --region=$REGION \
  --format="value(status.url)")

echo "Service URL: $SERVICE_URL"
```

---

## ⏰ STEP 6: Cloud Scheduler Setup

### 6.1 Create Scheduler Jobs

```bash
# Robot 1: Market Data Collector (Every 5 minutes)
gcloud scheduler jobs create http robot1-market-data \
  --schedule="*/5 * * * *" \
  --uri="${SERVICE_URL}/run_robot?robot=1" \
  --http-method=POST \
  --time-zone="UTC" \
  --location=$REGION \
  --oidc-service-account-email=$SA_EMAIL \
  --description="Robot 1: Market data collection every 5 minutes"

# Robot 2: News Monitor (Every 5 minutes)
gcloud scheduler jobs create http robot2-news-monitor \
  --schedule="*/5 * * * *" \
  --uri="${SERVICE_URL}/run_robot?robot=2" \
  --http-method=POST \
  --time-zone="UTC" \
  --location=$REGION \
  --oidc-service-account-email=$SA_EMAIL \
  --description="Robot 2: News monitoring every 5 minutes"

# Analysis Pipeline: Robots 3,8,7,4,6,5 (Every 30 minutes)
gcloud scheduler jobs create http analysis-pipeline \
  --schedule="*/30 * * * *" \
  --uri="${SERVICE_URL}/run_pipeline?robots=3,8,7,4,6,5" \
  --http-method=POST \
  --time-zone="UTC" \
  --location=$REGION \
  --oidc-service-account-email=$SA_EMAIL \
  --description="Full 30-min analysis pipeline"

# Robot 9: TP/SL Monitor (Every 3 minutes)
gcloud scheduler jobs create http robot9-tp-monitor \
  --schedule="*/3 * * * *" \
  --uri="${SERVICE_URL}/run_robot?robot=9" \
  --http-method=POST \
  --time-zone="UTC" \
  --location=$REGION \
  --oidc-service-account-email=$SA_EMAIL \
  --description="Robot 9: TP/SL real-time tracking"

# Robot 6: Weekly Report (Every Sunday at midnight)
gcloud scheduler jobs create http robot6-weekly-report \
  --schedule="0 0 * * 0" \
  --uri="${SERVICE_URL}/run_robot?robot=6" \
  --http-method=POST \
  --time-zone="UTC" \
  --location=$REGION \
  --oidc-service-account-email=$SA_EMAIL \
  --description="Robot 6: Weekly Telegram report"
```

### 6.2 Verify Scheduler Jobs

```bash
# List all jobs
gcloud scheduler jobs list --location=$REGION

# Test a job manually
gcloud scheduler jobs run robot1-market-data --location=$REGION
```

---

## 📊 STEP 7: Monitoring and Logging

### 7.1 View Logs

```bash
# View Cloud Run logs
gcloud run services logs read mytrade-orchestrator \
  --region=$REGION \
  --limit=50

# Follow logs in real-time
gcloud run services logs tail mytrade-orchestrator \
  --region=$REGION
```

### 7.2 Create Log-Based Alerts

```bash
# Create alert for errors
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="MyTrade Error Alert" \
  --condition-display-name="High error rate" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=60s
```

---

## 💰 STEP 8: Cost Optimization

### 8.1 Set Budget Alert

```bash
# Create budget (example: $50/month)
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="MyTrade Monthly Budget" \
  --budget-amount=50USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

### 8.2 Monitor Costs

```bash
# View current month costs
gcloud beta billing accounts list

# Export billing data to BigQuery (optional)
gcloud beta billing accounts set-billing-export \
  YOUR_BILLING_ACCOUNT_ID \
  --bigquery-table=PROJECT_ID.DATASET.TABLE
```

---

## 🔧 STEP 9: Update and Redeploy

### 9.1 Update Code

```bash
# Pull latest code
git pull origin main

# Rebuild and deploy
gcloud builds submit --config=cloudbuild.yaml

# Update Cloud Run service
gcloud run services update mytrade-orchestrator \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/mytrade-repo/mytrade:latest \
  --region=$REGION
```

### 9.2 Rollback (if needed)

```bash
# List revisions
gcloud run revisions list \
  --service=mytrade-orchestrator \
  --region=$REGION

# Rollback to previous revision
gcloud run services update-traffic mytrade-orchestrator \
  --to-revisions=REVISION_NAME=100 \
  --region=$REGION
```

---

## 🧪 STEP 10: Testing

### 10.1 Test Individual Robot

```bash
# Test Robot 1
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "${SERVICE_URL}/run_robot?robot=1"

# Check logs
gcloud run services logs read mytrade-orchestrator --region=$REGION --limit=20
```

### 10.2 Test Full Pipeline

```bash
# Trigger analysis pipeline
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "${SERVICE_URL}/run_pipeline?robots=3,8,7,4,6,5"
```

---

## 📱 STEP 11: Telegram Verification

After deployment, verify Telegram messages:

1. Wait for next scheduled run (check Cloud Scheduler)
2. Check Telegram channel for signals
3. Verify performance badge is showing
4. Check TRY currency pairs are included

---

## 🚨 Troubleshooting

### Common Issues

**Issue 1: "Permission Denied"**
```bash
# Grant run.invoker role to scheduler
gcloud run services add-iam-policy-binding mytrade-orchestrator \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.invoker" \
  --region=$REGION
```

**Issue 2: "Secret Not Found"**
```bash
# Verify secret exists
gcloud secrets describe SECRET_NAME

# Grant access
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

**Issue 3: "Container Build Failed"**
```bash
# Check build logs
gcloud builds list --limit=1
gcloud builds log BUILD_ID
```

---

## 📊 Expected Costs

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| Cloud Run | ~33,000 requests | $5-10 |
| Cloud Scheduler | 5 jobs | $0.30 |
| Secret Manager | 10 secrets | $0.18 |
| Cloud Build | 10 builds | $0 (free tier) |
| Artifact Registry | 1 GB storage | $0.10 |
| **TOTAL** | | **$5.58-10.58/month** |

---

## ✅ Production Checklist

- [ ] GCP Project created and billing enabled
- [ ] Service Account created with correct permissions
- [ ] All secrets added to Secret Manager
- [ ] Artifact Registry repository created
- [ ] Docker image built and pushed
- [ ] Cloud Run service deployed
- [ ] All 5 Cloud Scheduler jobs created
- [ ] Logs showing successful execution
- [ ] Telegram messages received
- [ ] Performance badge visible
- [ ] TRY currency pairs working
- [ ] Budget alerts configured
- [ ] Monitoring dashboard set up

---

## 🎯 Next Steps

1. Monitor first 24 hours of operation
2. Check Telegram for signal quality
3. Review Cloud Run logs for errors
4. Verify all robots running on schedule
5. Test manual triggers if needed

---

## 📞 Support

For issues:
1. Check logs: `gcloud run services logs read mytrade-orchestrator`
2. Review Cloud Scheduler: `gcloud scheduler jobs list`
3. Verify secrets: `gcloud secrets list`
4. Test manually: `curl -X POST $SERVICE_URL/run_robot?robot=1`

---

**Deployment Date**: [Fill in after deployment]
**Service URL**: [Fill in after deployment]
**Project ID**: [Fill in your project ID]

---

🎉 **Congratulations! Your MyTrade system is now running on Google Cloud!** 🚀
