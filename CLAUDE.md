# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup and Installation
```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your Convex URL and preferences
```

### Running the Scraper

#### Web API (Recommended)
```bash
# Start the Flask web API server
python3 app.py

# Available endpoints:
# GET/POST /health          - Health check
# GET      /status          - Check scraping status
# GET      /logs            - View recent activity logs
# GET      /convex/test     - Test Convex database connection
# GET/POST /scrape          - Scrape current month
# GET/POST /scrape/<month>  - Scrape specific month

# Example API usage:
curl http://localhost:5000/scrape
curl http://localhost:5000/scrape/january
curl http://localhost:5000/status
curl -X POST http://localhost:5000/scrape
```

#### CLI (Legacy)
```bash
# Scrape current month
python3 scraper.py

# Scrape specific months (supports: this, next, or month names)
python3 scraper.py --months this next january february

# Simple scraping (basic version)
python3 simple_scrape.py
```

## Architecture

This is a Python-based Forex Factory calendar news scraper that uses Selenium WebDriver to extract economic news events. The project consists of 6 main components:

### Core Files
- **app.py**: Flask web API server that wraps the scraper with REST endpoints, logging, and status monitoring
- **scraper.py**: Main scraper with advanced features including multi-month support, timezone conversion, and robust data parsing
- **simple_scrape.py**: Basic scraper implementation for single month scraping
- **config.py**: Configuration settings for filtering (currencies, impact levels, element mappings, timezone settings)
- **utils.py**: Utility functions for data processing, timezone conversion, CSV output, and flexible data storage
- **convex_client.py**: Convex database integration for saving scraped data to your backend
- **.env**: Environment configuration (Convex URL, storage method, API settings)

### Data Flow
1. **API Request**: HTTP request triggers scraping via Flask endpoints
2. **Background Processing**: Scraping runs in separate thread to avoid API timeouts
3. **WebDriver**: Chrome browser navigates to Forex Factory calendar
4. **Dynamic Loading**: Page scrolls to load all events (30-60 seconds)
5. **Data Extraction**: HTML table parsing using CSS class mappings from config
6. **Filtering**: Currency and impact level restrictions applied
7. **Timezone Conversion**: Times transformed from browser timezone to target timezone
8. **Flexible Storage**: Data saved to CSV files and/or Convex database based on configuration
9. **Status Updates**: Real-time logging and status tracking available via API endpoints

### Configuration System

**Static Configuration (`config.py`)**:
- `ALLOWED_CURRENCY_CODES`: Filter events by currency (default: USD only)
- `ALLOWED_IMPACT_COLORS`: Filter by impact level (default: red, gray)
- `TARGET_TIMEZONE`: Convert times to specific timezone (default: US/Eastern)
- `ICON_COLOR_MAP`: Maps CSS classes to impact colors
- `ALLOWED_ELEMENT_TYPES`: Maps HTML classes to data fields

**Environment Configuration (`.env`)**:
- `CONVEX_URL`: Your Convex database deployment URL
- `DATA_STORAGE`: Storage method - "csv", "convex", or "both"
- `TARGET_TIMEZONE`: Convert times to specific timezone
- `ALLOWED_CURRENCY_CODES`: Filter events by currency (comma-separated)
- `ALLOWED_IMPACT_COLORS`: Filter by impact level (comma-separated)
- `FLASK_DEBUG`: Enable Flask debug mode
- `FLASK_HOST`: Flask server host (default: 0.0.0.0)
- `FLASK_PORT`: Flask server port (default: 5000)

### Key Features
- **Web API**: RESTful endpoints with real-time status monitoring
- **Flexible Storage**: CSV files, Convex database, or both simultaneously
- **Background Processing**: Non-blocking API responses with threading
- **Comprehensive Logging**: Activity logs accessible via API endpoints
- **Multi-month Support**: Scrape current, next, or specific months
- **Timezone Handling**: Automatic detection and conversion
- **Error Recovery**: Robust error handling with detailed logging
- **Environment-based Config**: Easy deployment across different environments

### Deployment Ready
The scraper is containerization-ready with Flask web API, environment variable configuration, and flexible data storage options. Includes Dockerfile with modern Chrome installation and dependency handling. Suitable for deployment on VPS platforms like Dokploy with scheduled execution via cron jobs or API triggers.

### Data Storage
- **CSV Files**: Saved in `/news/` directory with format `{Month}_{Year}_news.csv`
- **Convex Database**: Real-time database integration with automatic syncing
- **Flexible Configuration**: Choose between CSV only, Convex only, or both simultaneously