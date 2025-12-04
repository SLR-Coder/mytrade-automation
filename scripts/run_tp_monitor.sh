#!/bin/bash
# run_tp_monitor.sh
# Robot 9: TP/SL Monitor - runs every 3 minutes
# Monitors open positions and sends Telegram notifications when TP/SL hit
#
# Production-ready with:
# - Retry logic for rate limit errors
# - Exponential backoff

set -e  # Exit on error

echo "=============================================="
echo "🎯 ROBOT 9: TP/SL MONITOR"
echo "=============================================="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Set Python path
export PYTHONPATH=$PWD

# Retry logic
max_retries=3
retry_count=0
wait_time=5

while [ $retry_count -lt $max_retries ]; do
    echo "🤖 Running Robot 9 (attempt $((retry_count + 1))/$max_retries)..."

    if python3 robots/tp_monitor.py; then
        echo "✅ Robot 9 completed successfully"
        echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
        exit 0
    else
        exit_code=$?
        retry_count=$((retry_count + 1))

        if [ $retry_count -lt $max_retries ]; then
            echo "⚠️  Robot 9 failed (exit code: $exit_code)"
            echo "⏳ Waiting ${wait_time}s before retry..."
            sleep $wait_time
            wait_time=$((wait_time * 2))  # Exponential backoff: 5s, 10s, 20s
        else
            echo "❌ Robot 9 failed after $max_retries attempts"
            echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
            exit 1
        fi
    fi
done
