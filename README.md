# Economic Calendar Scraper

Scrapes economic news events from [Forex Factory](https://www.forexfactory.com/calendar) and [Energy Exchange](https://www.energyexch.com/calendar) using Selenium. Supports filtering by currency, commodity, and impact level, with storage to CSV and/or PostgreSQL.

Forked from [fizahkhalid/forex_factory_calendar_news_scraper](https://github.com/fizahkhalid/forex_factory_calendar_news_scraper).

## Features

- Scrapes both Forex Factory and Energy Exchange calendars
- Flask API for triggering scrapes and querying stored events
- CLI for scripting and cron jobs
- Configurable currency, commodity, and impact filters
- Automatic timezone conversion
- Storage: CSV files and/or PostgreSQL database
- Local PostgreSQL via Docker Compose
- Docker support with health checks

## Quick Start

```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Start local PostgreSQL on localhost:55432
docker compose up -d postgres

# Run API
python3 app.py
```

### Web API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/status` | GET | Current scraping status |
| `/logs` | GET | Recent activity logs |
| `/postgres/test` | GET | Test PostgreSQL connection and initialize schema |
| `/events` | GET | Query stored PostgreSQL events with filters and pagination |
| `/events/<id>` | GET | Get one event by database id |
| `/events/summary` | GET | Get grouped event counts |
| `/scrape` | GET/POST | Scrape current month (both calendars) |
| `/scrape/<month>` | GET/POST | Scrape specific month (both calendars) |

The `month` parameter accepts: `this`, `next`, or a month name (`january`, `february`, etc.).

Example consumer queries:

```bash
curl "http://localhost:5000/events?source=forex_factory&month=July&year=2026"
curl "http://localhost:5000/events?source=energy_exch&impact=red&limit=100"
curl "http://localhost:5000/events?q=CPI&date_from=01/07/2026&date_to=31/07/2026"
```

See [API_GUIDE.md](API_GUIDE.md) for all filters and production usage notes.

### CLI

```bash
python3 scraper.py                              # Current month, both calendars
python3 scraper.py --months this next january   # Multiple months
python3 scraper.py --source forex               # Forex Factory only
python3 scraper.py --source energy              # Energy Exchange only
```

### Docker

```bash
# Database only for local development
docker compose up -d postgres

# Scraper API image
docker build -t economic-calendar-scraper .
docker run -p 5000:5000 --env-file .env economic-calendar-scraper
```

## Configuration

All configuration is via environment variables (`.env` file). See [.env.example](.env.example) for defaults.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://scraper:scraper_password@localhost:55432/economic_calendar` | PostgreSQL connection URL |
| `DATA_STORAGE` | `csv,postgres` | Storage method: `csv`, `postgres`, or comma-separated |
| `TARGET_TIMEZONE` | `US/Eastern` | Output timezone for event times |
| `ALLOWED_CURRENCY_CODES` | `USD` | Comma-separated forex currency filter |
| `ALLOWED_ENERGY_CODES` | `OIL,NG,BRENT,WTI,NATGAS,CL,CRUDE` | Comma-separated energy commodity filter |
| `ALLOWED_IMPACT_COLORS` | `red,gray` | Impact levels to include: `red`, `orange`, `yellow`, `gray` |

## Output

CSV files are saved to the `news/` directory:
- Forex: `news/{Month}_{Year}_news.csv`
- Energy: `news/{Month}_{Year}_energy_news.csv`

PostgreSQL stores events in `economic_events` and scrape metadata in `scrape_sessions`.

Each event includes: date, time, day, currency, impact, event name, detail URL, actual/forecast/previous values, and `source` (`forex_factory` or `energy_exch`).

## How It Works

1. Selenium launches a headless Chrome browser
2. Navigates to the calendar page for the requested month
3. Scrolls to load all events (infinite scroll, ~30-60s per calendar)
4. Parses the calendar table using CSS class mappings
5. Filters events by currency/commodity and impact level
6. Converts event times from the browser's timezone to the target timezone
7. Saves results to CSV and/or PostgreSQL

## Requirements

- Python 3.9+
- Google Chrome (installed automatically in Docker)
- ChromeDriver (auto-managed via `webdriver_manager`)
- PostgreSQL, or the included Docker Compose service

## License

MIT — see [LICENSE](LICENSE).
