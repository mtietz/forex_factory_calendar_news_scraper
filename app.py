from flask import Flask, jsonify, request
import logging
from datetime import datetime
import threading
import time
import traceback
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import your existing scraper functions
from scraper import init_driver, scroll_to_end, parse_table, scrape_all_calendars, scrape_single_source, get_month_year_from_param, SOURCE_FOREX, SOURCE_ENERGY
from config import FOREX_FACTORY_URL, ENERGY_EXCH_URL
from utils import save_data
import config

# Import Convex testing functions
try:
    from convex_client import test_convex_connection, is_convex_available
    CONVEX_INTEGRATION = True
except ImportError:
    CONVEX_INTEGRATION = False

# Configure logging so we can see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask application instance
app = Flask(__name__)

# Global variable to track scraping status
# In production, you'd use a database, but this works for learning
scraping_status = {
    "is_running": False,
    "current_month": None,
    "last_run": None,
    "last_error": None,
    "success_count": 0,
    "error_count": 0
}

# Store recent activity logs (last 50 entries)
activity_logs = []

def add_activity_log(level, message):
    """Helper function to track activity for the /logs endpoint"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message
    }
    activity_logs.append(log_entry)

    # Keep only last 50 logs to prevent memory issues
    if len(activity_logs) > 50:
        activity_logs.pop(0)

    # Also log to console
    if level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)


# STEP 1: Health Check Endpoint
@app.route('/health')
def health_check():
    """
    Simple endpoint to check if the service is running.
    This is useful for monitoring and load balancers.
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "forex-scraper"
    })


# STEP 2: Status Endpoint
@app.route('/status')
def get_status():
    """
    Returns current scraping status.
    Shows if scraper is running, last run time, etc.
    """
    return jsonify(scraping_status)


# NEW: Logs Endpoint for Debugging
@app.route('/logs')
def get_logs():
    """
    Returns recent activity logs.
    Useful for debugging when things go wrong.
    """
    return jsonify({
        "logs": activity_logs[-20:],  # Last 20 logs
        "total_logs": len(activity_logs)
    })


# NEW: Convex Connection Test
@app.route('/convex/test')
def test_convex():
    """
    Test Convex database connection.
    Useful for debugging database integration.
    """
    if not CONVEX_INTEGRATION:
        return jsonify({
            "available": False,
            "error": "Convex client not imported"
        })

    connection_test = test_convex_connection()
    return jsonify(connection_test)


# STEP 3: Main Scrape Endpoint (Current Month)
@app.route('/scrape', methods=['GET', 'POST'])
def scrape_current():
    """
    Triggers scraping for current month.
    Both GET and POST work - GET is easier to test in browser.
    """
    if scraping_status["is_running"]:
        return jsonify({
            "error": "Scraping already in progress",
            "current_month": scraping_status["current_month"]
        }), 409  # 409 = Conflict status code

    # Run scraping in background thread so API responds immediately
    thread = threading.Thread(target=scrape_month, args=["this"])
    thread.start()

    return jsonify({
        "message": "Scraping started for current month",
        "status": "started",
        "check_status_at": "/status"
    })


# STEP 4: Specific Month Endpoint
@app.route('/scrape/<month>', methods=['GET', 'POST'])
def scrape_specific_month(month):
    """
    Triggers scraping for specific month.
    URL parameter 'month' can be: 'this', 'next', 'january', 'february', etc.
    """
    if scraping_status["is_running"]:
        return jsonify({
            "error": "Scraping already in progress",
            "current_month": scraping_status["current_month"]
        }), 409

    # Validate month parameter
    valid_months = [
        'this', 'next', 'january', 'february', 'march', 'april',
        'may', 'june', 'july', 'august', 'september', 'october',
        'november', 'december'
    ]

    if month.lower() not in valid_months:
        return jsonify({
            "error": f"Invalid month: {month}",
            "valid_months": valid_months
        }), 400  # 400 = Bad Request

    # Run scraping in background thread
    thread = threading.Thread(target=scrape_month, args=[month.lower()])
    thread.start()

    return jsonify({
        "message": f"Scraping started for {month}",
        "status": "started",
        "check_status_at": "/status"
    })


