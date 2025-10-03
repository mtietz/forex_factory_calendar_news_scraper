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
from scraper import init_driver, scroll_to_end, parse_table
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
    This function does the actual scraping work.
    It's a modified version of your main() function.
    Runs in background thread so API doesn't hang.
    """
    global scraping_status

    # Update status to running
    scraping_status["is_running"] = True
    scraping_status["current_month"] = month_param
    scraping_status["last_error"] = None

    try:
        add_activity_log("INFO", f"Starting scrape for month: {month_param}")

        # This is copied from your main() function
        param = month_param.lower()
        url = f"https://www.forexfactory.com/calendar?month={param}"
        add_activity_log("INFO", f"Navigating to {url}")

        # Initialize Chrome driver
        add_activity_log("INFO", "Initializing Chrome WebDriver...")
        driver = init_driver()
        driver.get(url)

        # Detect timezone (from your code)
        detected_tz = driver.execute_script("return Intl.DateTimeFormat().resolvedOptions().timeZone")
        add_activity_log("INFO", f"Browser timezone detected: {detected_tz}")
        config.SCRAPER_TIMEZONE = detected_tz

        # Scroll to load all content (from your code)
        add_activity_log("INFO", "Scrolling page to load all events...")
        scroll_to_end(driver)

        # Determine month name and year (from your code)
        if param == "this":
            now = datetime.now()
            month = now.strftime("%B")
            year = now.year
        elif param == "next":
            now = datetime.now()
            next_month = (now.month % 12) + 1
            year = now.year if now.month < 12 else now.year + 1
            month = datetime(year, next_month, 1).strftime("%B")
        else:
            month = param.capitalize()
            year = datetime.now().year

        add_activity_log("INFO", f"Parsing data for {month} {year}")

        # Parse the table (your existing function)
        data, _ = parse_table(driver, month, str(year))
        add_activity_log("INFO", f"Parsed {len(data)} events from calendar")

        # Clean up WebDriver first
        driver.quit()
        add_activity_log("INFO", "WebDriver closed successfully")

        # Save data using new flexible storage system
        storage_method = os.getenv('DATA_STORAGE', 'both')
        add_activity_log("INFO", f"Saving data using method: {storage_method}")

        # Replace existing events to ensure deleted events on Forex Factory are also removed
        save_results = save_data(data, month, str(year), storage_method, replace_existing=True)

        # Log storage results
        if save_results["csv"]["attempted"]:
            if save_results["csv"]["success"]:
                add_activity_log("INFO", f"✅ CSV saved successfully")
            else:
                add_activity_log("ERROR", f"❌ CSV save failed: {save_results['csv']['error']}")

        if save_results["convex"]["attempted"]:
            if save_results["convex"]["success"]:
                count = save_results["convex"]["saved_count"]
                add_activity_log("INFO", f"✅ Convex saved {count} records successfully")
            else:
                add_activity_log("ERROR", f"❌ Convex save failed: {save_results['convex']['error']}")

        # Update status - SUCCESS
        scraping_status["is_running"] = False
        scraping_status["current_month"] = None
        scraping_status["last_run"] = datetime.now().isoformat()
        scraping_status["success_count"] += 1

        add_activity_log("INFO", f"✅ Successfully completed scraping for {month} {year} - Storage results: {save_results}")

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
    print("🚀 Starting Forex Factory Scraper API...")
    print("\n📍 Available endpoints:")
    print("  GET  /health          - Health check")
    print("  GET  /status          - Check scraping status")
    print("  GET  /logs            - View recent activity logs")
    print("  GET  /convex/test     - Test Convex database connection")
    print("  GET  /scrape          - Scrape current month")
    print("  GET  /scrape/<month>  - Scrape specific month")

    # Show environment configuration
    storage_method = os.getenv('DATA_STORAGE', 'both')
    convex_url = os.getenv('CONVEX_URL', 'Not configured')
    print(f"\n⚙️  Configuration:")
    print(f"  Storage method: {storage_method}")
    print(f"  Convex URL: {convex_url}")
    print(f"  Convex integration: {'✅ Available' if CONVEX_INTEGRATION else '❌ Not available'}")

    print(f"\n🌐 Access at: http://localhost:5000")
    print("💡 Try: curl http://localhost:5000/health")

    app.run(debug=True, host='0.0.0.0', port=5000)