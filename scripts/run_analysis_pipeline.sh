#!/bin/bash
# run_analysis_pipeline.sh
# Full analysis pipeline - runs every 30 minutes
# Analyzes last 6 batches (30 minutes of data) collected by Robot 1
#
# Production-ready with:
# - Retry logic for rate limit errors
# - Exponential backoff
# - Delays between robots to avoid API quota issues

set -e  # Exit on error

echo "=============================================="
echo "🚀 STARTING 30-MINUTE ANALYSIS PIPELINE"
echo "=============================================="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Set Python path
export PYTHONPATH=$PWD

# Function to run robot with retry logic
run_robot_with_retry() {
    local robot_name=$1
    local robot_file=$2
    local max_retries=3
    local retry_count=0
    local wait_time=10

    while [ $retry_count -lt $max_retries ]; do
        echo "🤖 Attempting: $robot_name (try $((retry_count + 1))/$max_retries)"

        if python3 "$robot_file"; then
            echo "✅ $robot_name completed successfully"
            return 0
        else
            retry_count=$((retry_count + 1))

            if [ $retry_count -lt $max_retries ]; then
                echo "⚠️  $robot_name failed, waiting ${wait_time}s before retry..."
                sleep $wait_time
                wait_time=$((wait_time * 2))  # Exponential backoff
            else
                echo "❌ $robot_name failed after $max_retries attempts"
                return 1
            fi
        fi
    done
}

# Function to run optional robot (won't fail pipeline)
run_optional_robot() {
    local robot_name=$1
    local robot_file=$2

    echo "🤖 Running optional: $robot_name"

    if python3 "$robot_file"; then
        echo "✅ $robot_name completed successfully"
    else
        echo "⚠️  $robot_name failed (optional, continuing...)"
    fi
}

# ============================================================================
# STEP 1: AI Signal Generator (Robot 3)
# ============================================================================
echo "🤖 [1/6] Running Robot 3: AI Signal Generator..."
run_robot_with_retry "Robot 3" "robots/ai_signal_generator.py" || exit 1
echo ""
echo "⏳ Waiting 10 seconds (rate limit prevention)..."
sleep 10
echo ""

# ============================================================================
# STEP 2: Personal AI Analyst (Robot 8)
# ============================================================================
echo "🧠 [2/6] Running Robot 8: Personal AI Analyst..."
run_robot_with_retry "Robot 8" "robots/personal_ai_analyst.py" || exit 1
echo ""
echo "⏳ Waiting 10 seconds (rate limit prevention)..."
sleep 10
echo ""

# ============================================================================
# STEP 3: AI Command Center (Robot 7)
# ============================================================================
echo "👨‍✈️ [3/6] Running Robot 7: AI Command Center..."
run_robot_with_retry "Robot 7" "robots/ai_command_center.py" || exit 1
echo ""
echo "⏳ Waiting 10 seconds (rate limit prevention)..."
sleep 10
echo ""

# ============================================================================
# STEP 4: Chart Generator (Robot 4) - OPTIONAL
# ============================================================================
echo "📊 [4/6] Running Robot 4: Chart Generator (optional)..."
run_optional_robot "Robot 4" "robots/chart_generator.py"
echo ""
echo "⏳ Waiting 10 seconds (rate limit prevention)..."
sleep 10
echo ""

# ============================================================================
# STEP 5: Performance Tracker (Robot 6) - OLD VERSION
# ============================================================================
echo "📈 [5/6] Running Robot 6: Performance Tracker..."
# Note: Using old performance_tracker.py (database version)
# Weekly report is separate (run_weekly_report.sh)
if [ -f "robots/performance_tracker.py" ]; then
    run_optional_robot "Robot 6" "robots/performance_tracker.py"
else
    echo "⚠️  Robot 6 (performance_tracker.py) not found, skipping..."
fi
echo ""
echo "⏳ Waiting 10 seconds (rate limit prevention)..."
sleep 10
echo ""

# ============================================================================
# STEP 6: Telegram Publisher (Robot 5)
# ============================================================================
echo "📱 [6/6] Running Robot 5: Telegram Publisher..."
run_robot_with_retry "Robot 5" "robots/telegram_publisher.py" || exit 1
echo ""

echo "=============================================="
echo "✅ PIPELINE COMPLETED SUCCESSFULLY"
echo "=============================================="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "Summary:"
echo "  - Robot 3: AI Signal Generator ✅"
echo "  - Robot 8: Personal AI Analyst ✅"
echo "  - Robot 7: AI Command Center ✅"
echo "  - Robot 4: Chart Generator (optional)"
echo "  - Robot 6: Performance Tracker (optional)"
echo "  - Robot 5: Telegram Publisher ✅"
echo ""
echo "Next steps:"
echo "  - Robot 9 monitors TP/SL in real-time (separate job)"
echo "  - Robot 6 Weekly Report runs on Sundays (separate job)"