def scrape_month(month_param):
    """
    This function does the actual scraping work for BOTH calendars.
    Scrapes Forex Factory and Energy Exchange calendars.
    Runs in background thread so API doesn't hang.
    """
    global scraping_status

    # Update status to running
    scraping_status["is_running"] = True
    scraping_status["current_month"] = month_param
    scraping_status["last_error"] = None

    try:
        add_activity_log("INFO", f"Starting scrape for month: {month_param} (both calendars)")

        param = month_param.lower()
        month, year = get_month_year_from_param(param)

        # Initialize Chrome driver
        add_activity_log("INFO", "Initializing Chrome WebDriver...")
        driver = init_driver()

        # Detect timezone
        driver.get(FOREX_FACTORY_URL)
        detected_tz = driver.execute_script("return Intl.DateTimeFormat().resolvedOptions().timeZone")
        add_activity_log("INFO", f"Browser timezone detected: {detected_tz}")
        config.SCRAPER_TIMEZONE = detected_tz

        storage_method = os.getenv('DATA_STORAGE', 'both')
        total_forex = 0
        total_energy = 0

        # ========== SCRAPE FOREX FACTORY ==========
        add_activity_log("INFO", f"Scraping Forex Factory for {month} {year}...")
        forex_url = f"{FOREX_FACTORY_URL}?month={param}"
        try:
            driver.get(forex_url)
            scroll_to_end(driver)
            forex_data, _ = parse_table(driver, month, str(year), SOURCE_FOREX)
            total_forex = len(forex_data)
            add_activity_log("INFO", f"Parsed {total_forex} events from Forex Factory")

            # Save forex data
            forex_save_results = save_data(forex_data, month, str(year), storage_method, replace_existing=True, source=SOURCE_FOREX)
            if forex_save_results["csv"]["success"]:
                add_activity_log("INFO", f"✅ Forex CSV saved successfully")
            if forex_save_results["convex"]["success"]:
                add_activity_log("INFO", f"✅ Forex Convex saved {forex_save_results['convex']['saved_count']} records")
        except Exception as e:
            add_activity_log("ERROR", f"❌ Forex Factory scrape failed: {str(e)}")

        # ========== SCRAPE ENERGY EXCHANGE ==========
        add_activity_log("INFO", f"Scraping Energy Exchange for {month} {year}...")
        energy_url = f"{ENERGY_EXCH_URL}?month={param}"
        try:
            driver.get(energy_url)
            scroll_to_end(driver)
            energy_data, _ = parse_table(driver, month, str(year), SOURCE_ENERGY)
            total_energy = len(energy_data)
            add_activity_log("INFO", f"Parsed {total_energy} events from Energy Exchange")

            # Save energy data
            energy_save_results = save_data(energy_data, month, str(year), storage_method, replace_existing=True, source=SOURCE_ENERGY)
            if energy_save_results["csv"]["success"]:
                add_activity_log("INFO", f"✅ Energy CSV saved successfully")
            if energy_save_results["convex"]["success"]:
                add_activity_log("INFO", f"✅ Energy Convex saved {energy_save_results['convex']['saved_count']} records")
        except Exception as e:
            add_activity_log("ERROR", f"❌ Energy Exchange scrape failed: {str(e)}")

        # Clean up WebDriver
        driver.quit()
        add_activity_log("INFO", "WebDriver closed successfully")

        # Update status - SUCCESS
        scraping_status["is_running"] = False
        scraping_status["current_month"] = None
        scraping_status["last_run"] = datetime.now().isoformat()
        scraping_status["success_count"] += 1

        add_activity_log("INFO", f"✅ Completed scraping for {month} {year} - Total: {total_forex + total_energy} events (Forex: {total_forex}, Energy: {total_energy})")

    except Exception as e:
        # Get full error details including stack trace
        error_details = traceback.format_exc()

        # Update status - ERROR
        scraping_status["is_running"] = False
        scraping_status["current_month"] = None
        scraping_status["last_error"] = str(e)
        scraping_status["error_count"] += 1

        # Log detailed error information
        add_activity_log("ERROR", f"❌ Scraping failed: {str(e)}")
        add_activity_log("ERROR", f"Full error trace: {error_details}")

        # Try to clean up WebDriver if it exists
        try:
            if 'driver' in locals():
                driver.quit()
                add_activity_log("INFO", "WebDriver cleaned up after error")
        except:
            pass  # Ignore cleanup errors


if __name__ == '__main__':
    """
    This runs the Flask development server.
    - debug=True: Automatically restarts when you change code
    - host='0.0.0.0': Makes it accessible from other machines
    - port=5000: Default Flask port
    """
    print("🚀 Starting Forex & Energy Calendar Scraper API...")
    print("\n📍 Available endpoints:")
    print("  GET  /health          - Health check")
    print("  GET  /status          - Check scraping status")
    print("  GET  /logs            - View recent activity logs")
    print("  GET  /convex/test     - Test Convex database connection")
    print("  GET  /scrape          - Scrape current month (both calendars)")
    print("  GET  /scrape/<month>  - Scrape specific month (both calendars)")

    # Show environment configuration
    storage_method = os.getenv('DATA_STORAGE', 'both')
    convex_url = os.getenv('CONVEX_URL', 'Not configured')
    print(f"\n⚙️  Configuration:")
    print(f"  Storage method: {storage_method}")
    print(f"  Convex URL: {convex_url}")
    print(f"  Convex integration: {'✅ Available' if CONVEX_INTEGRATION else '❌ Not available'}")

    print(f"\n📊 Data Sources:")
    print(f"  - Forex Factory: {FOREX_FACTORY_URL}")
    print(f"  - Energy Exchange: {ENERGY_EXCH_URL}")

    print(f"\n🌐 Access at: http://localhost:5000")
    print("💡 Try: curl http://localhost:5000/health")

    app.run(debug=True, host='0.0.0.0', port=5000)