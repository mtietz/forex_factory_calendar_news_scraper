# Economic Calendar API Guide

This API exposes scraped Forex Factory and Energy Exchange calendar events from PostgreSQL so outside consumers can fetch the data with filters.

## Authentication

Production should set an API key:

```env
API_KEY=your-long-random-secret
```

When `API_KEY` is configured, every endpoint except `/health` requires one of these headers:

```http
X-API-Key: your-long-random-secret
```

or:

```http
Authorization: Bearer your-long-random-secret
```

Examples in this guide omit the header for readability. For production, include it:

```bash
curl -H "X-API-Key: $ECONOMIC_CALENDAR_API_KEY" \
  "https://ff-scraper.mtietz.cloud/events?limit=100"
```

## Base URL

Local development:

```text
http://localhost:5000
```

Production:

```text
https://your-domain.example
```

## Database / Migration Behavior

The app uses `DATABASE_URL` or `POSTGRES_URL` to connect to PostgreSQL.

On app/API usage, the initial migration is applied automatically from:

```text
migrations/001_init_postgres.sql
```

The migration runs through `init_schema()` when you:

- call `GET /postgres/test`
- call event read endpoints
- save scraped data after a scrape

So in Dokploy/prod, if `DATABASE_URL` is configured correctly, the tables are created automatically. You can verify with:

```bash
curl https://your-domain.example/postgres/test
```

## Endpoints

### Health

```http
GET /health
```

Returns service health.

### PostgreSQL test

```http
GET /postgres/test
```

Tests DB connectivity and initializes the schema if needed.

Example response:

```json
{
  "connected": true,
  "event_count": 78
}
```

### List events

```http
GET /events
```

Returns events with pagination metadata.

Example response shape:

```json
{
  "events": [],
  "count": 50,
  "total": 78,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

#### Query parameters

| Parameter | Description | Example |
|---|---|---|
| `source` | Calendar source. Supports comma-separated values. | `forex_factory`, `energy_exch` |
| `month` | Month name. Supports comma-separated values. | `July` |
| `year` | Year. Supports comma-separated values. | `2026` |
| `impact` | Impact color. Supports comma-separated values. | `red`, `gray` |
| `currency` | Currency code. Supports comma-separated values. | `USD` |
| `date` | Exact event date in `DD/MM/YYYY`. | `07/07/2026` |
| `day` | Weekday abbreviation. | `Mon`, `Tue` |
| `date_from` | Start date inclusive, `DD/MM/YYYY`. | `01/07/2026` |
| `date_to` | End date inclusive, `DD/MM/YYYY`. | `31/07/2026` |
| `event` | Case-insensitive event name search. | `CPI` |
| `q` | Alias for `event`. | `inventory` |
| `is_high_impact` | Boolean filter. | `true` |
| `has_data` | Boolean filter for actual/forecast/previous availability. | `true` |
| `order_by` | Sort order: `date`, `scraped_at`, `source`, `impact`, `event`. | `date` |
| `limit` | Page size, max `5000`. | `100` |
| `offset` | Pagination offset. | `100` |

#### Examples

Get latest stored events:

```bash
curl "http://localhost:5000/events?limit=100"
```

Get July 2026 Forex Factory events:

```bash
curl "http://localhost:5000/events?source=forex_factory&month=July&year=2026"
```

Get Energy Exchange high-impact events:

```bash
curl "http://localhost:5000/events?source=energy_exch&is_high_impact=true"
```

Get red-impact USD events:

```bash
curl "http://localhost:5000/events?currency=USD&impact=red"
```

Search by event name:

```bash
curl "http://localhost:5000/events?q=CPI"
```

Date range filter:

```bash
curl "http://localhost:5000/events?date_from=01/07/2026&date_to=31/07/2026"
```

Multiple values:

```bash
curl "http://localhost:5000/events?source=forex_factory,energy_exch&impact=red,gray"
```

Pagination:

```bash
curl "http://localhost:5000/events?limit=50&offset=0"
curl "http://localhost:5000/events?limit=50&offset=50"
```

### Get single event

```http
GET /events/{id}
```

Example:

```bash
curl "http://localhost:5000/events/1"
```

Response:

```json
{
  "event": {
    "id": 1,
    "source": "forex_factory",
    "month": "July",
    "year": 2026,
    "date": "07/07/2026",
    "time": "8:30am",
    "currency": "USD",
    "impact": "red",
    "event": "Example Event"
  }
}
```

### Event summary

```http
GET /events/summary
```

Returns counts grouped by source, impact, and month/year.

Example:

```bash
curl "http://localhost:5000/events/summary"
```

## Triggering Scrapes

Start current month scrape:

```http
GET /scrape
```

Start a specific month scrape:

```http
GET /scrape/july
```

Check status:

```http
GET /status
```

View logs:

```http
GET /logs
```

## Source Values

Events always include a `source` field so consumers can separate calendars:

| Source | Calendar |
|---|---|
| `forex_factory` | Forex Factory |
| `energy_exch` | Energy Exchange |

## Production Notes

For Dokploy or other deployments, configure:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB_NAME
DATA_STORAGE=postgres
```

Use `DATA_STORAGE=csv,postgres` if you also want CSV files written inside the container.

After deployment, run:

```bash
curl https://your-domain.example/postgres/test
```

That verifies the DB connection and applies the migration automatically.
