#!/bin/bash
# =============================================================================
# MyTrade Automation - Cloud Run + Scheduler Deployment Script
# =============================================================================

set -e

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="${REGION:-europe-west1}"
SERVICE_NAME="mytrade-automation"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=============================================="
echo "  MyTrade Automation - Cloud Run Deployment"
echo "=============================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "=============================================="

# Step 1: Build Docker image
echo ""
echo "📦 Step 1: Building Docker image..."
docker build -t ${IMAGE_NAME} .

# Step 2: Push to GCR
echo ""
echo "📤 Step 2: Pushing to Container Registry..."
docker push ${IMAGE_NAME}

# Step 3: Deploy to Cloud Run
echo ""
echo "🚀 Step 3: Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 1 \
    --min-instances 0 \
    --max-instances 1 \
    --allow-unauthenticated \
    --set-env-vars "ENVIRONMENT=production"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo ""
echo "✅ Cloud Run deployed!"
echo "   URL: ${SERVICE_URL}"

# Step 4: Create Cloud Scheduler jobs
echo ""
echo "⏰ Step 4: Setting up Cloud Scheduler jobs..."

# Delete existing jobs (ignore errors if they don't exist)
echo "   Cleaning up existing jobs..."
gcloud scheduler jobs delete data-collection --location ${REGION} --quiet 2>/dev/null || true
gcloud scheduler jobs delete news-monitor --location ${REGION} --quiet 2>/dev/null || true
gcloud scheduler jobs delete analysis-pipeline --location ${REGION} --quiet 2>/dev/null || true
gcloud scheduler jobs delete tp-sl-monitor --location ${REGION} --quiet 2>/dev/null || true
gcloud scheduler jobs delete performance-tracker --location ${REGION} --quiet 2>/dev/null || true
gcloud scheduler jobs delete weekly-report --location ${REGION} --quiet 2>/dev/null || true

# Create new jobs
echo "   Creating scheduler jobs..."

# Robot 1: Data Collection - Every 5 minutes
gcloud scheduler jobs create http data-collection \
    --location ${REGION} \
    --schedule "*/5 * * * *" \
    --uri "${SERVICE_URL}/data-collection" \
    --http-method POST \
    --time-zone "UTC" \
    --description "Robot 1: Data collection every 5 minutes" \
    --attempt-deadline 180s

# Robot 2: News Monitor - Every 1 hour
gcloud scheduler jobs create http news-monitor \
    --location ${REGION} \
    --schedule "0 * * * *" \
    --uri "${SERVICE_URL}/news-monitor" \
    --http-method POST \
    --time-zone "UTC" \
    --description "Robot 2: News monitoring every hour" \
    --attempt-deadline 300s

# Analysis Pipeline - Every 30 minutes
gcloud scheduler jobs create http analysis-pipeline \
    --location ${REGION} \
    --schedule "*/30 * * * *" \
    --uri "${SERVICE_URL}/analysis-pipeline" \
    --http-method POST \
    --time-zone "UTC" \
    --description "Robots 3,8,7,4,5: Analysis pipeline every 30 min" \
    --attempt-deadline 540s

# Robot 9: TP/SL Monitor - Every 3 minutes
gcloud scheduler jobs create http tp-sl-monitor \
    --location ${REGION} \
    --schedule "*/3 * * * *" \
    --uri "${SERVICE_URL}/tp-sl-monitor" \
    --http-method POST \
    --time-zone "UTC" \
    --description "Robot 9: TP/SL monitor every 3 minutes" \
    --attempt-deadline 120s

# Robot 6: Performance Tracker - Daily at 23:00 UTC
gcloud scheduler jobs create http performance-tracker \
    --location ${REGION} \
    --schedule "0 23 * * *" \
    --uri "${SERVICE_URL}/performance-tracker" \
    --http-method POST \
    --time-zone "UTC" \
    --description "Robot 6: Performance tracker daily" \
    --attempt-deadline 180s

# Weekly Report - Sunday at 00:00 UTC
gcloud scheduler jobs create http weekly-report \
    --location ${REGION} \
    --schedule "0 0 * * 0" \
    --uri "${SERVICE_URL}/weekly-report" \
    --http-method POST \
    --time-zone "UTC" \
    --description "Weekly Telegram report" \
    --attempt-deadline 300s

echo ""
echo "=============================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=============================================="
echo ""
echo "Cloud Run URL: ${SERVICE_URL}"
echo ""
echo "Scheduler Jobs Created:"
gcloud scheduler jobs list --location ${REGION}
echo ""
echo "To test manually:"
echo "  curl -X POST ${SERVICE_URL}/data-collection"
echo "  curl -X POST ${SERVICE_URL}/analysis-pipeline"
echo ""
echo "To view logs:"
echo "  gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}' --limit 50"
echo ""
