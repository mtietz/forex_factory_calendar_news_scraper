// This file shows what you need to add to your Convex backend
// Copy this content to your Convex project's convex/schema.ts file

import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // Table for individual economic events
  economic_events: defineTable({
    // Metadata
    scraped_at: v.string(),
    source: v.string(),
    month: v.string(),
    year: v.number(),

    // Event details
    date: v.string(),
    time: v.string(),
    day: v.string(),
    currency: v.string(),
    impact: v.string(),
    event: v.string(),
    actual: v.string(),
    forecast: v.string(),
    previous: v.string(),
    detail_url: v.string(),

    // Computed fields
    event_key: v.string(),
    is_high_impact: v.boolean(),
    has_data: v.boolean(),
  })
  .index("by_month_year", ["month", "year"])
  .index("by_date", ["date"])
  .index("by_currency", ["currency"])
  .index("by_impact", ["impact"])
  .index("by_event_key", ["event_key"]),

  // Table for tracking scrape sessions
  scrape_sessions: defineTable({
    month: v.string(),
    year: v.number(),
    total_events: v.number(),
    scraped_at: v.string(),
    source: v.string(),
  })
  .index("by_month_year", ["month", "year"])
  .index("by_scraped_at", ["scraped_at"]),
});