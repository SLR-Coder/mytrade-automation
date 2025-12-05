# server.py
# -*- coding: utf-8 -*-
"""
HTTP Server for Cloud Run + Cloud Scheduler
Receives HTTP requests and triggers appropriate robots
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from flask import Flask, request, jsonify

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MyTrade-Server")

app = Flask(__name__)


def run_robots(robot_ids: str) -> dict:
    """
    Run specified robots

    Args:
        robot_ids: Comma-separated robot IDs (e.g., "1,2,3")

    Returns:
        Result dictionary with status and details
    """
    start_time = datetime.now()

    try:
        # Import and run main with robot selection
        from main import main_async

        # Set robot selection
        os.environ["ROBOT"] = robot_ids

        # Run async main
        result = asyncio.run(main_async())

        duration = (datetime.now() - start_time).total_seconds()

        return {
            "status": "success" if result == 0 else "partial_failure",
            "robots": robot_ids,
            "exit_code": result,
            "duration_seconds": duration,
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


@app.route("/", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "mytrade-automation",
        "timestamp": datetime.now().isoformat()
    })


@app.route("/run", methods=["POST"])
def run_endpoint():
    """
    Run robots endpoint

    Query params:
        robots: Comma-separated robot IDs (e.g., "1,2,3" or "3,8,7,4,5")

    Example:
        POST /run?robots=1
        POST /run?robots=3,8,7,4,5
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


# Specific endpoints for each job type
@app.route("/data-collection", methods=["POST"])
def data_collection():
    """Robot 1: Data Collection"""
    logger.info("Running Robot 1: Data Collection")
    result = run_robots("1")
    return jsonify(result), 200 if result["status"] == "success" else 500


@app.route("/news-monitor", methods=["POST"])
def news_monitor():
    """Robot 2: News Monitor"""
    logger.info("Running Robot 2: News Monitor")
    result = run_robots("2")
    return jsonify(result), 200 if result["status"] == "success" else 500


@app.route("/analysis-pipeline", methods=["POST"])
def analysis_pipeline():
    """Robots 3,8,7,4,5: Full Analysis Pipeline"""
    logger.info("Running Analysis Pipeline: Robots 3,8,7,4,5")
    result = run_robots("3,8,7,4,5")
    return jsonify(result), 200 if result["status"] == "success" else 500


@app.route("/tp-sl-monitor", methods=["POST"])
def tp_sl_monitor():
    """Robot 9: TP/SL Monitor"""
    logger.info("Running Robot 9: TP/SL Monitor")
    result = run_robots("9")
    return jsonify(result), 200 if result["status"] == "success" else 500


@app.route("/performance-tracker", methods=["POST"])
def performance_tracker():
    """Robot 6: Performance Tracker"""
    logger.info("Running Robot 6: Performance Tracker")
    result = run_robots("6")
    return jsonify(result), 200 if result["status"] == "success" else 500


@app.route("/weekly-report", methods=["POST"])
def weekly_report():
    """Weekly Telegram Report"""
    logger.info("Running Weekly Report")
    try:
        from robots import weekly_telegram_report
        weekly_telegram_report.run()
        return jsonify({
            "status": "success",
            "job": "weekly-report",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Weekly report error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
