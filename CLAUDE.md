# CLAUDE.md

## Commands

```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Run web API
python3 app.py

# Run CLI
python3 scraper.py                              # Current month, both calendars
python3 scraper.py --months this next january   # Multiple months
python3 scraper.py --source forex               # Forex Factory only
python3 scraper.py --source energy              # Energy Exchange only

# Docker
docker build -t economic-calendar-scraper .
docker run -p 5000:5000 --env-file .env economic-calendar-scraper

# Environment setup
cp .env.example .env
```

## Architecture

Selenium-based scraper for economic calendar events from Forex Factory and Energy Exchange. Both sites share the same HTML table structure (`calendar__table` with `calendar__cell` classes).

### Files

| File | Purpose |
|---|---|
| `app.py` | Flask API server. Runs scrapes in background threads. Endpoints: `/health`, `/status`, `/logs`, `/convex/test`, `/scrape`, `/scrape/<month>` |
| `scraper.py` | Core scraping logic. `init_driver()` creates headless Chrome, `scroll_to_end()` handles infinite scroll, `parse_table()` extracts rows using CSS class mappings, `scrape_all_calendars()` orchestrates both sources |
| `utils.py` | `reformat_data()` structures raw rows, `filter_row()` applies currency/impact filters, `convert_time_zone()` handles timezone conversion, `save_data()` dispatches to CSV/Convex, `save_csv()` writes CSV files |
| `config.py` | `ALLOWED_ELEMENT_TYPES` maps CSS classes to field names, `ICON_COLOR_MAP` maps impact icon classes to colors (both `ff-` and `ee-` prefixes), static filter defaults |
| `convex_client.py` | `save_to_convex()` transforms and saves records, `delete_events_by_month()` clears by month/year/source, `test_convex_connection()` pings backend |
| `simple_scrape.py` | Minimal standalone scraper from the original fork. Not used by the main application |

### Data Flow

1. API request or CLI invocation triggers scraping
2. `init_driver()` creates headless Chrome with anti-detection options
3. Browser navigates to calendar URL with `?month=` parameter
4. `scroll_to_end()` scrolls in 500px increments until position stops changing
5. `parse_table()` iterates `<tr>` rows in `calendar__table`, maps `<td>` classes via `ALLOWED_ELEMENT_TYPES`, resolves impact colors via `ICON_COLOR_MAP`, adds `source` field to each row
6. `reformat_data()` fills in date/time from previous rows (calendar uses row spanning), applies `filter_row()` for currency and impact filtering
7. `convert_time_zone()` converts times from browser timezone to `TARGET_TIMEZONE`, skipping non-standard formats ("All Day", "Day 1", "Sep Data", date ranges)
8. `save_data()` writes to CSV and/or Convex based on `DATA_STORAGE` env var

### Source Constants

- `SOURCE_FOREX = "forex_factory"` and `SOURCE_ENERGY = "energy_exch"` in `scraper.py`
- Used throughout for source-specific filtering, filenames, and Convex records

### Key Behaviors

- Scraping takes 30-60 seconds per calendar due to infinite scroll + page load delays
- API runs scrapes in background threads with mutex (one scrape at a time)
- Browser timezone is auto-detected via JS `Intl.DateTimeFormat()` on first page load
- Energy Exchange events skip currency filtering (commodities are embedded in event names)
- `parse_table()` also calls `save_csv()` directly (in addition to the API's `save_data()` call)

### Environment Variables

See `.env.example` for all options. Key ones: `CONVEX_URL`, `DATA_STORAGE` (csv/convex/both), `TARGET_TIMEZONE`, `ALLOWED_CURRENCY_CODES`, `ALLOWED_ENERGY_CODES`, `ALLOWED_IMPACT_COLORS`.

### Debugging

- `/logs` endpoint shows last 20 activity entries
- `/convex/test` tests database connectivity
- Set `headless=False` in `init_driver()` to watch the browser
- `--source forex` or `--source energy` CLI flags to test one calendar at a time
