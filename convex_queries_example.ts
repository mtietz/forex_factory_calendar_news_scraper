// This file shows what you need to add to your Convex backend
// Copy this content to your Convex project's convex/queries.ts file

import { query } from "./_generated/server";
import { v } from "convex/values";

// Simple ping query for connection testing
export const ping = query({
  args: {},
  handler: async () => {
    return { status: "ok", timestamp: new Date().toISOString() };
  },
});

// Get economic events by month/year
export const getEconomicEvents = query({
  args: {
    month: v.string(),
    year: v.number(),
  },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("economic_events")
      .withIndex("by_month_year", (q) =>
        q.eq("month", args.month).eq("year", args.year)
      )
      .collect();
  },
});

// Get recent scrape sessions
export const getRecentSessions = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db
      .query("scrape_sessions")
      .withIndex("by_scraped_at")
      .order("desc")
      .take(10);
  },
});

// Get high-impact events only
export const getHighImpactEvents = query({
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

    return events.filter((event) => event.is_high_impact);
  },
});