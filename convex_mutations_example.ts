// This file shows what you need to add to your Convex backend
// Copy this content to your Convex project's convex/mutations.ts file

import { mutation } from "./_generated/server";
import { v } from "convex/values";

// Mutation to save individual economic events
export const saveEconomicEvent = mutation({
  args: {
    scraped_at: v.string(),
    source: v.string(),
    month: v.string(),
    year: v.number(),
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
    event_key: v.string(),
    is_high_impact: v.boolean(),
    has_data: v.boolean(),
  },
  handler: async (ctx, args) => {
    // Check if this event already exists (prevent duplicates)
    const existing = await ctx.db
      .query("economic_events")
      .withIndex("by_event_key", (q) => q.eq("event_key", args.event_key))
      .first();

    if (existing) {
      // Update existing event with new data
      return await ctx.db.patch(existing._id, args);
    } else {
      // Insert new event
      return await ctx.db.insert("economic_events", args);
    }
  },
});

// Mutation to save scrape session metadata
export const saveScrapeSession = mutation({
  args: {
    month: v.string(),
    year: v.number(),
    total_events: v.number(),
    scraped_at: v.string(),
    source: v.string(),
  },
  handler: async (ctx, args) => {
    // Check if a session for this month/year already exists
    const existing = await ctx.db
      .query("scrape_sessions")
      .withIndex("by_month_year", (q) =>
        q.eq("month", args.month).eq("year", args.year)
      )
      .first();

    if (existing) {
      // Update existing session
      return await ctx.db.patch(existing._id, args);
    } else {
      // Create new session
      return await ctx.db.insert("scrape_sessions", args);
    }
  },
});

// Utility mutation to clear old data (optional - for cleanup)
export const clearOldEvents = mutation({
  args: {
    month: v.string(),
    year: v.number(),
  },
  handler: async (ctx, args) => {
    const events = await ctx.db
      .query("economic_events")
      .withIndex("by_month_year", (q) =>
        q.eq("month", args.month).eq("year", args.year)
      )
      .collect();

    for (const event of events) {
      await ctx.db.delete(event._id);
    }

    return { deleted_count: events.length };
  },
});