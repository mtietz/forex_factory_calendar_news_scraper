"""
Convex Database Client for Forex Factory Scraper

This module handles all interactions with the Convex database.
It transforms scraped data and saves it to your Convex backend.
"""

import os
from typing import List, Dict, Any
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Only import convex if we have the URL configured
CONVEX_URL = os.getenv('CONVEX_URL')

if CONVEX_URL:
    try:
        import convex
        # Initialize Convex client
        client = convex.ConvexClient(CONVEX_URL)
        logger = logging.getLogger(__name__)
        logger.info(f"✅ Convex client initialized: {CONVEX_URL}")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Failed to initialize Convex client: {e}")
        client = None
else:
    client = None
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ No CONVEX_URL found in environment variables")


def is_convex_available() -> bool:
    """Check if Convex client is properly configured and available"""
    return client is not None


def transform_scraped_data(raw_data: List[Dict], month: str, year: str) -> List[Dict]:
    """
    Transform scraped data into the format expected by Convex.

    This function takes the raw scraped data and converts it into a clean format
    that's suitable for storing in your Convex database.

    Args:
        raw_data: List of dictionaries from the scraper
        month: Month name (e.g., "September")
        year: Year string (e.g., "2024")

    Returns:
        List of cleaned data records ready for Convex
    """

    transformed_records = []

    for record in raw_data:
        # Create a clean record with consistent field names
        clean_record = {
            # Metadata
            "scraped_at": datetime.now().isoformat(),
            "source": "forex_factory",
            "month": month,
            "year": int(year),

            # Event details (from your scraper)
            "date": record.get("date", ""),
            "time": record.get("time", ""),
            "day": record.get("day", ""),
            "currency": record.get("currency", ""),
            "impact": record.get("impact", ""),
            "event": record.get("event", ""),
            "actual": record.get("actual", ""),
            "forecast": record.get("forecast", ""),
            "previous": record.get("previous", ""),
            "detail_url": record.get("detail", ""),

            # Additional computed fields
            "event_key": f"{record.get('date', '')}-{record.get('time', '')}-{record.get('event', '')}",
            "is_high_impact": record.get("impact", "").lower() == "red",
            "has_data": bool(record.get("actual") or record.get("forecast") or record.get("previous"))
        }

        # Only include records that have meaningful content
        if clean_record["event"] and clean_record["date"]:
            transformed_records.append(clean_record)

    return transformed_records


def save_to_convex(data: List[Dict], month: str, year: str, replace_existing: bool = False) -> Dict[str, Any]:
    """
    Save scraped data to Convex database.

    Args:
        data: List of scraped data records
        month: Month name
        year: Year string
        replace_existing: If True, delete existing events for this month/year before saving

    Returns:
        Dictionary with operation results
    """

    if not is_convex_available():
        return {
            "success": False,
            "error": "Convex client not available. Check CONVEX_URL environment variable.",
            "saved_count": 0
        }

    try:
        # Delete existing events if requested
        if replace_existing:
            delete_result = delete_events_by_month(month, year)
            logger.info(f"Deleted {delete_result.get('deleted_count', 0)} existing events before saving new data")

        # Transform data to clean format
        clean_data = transform_scraped_data(data, month, year)

        if not clean_data:
            return {
                "success": False,
                "error": "No valid data to save after transformation",
                "saved_count": 0
            }

        # Save each record to Convex
        # Note: You'll need to create the corresponding mutation in your Convex backend
        saved_count = 0

        for i, record in enumerate(clean_data):
            try:
                # This calls a Convex mutation function - now in economicEvents.ts
                result = client.mutation("economicEvents:saveEconomicEvent", record)
                saved_count += 1
                logger.info(f"Saved record {i+1}/{len(clean_data)}: {record.get('event', 'Unknown event')}")

            except Exception as record_error:
                logger.error(f"Failed to save record {i+1}/{len(clean_data)}: {record.get('event', 'Unknown')}")
                logger.error(f"Record error details: {record_error}")
                logger.error(f"Problematic record: {record}")
                # Continue with other records even if one fails
                continue

        # Save batch metadata
        batch_info = {
            "month": month,
            "year": int(year),
            "total_events": len(clean_data),
            "scraped_at": datetime.now().isoformat(),
            "source": "forex_factory_scraper"
        }

        try:
            # Save batch information
            client.mutation("economicEvents:saveScrapeSession", batch_info)
        except Exception as batch_error:
            logger.error(f"Failed to save batch info: {batch_error}")

        return {
            "success": True,
            "saved_count": saved_count,
            "total_processed": len(clean_data),
            "month": month,
            "year": year
        }

    except Exception as e:
        logger.error(f"Failed to save to Convex: {e}")
        return {
            "success": False,
            "error": str(e),
            "saved_count": 0
        }


def delete_events_by_month(month: str, year: str) -> Dict[str, Any]:
    """
    Delete all events for a specific month and year from Convex.
    This ensures that when we re-scrape, removed events are also deleted.

    Args:
        month: Month name (e.g., "September")
        year: Year string (e.g., "2024")

    Returns:
        Dictionary with deletion results
    """

    if not is_convex_available():
        return {
            "success": False,
            "error": "Convex client not available. Check CONVEX_URL environment variable.",
            "deleted_count": 0
        }

    try:
        # Call Convex mutation to delete events for this month/year
        result = client.mutation("economicEvents:deleteEventsByMonth", {
            "month": month,
            "year": int(year)
        })

        logger.info(f"✅ Deleted events for {month} {year}: {result.get('deleted_count', 0)} events removed")

        return {
            "success": True,
            "deleted_count": result.get("deleted_count", 0),
            "month": month,
            "year": year
        }

    except Exception as e:
        logger.error(f"❌ Failed to delete events for {month} {year}: {e}")
        return {
            "success": False,
            "error": str(e),
            "deleted_count": 0
        }


def test_convex_connection() -> Dict[str, Any]:
    """
    Test the Convex connection and return status information.
    Useful for debugging and health checks.
    """

    if not is_convex_available():
        return {
            "connected": False,
            "error": "Convex client not configured",
            "url": CONVEX_URL or "Not set"
        }

    try:
        # Try a simple query to test connection
        test_result = client.query("economicEvents:ping", {})

        return {
            "connected": True,
            "url": CONVEX_URL,
            "test_result": test_result
        }

    except Exception as e:
        return {
            "connected": False,
            "url": CONVEX_URL,
            "error": str(e)
        }


# Example of what your Convex mutations should look like:
"""
// convex/mutations.ts - You'll need to create these in your Convex backend

import { mutation } from "./_generated/server";
import { v } from "convex/values";

export const saveForexEvent = mutation({
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
    return await ctx.db.insert("forex_events", args);
  },
});

export const saveScrapeSession = mutation({
  args: {
    month: v.string(),
    year: v.number(),
    total_events: v.number(),
    scraped_at: v.string(),
    source: v.string(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("scrape_sessions", args);
  },
});
"""