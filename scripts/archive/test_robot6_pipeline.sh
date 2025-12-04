#!/bin/bash
# Robot 6 test pipeline

echo "============================================================"
echo "🔄 STEP 1: Google Sheets → Database Sync"
echo "============================================================"
export PYTHONPATH="$PWD:$PYTHONPATH"
python3 robots/sheets_to_db_sync.py

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "📊 STEP 2: Robot 6 - Performance Tracker"
    echo "============================================================"
    python3 robots/performance_tracker.py
else
    echo "❌ Sync failed, skipping Robot 6"
    exit 1
fi
