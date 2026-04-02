# Economic Calendar Scraper

Scrapes economic news events from [Forex Factory](https://www.forexfactory.com/calendar) and [Energy Exchange](https://www.energyexch.com/calendar) using Selenium. Supports filtering by currency, commodity, and impact level, with optional storage to CSV and/or [Convex](https://convex.dev) database.

Forked from [fizahkhalid/forex_factory_calendar_news_scraper](https://github.com/fizahkhalid/forex_factory_calendar_news_scraper).

## Features

- Scrapes both Forex Factory and Energy Exchange calendars
- Flask API for triggering scrapes via HTTP
- CLI for scripting and cron jobs
- Configurable currency, commodity, and impact filters
- Automatic timezone conversion
- Dual storage: CSV files and/or Convex database
- Docker support with health checks

## Quick Start

```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your preferences
```

### Web API

```bash
python3 app.py
```

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/status` | GET | Current scraping status |
| `/logs` | GET | Recent activity logs |
| `/convex/test` | GET | Test Convex database connection |
| `/scrape` | GET/POST | Scrape current month (both calendars) |
| `/scrape/<month>` | GET/POST | Scrape specific month (both calendars) |

The `month` parameter accepts: `this`, `next`, or a month name (`january`, `february`, etc.).

### CLI

```bash
python3 scraper.py                              # Current month, both calendars
python3 scraper.py --months this next january   # Multiple months
python3 scraper.py --source forex               # Forex Factory only
python3 scraper.py --source energy              # Energy Exchange only
```

### Docker

```bash
docker build -t economic-calendar-scraper .
docker run -p 5000:5000 --env-file .env economic-calendar-scraper
```

## Configuration

All configuration is via environment variables (`.env` file). See [.env.example](.env.example) for defaults.

| Variable | Default | Description |
|---|---|---|
| `CONVEX_URL` | — | Convex deployment URL (optional) |
| `DATA_STORAGE` | `both` | Storage method: `csv`, `convex`, or `both` |
| `TARGET_TIMEZONE` | `US/Eastern` | Output timezone for event times |
| `ALLOWED_CURRENCY_CODES` | `USD` | Comma-separated forex currency filter |
| `ALLOWED_ENERGY_CODES` | `OIL,NG,BRENT,WTI,NATGAS,CL,CRUDE` | Comma-separated energy commodity filter |
| `ALLOWED_IMPACT_COLORS` | `red,gray` | Impact levels to include: `red`, `orange`, `yellow`, `gray` |

## Output

CSV files are saved to the `news/` directory:
- Forex: `news/{Month}_{Year}_news.csv`
- Energy: `news/{Month}_{Year}_energy_news.csv`

Each row includes: date, time, day, currency, impact, event name, detail URL, actual/forecast/previous values, and source.

## Convex Integration

To use Convex as a backend, set `CONVEX_URL` in your `.env` and ensure your Convex deployment has these mutations in `convex/economicEvents.ts`:

- `economicEvents:saveEconomicEvent` — Save individual event records
- `economicEvents:saveScrapeSession` — Save scrape batch metadata
- `economicEvents:deleteEventsByMonth` — Delete events by month/year/source
- `economicEvents:ping` — Connection test query

## How It Works

1. Selenium launches a headless Chrome browser
2. Navigates to the calendar page for the requested month
3. Scrolls to load all events (infinite scroll, ~30-60s per calendar)
4. Parses the calendar table using CSS class mappings
5. Filters events by currency/commodity and impact level
6. Converts event times from the browser's timezone to the target timezone
7. Saves results to CSV and/or Convex

## Requirements

- Python 3.9+
- Google Chrome (installed automatically in Docker)
- ChromeDriver (auto-managed via `webdriver_manager`)

## License

MIT — see [LICENSE](LICENSE).
