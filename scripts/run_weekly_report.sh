#!/bin/bash
# run_weekly_report.sh
# Robot 6: Weekly Telegram Performance Report
# Runs once per week (e.g., every Sunday)
#
# Production-ready with:
# - Retry logic for rate limit errors
# - Exponential backoff

set -e  # Exit on error

echo "=============================================="
echo "📊 ROBOT 6: WEEKLY TELEGRAM REPORT"
echo "=============================================="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Set Python path
export PYTHONPATH=$PWD

# Retry logic
max_retries=3
retry_count=0
wait_time=15

while [ $retry_count -lt $max_retries ]; do
    echo "📊 Generating weekly report (attempt $((retry_count + 1))/$max_retries)..."

    if python3 robots/weekly_telegram_report.py; then
        echo "✅ Robot 6 completed successfully"
        echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
        exit 0
    else
        exit_code=$?
        retry_count=$((retry_count + 1))

        if [ $retry_count -lt $max_retries ]; then
            echo "⚠️  Robot 6 failed (exit code: $exit_code)"
            echo "⏳ Waiting ${wait_time}s before retry..."
            sleep $wait_time
            wait_time=$((wait_time * 2))  # Exponential backoff: 15s, 30s, 60s
        else
            echo "❌ Robot 6 failed after $max_retries attempts"
            echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
            exit 1
        fi
    fi
done
