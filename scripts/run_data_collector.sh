#!/bin/bash
# run_data_collector.sh
# Robot 1: Market Data Collector - runs every 5 minutes
# Collects market data ONLY (no AI analysis) for temporal trend analysis
#
# Production-ready with:
# - Retry logic for rate limit errors
# - Exponential backoff

set -e  # Exit on error

echo "=============================================="
echo "📊 ROBOT 1: MARKET DATA COLLECTOR"
echo "=============================================="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Set Python path
export PYTHONPATH=$PWD

# Retry logic
max_retries=3
retry_count=0
wait_time=10

while [ $retry_count -lt $max_retries ]; do
    echo "🔍 Collecting market data (attempt $((retry_count + 1))/$max_retries)..."

    if python3 robots/market_harvester.py; then
        echo "✅ Robot 1 completed successfully"
        echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
        exit 0
    else
        exit_code=$?
        retry_count=$((retry_count + 1))

        if [ $retry_count -lt $max_retries ]; then
            echo "⚠️  Robot 1 failed (exit code: $exit_code)"
            echo "⏳ Waiting ${wait_time}s before retry..."
            sleep $wait_time
            wait_time=$((wait_time * 2))  # Exponential backoff: 10s, 20s, 40s
        else
            echo "❌ Robot 1 failed after $max_retries attempts"
            echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
            exit 1
        fi
    fi
done
