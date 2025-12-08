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
python3 app.py

# Available endpoints:
# GET/POST /health          - Health check
# GET      /status          - Check scraping status
# GET      /logs            - View recent activity logs
# GET      /convex/test     - Test Convex database connection
# GET/POST /scrape          - Scrape current month (both calendars)
# GET/POST /scrape/<month>  - Scrape specific month (both calendars)
```

#### CLI
```bash
python3 scraper.py                              # Current month (both calendars)
python3 scraper.py --months this next january   # Multiple months
python3 scraper.py --source forex               # Forex Factory only
python3 scraper.py --source energy              # Energy Exchange only
python3 scraper.py --source all                 # Both (default)
```

#### Docker
```bash
docker build -t forex-scraper .
docker run -p 5000:5000 --env-file .env forex-scraper
```

## Architecture

Python-based calendar scraper using Selenium WebDriver to extract economic news events from two sources:
- **Forex Factory** (forexfactory.com/calendar) - Currency/forex news
- **Energy Exchange** (energyexch.com/calendar) - Energy/commodity news

### Core Components
- **app.py**: Flask API server with background threading for non-blocking scrape operations
- **scraper.py**: Main scraper with `scrape_all_calendars()`, `scrape_single_source()`, `parse_table()` functions
- **utils.py**: Data reformatting, timezone conversion, and flexible storage (`save_data()` supports CSV/Convex/both)
- **config.py**: Static filtering rules, CSS class mappings, and calendar URLs
- **convex_client.py**: Convex database integration with source-aware `save_to_convex()`, `delete_events_by_month()`

### Data Flow
1. API request triggers `scrape_month()` in background thread
2. Selenium Chrome driver scrapes both Forex Factory and Energy Exchange sequentially
3. `scroll_to_end()` loads all events via infinite scroll (30-60 seconds per calendar)
4. `parse_table()` extracts data using CSS class mappings, adds `source` field to each row
5. `reformat_data()` applies source-specific filtering and timezone conversion
6. `save_data()` writes to separate CSV files and/or Convex database per source

### Configuration

**Environment variables (`.env`)**:
- `CONVEX_URL`: Convex deployment URL
- `DATA_STORAGE`: `csv`, `convex`, or `both`
- `TARGET_TIMEZONE`: Output timezone (default: US/Eastern)
- `ALLOWED_CURRENCY_CODES`: Forex currency filter (e.g., USD)
- `ALLOWED_ENERGY_CODES`: Energy commodity filter (e.g., OIL,NG,BRENT,WTI)
- `ALLOWED_IMPACT_COLORS`: Impact filter for both (red, orange, yellow, gray)

**Static config (`config.py`)**:
- `FOREX_FACTORY_URL`, `ENERGY_EXCH_URL`: Calendar base URLs
- `ALLOWED_ELEMENT_TYPES`: Maps CSS classes to field names (shared by both sites)
- `ICON_COLOR_MAP`: Maps impact icon CSS classes to color strings

### Output Files
- Forex: `news/{Month}_{Year}_news.csv`
- Energy: `news/{Month}_{Year}_energy_news.csv`

### Convex Integration

The Convex backend requires these mutations in `convex/economicEvents.ts`:
- `economicEvents:saveEconomicEvent` - Save individual event records (includes `source` field)
- `economicEvents:saveScrapeSession` - Save batch metadata
- `economicEvents:deleteEventsByMonth` - Clear existing events by month/year/source
- `economicEvents:ping` - Connection test query

### Debugging Tips
- Check `/logs` endpoint for recent activity
- Browser timezone is auto-detected via `Intl.DateTimeFormat().resolvedOptions().timeZone`
- Set `headless=False` in `init_driver()` to see browser during scraping
- Use `--source forex` or `--source energy` CLI flags to test individual calendars
