CREATE TABLE IF NOT EXISTS economic_events (
    id BIGSERIAL PRIMARY KEY,
    scraped_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    month TEXT NOT NULL,
    year INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL DEFAULT '',
    day TEXT NOT NULL DEFAULT '',
    currency TEXT NOT NULL DEFAULT '',
    impact TEXT NOT NULL DEFAULT '',
    event TEXT NOT NULL,
    actual TEXT NOT NULL DEFAULT '',
    forecast TEXT NOT NULL DEFAULT '',
    previous TEXT NOT NULL DEFAULT '',
    detail_url TEXT NOT NULL DEFAULT '',
    event_key TEXT NOT NULL,
    is_high_impact BOOLEAN NOT NULL DEFAULT FALSE,
    has_data BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, month, year, event_key)
);

CREATE INDEX IF NOT EXISTS idx_economic_events_source_month_year
    ON economic_events (source, month, year);
CREATE INDEX IF NOT EXISTS idx_economic_events_impact
    ON economic_events (impact);
CREATE INDEX IF NOT EXISTS idx_economic_events_currency
    ON economic_events (currency);

CREATE TABLE IF NOT EXISTS scrape_sessions (
    id BIGSERIAL PRIMARY KEY,
    scraped_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    month TEXT NOT NULL,
    year INTEGER NOT NULL,
    total_events INTEGER NOT NULL DEFAULT 0,
    saved_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
