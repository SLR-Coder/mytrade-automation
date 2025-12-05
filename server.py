# server.py
# -*- coding: utf-8 -*-
"""
HTTP Server for Cloud Run + Cloud Scheduler
Receives HTTP requests and triggers appropriate robots
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from flask import Flask, request, jsonify

# Setup logging BEFORE any imports that might use it
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MyTrade-Server")

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "mytrade-automation",
        "timestamp": datetime.now().isoformat()
    })


@app.route("/run", methods=["POST", "GET"])
def run_endpoint():
    """
    Run robots endpoint

    Query params:
        robots: Comma-separated robot IDs (e.g., "1,2,3" or "3,8,7,4,5")
    """
    robots = request.args.get("robots", "")

    if not robots:
        return jsonify({
            "status": "error",
            "error": "Missing 'robots' parameter"
        }), 400

    logger.info(f"Received request to run robots: {robots}")
    result = run_robots(robots)

    status_code = 200 if result["status"] == "success" else 500
    return jsonify(result), status_code


def run_robots(robot_ids: str) -> dict:
    """Run specified robots"""
    start_time = datetime.now()

    try:
        # Run using subprocess to avoid thread/signal issues
        result = subprocess.run(
            [sys.executable, "main.py", robot_ids],
            capture_output=True,
            text=True,
            timeout=540  # 9 minutes max
        )

        duration = (datetime.now() - start_time).total_seconds()

        return {
            "status": "success" if result.returncode == 0 else "partial_failure",
            "robots": robot_ids,
            "exit_code": result.returncode,
            "duration_seconds": duration,
            "stdout": result.stdout[-2000:] if result.stdout else "",  # Last 2000 chars
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "timestamp": datetime.now().isoformat()
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "robots": robot_ids,
            "error": "Execution timed out after 9 minutes",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error running robots {robot_ids}: {e}", exc_info=True)
        return {
            "status": "error",
            "robots": robot_ids,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Specific endpoints for each job type
@app.route("/data-collection", methods=["POST", "GET"])
def data_collection():
    """Robot 1: Data Collection"""
    logger.info("Running Robot 1: Data Collection")
    result = run_robots("1")
    return jsonify(result), 200 if result["status"] == "success" else 500


@app.route("/news-monitor", methods=["POST", "GET"])
def news_monitor():
    """Robot 2: News Monitor"""
    logger.info("Running Robot 2: News Monitor")
    result = run_robots("2")
    return jsonify(result), 200 if result["status"] == "success" else 500


@app.route("/analysis-pipeline", methods=["POST", "GET"])
def analysis_pipeline():
    """
    Robots 3,8,7,4,5: Full Analysis Pipeline

    Waits for Robot 1 to complete before starting analysis.
    Robot 1 runs at :00, :05, :10... and takes ~50 seconds.
    This endpoint should be scheduled at :02, :32 (2 min offset).
    """
    import time

    # Check if we should wait for Robot 1
    wait_seconds = int(request.args.get("wait", "0"))
    if wait_seconds > 0:
        logger.info(f"Waiting {wait_seconds}s for Robot 1 to complete...")
        time.sleep(wait_seconds)

    logger.info("Running Analysis Pipeline: Robots 3,8,7,4,5")
    result = run_robots("3,8,7,4,5")
    return jsonify(result), 200 if result["status"] == "success" else 500


@app.route("/tp-sl-monitor", methods=["POST", "GET"])
def tp_sl_monitor():
    """Robot 9: TP/SL Monitor"""
    logger.info("Running Robot 9: TP/SL Monitor")
    result = run_robots("9")
    return jsonify(result), 200 if result["status"] == "success" else 500


@app.route("/performance-tracker", methods=["POST", "GET"])
def performance_tracker():
    """Robot 6: Performance Tracker"""
    logger.info("Running Robot 6: Performance Tracker")
    result = run_robots("6")
    return jsonify(result), 200 if result["status"] == "success" else 500


@app.route("/weekly-report", methods=["POST", "GET"])
def weekly_report():
    """Weekly Telegram Report"""
    logger.info("Running Weekly Report")
    try:
        result = subprocess.run(
            [sys.executable, "-c", "from robots import weekly_telegram_report; weekly_telegram_report.run()"],
            capture_output=True,
            text=True,
            timeout=300
        )
        return jsonify({
            "status": "success" if result.returncode == 0 else "error",
            "job": "weekly-report",
            "stdout": result.stdout[-1000:] if result.stdout else "",
            "timestamp": datetime.now().isoformat()
        }), 200 if result.returncode == 0 else 500
    except Exception as e:
        logger.error(f"Weekly report error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


# This is important for Cloud Run
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting MyTrade server on port {port}")
    # Use threaded=True for better concurrency
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
