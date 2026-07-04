# External App Integration Guide

Use this guide to consume economic calendar events directly from the scraper API. The external app no longer needs to store a duplicate copy of events unless it wants its own cache.

## Recommended Architecture

```text
Scraper Dokploy cron
  POST /scrape
      ↓
Scraper PostgreSQL DB
      ↓
Scraper API
  GET /events
      ↓
External app reads events directly
```

The scraper service owns the economic calendar data. External apps should read from the scraper API with filters.

## Authentication

Production access is protected with an API key. Configure the same secret in the external app:

```env
ECONOMIC_CALENDAR_API_KEY=your-long-random-secret
```

Send it with every request, either as:

```http
X-API-Key: your-long-random-secret
```

or:

```http
Authorization: Bearer your-long-random-secret
```

## Base URL

Configure the scraper API URL in the external app environment:

```env
ECONOMIC_CALENDAR_API_URL=https://ff-scraper.mtietz.cloud
```

For local development:

```env
ECONOMIC_CALENDAR_API_URL=http://localhost:5000
```

## Main Endpoint

```http
GET /events
```

Returns events from the scraper PostgreSQL database.

Example:

```bash
curl -H "X-API-Key: $ECONOMIC_CALENDAR_API_KEY" \
  "$ECONOMIC_CALENDAR_API_URL/events?limit=100"
```

Response shape:

```json
{
  "events": [
    {
      "id": 1,
      "source": "forex_factory",
      "month": "July",
      "year": 2026,
      "date": "01/07/2026",
      "time": "08:15",
      "day": "Wed",
      "currency": "USD",
      "impact": "orange",
      "event": "ADP Non-Farm Employment Change",
      "actual": "98K",
      "forecast": "",
      "previous": "",
      "detail_url": "https://www.forexfactory.com/calendar?month=July#detail=150303",
      "event_key": "01/07/2026-08:15-ADP Non-Farm Employment Change",
      "is_high_impact": false,
      "has_data": true,
      "scraped_at": "2026-07-04T11:25:52.153667+00:00"
    }
  ],
  "count": 1,
  "total": 78,
  "limit": 100,
  "offset": 0,
  "has_more": false
}
```

## Filters

All filters are query parameters.

| Parameter | Description | Example |
|---|---|---|
| `source` | Calendar source. Supports comma-separated values. | `forex_factory`, `energy_exch` |
| `month` | Month name. Supports comma-separated values. | `July` |
| `year` | Year. Supports comma-separated values. | `2026` |
| `impact` | Impact color. Supports comma-separated values. | `red`, `orange`, `gray` |
| `currency` | Currency code. Supports comma-separated values. | `USD` |
| `date` | Exact event date, `DD/MM/YYYY`. | `01/07/2026` |
| `day` | Weekday abbreviation. | `Mon`, `Tue`, `Wed` |
| `date_from` | Start date inclusive, `DD/MM/YYYY`. | `01/07/2026` |
| `date_to` | End date inclusive, `DD/MM/YYYY`. | `31/07/2026` |
| `event` | Case-insensitive event name search. | `CPI` |
| `q` | Alias for `event`. | `inventory` |
| `is_high_impact` | Boolean filter. | `true` |
| `has_data` | Boolean filter for actual/forecast/previous data. | `true` |
| `order_by` | Sort order: `date`, `scraped_at`, `source`, `impact`, `event`. | `date` |
| `limit` | Page size, max `5000`. | `100` |
| `offset` | Pagination offset. | `100` |

## Source Values

Use `source` to separate the two calendars.

| Source | Meaning |
|---|---|
| `forex_factory` | Forex Factory calendar |
| `energy_exch` | Energy Exchange calendar |

## Common Requests

### Get all current stored events

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events?limit=5000"
```

### Get Forex Factory events for a month

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events?source=forex_factory&month=July&year=2026"
```

### Get Energy Exchange events

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events?source=energy_exch&month=July&year=2026"
```

### Get high-impact events only

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events?is_high_impact=true"
```

### Get red-impact USD events

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events?currency=USD&impact=red"
```

### Search by event name

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events?q=CPI"
```

### Get events in a date range

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events?date_from=01/07/2026&date_to=31/07/2026"
```

### Use multiple values

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events?source=forex_factory,energy_exch&impact=red,orange"
```

### Pagination

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events?limit=100&offset=0"
curl "$ECONOMIC_CALENDAR_API_URL/events?limit=100&offset=100"
```

Continue requesting pages while `has_more` is `true`.

## Single Event Endpoint

```http
GET /events/{id}
```

Example:

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events/1"
```

Response:

```json
{
  "event": {
    "id": 1,
    "source": "forex_factory",
    "event": "ADP Non-Farm Employment Change"
  }
}
```

## Summary Endpoint

```http
GET /events/summary
```

Returns grouped counts by source, impact, and month/year.

Example:

```bash
curl "$ECONOMIC_CALENDAR_API_URL/events/summary"
```

Example response:

```json
{
  "by_source": [
    { "source": "energy_exch", "count": 40 },
    { "source": "forex_factory", "count": 38 }
  ],
  "by_impact": [
    { "impact": "gray", "count": 1 },
    { "impact": "orange", "count": 31 },
    { "impact": "red", "count": 46 }
  ],
  "by_month": [
    { "month": "July", "year": 2026, "count": 78 }
  ]
}
```

## JavaScript/TypeScript Example

```ts
const API_URL = process.env.ECONOMIC_CALENDAR_API_URL;

export async function getEconomicEvents(params: Record<string, string | number | boolean>) {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  }

  const response = await fetch(`${API_URL}/events?${searchParams.toString()}`, {
    headers: {
      "X-API-Key": process.env.ECONOMIC_CALENDAR_API_KEY ?? "",
    },
  });

  if (!response.ok) {
    throw new Error(`Economic calendar API error: ${response.status}`);
  }

  return response.json();
}

// Example usage
const data = await getEconomicEvents({
  source: "forex_factory",
  impact: "red",
  month: "July",
  year: 2026,
  limit: 100,
});

console.log(data.events);
```

## Should the External App Store a Copy?

Usually, no. The external app can read directly from this API.

Store a copy only if the external app needs:

- offline availability when the scraper API is down
- heavy joins with app-specific tables
- user-specific annotations on events
- very high read traffic
- independent historical snapshots

Otherwise, use direct API reads.

## Refresh Schedule

The scraper service is refreshed by its own Dokploy cronjob:

```bash
curl -X POST http://localhost:5000/scrape
```

The external app does **not** need a cronjob if it reads directly from `/events`.

## Health / Availability

The external app can check scraper availability with:

```http
GET /health
```

Example:

```bash
curl "$ECONOMIC_CALENDAR_API_URL/health"
```

## Error Handling

Recommended external app behavior:

- If `/events` returns `200`, use the returned data.
- If it returns `5xx`, show cached/stale data if your app has any.
- If it returns `400`, check query parameters.
- Set reasonable request timeouts, e.g. 5–10 seconds.

## Notes

- Dates are currently strings in `DD/MM/YYYY` format.
- `source` is always included so consumers can separate calendars.
- `is_high_impact` is true when `impact` is `red`.
- `has_data` is true when one of `actual`, `forecast`, or `previous` is present.
