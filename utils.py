import os
import re
import json
import pytz
import pandas as pd
from datetime import datetime
import config
from urllib.request import urlopen


def read_json(path):
    """
    Read JSON data from a file.
    Args: path (str): The path to the JSON file.
    Returns: dict: The loaded JSON data.
    """
    with open(path, 'r') as f:
        data = json.load(f)
    return data


def extract_date_parts(text, year):
    # Full pattern: Day (e.g., Sun), Month (e.g., Jun), Day number (e.g., 1 or 01)
    pattern = r'\b(?P<day>Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b\s+' \
              r'(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\s+' \
              r'(?P<date>\d{1,2})\b'

    match = re.search(pattern, text)
    if match:
        month_abbr = match.group("month")
        day = int(match.group("date"))

        # Convert month abbreviation to month number
        month_number = datetime.strptime(month_abbr, "%b").month

        # Format date as dd/mm/yyyy
        formatted_date = f"{day:02d}/{month_number:02d}/{year}"

        return {
            "day": match.group("day"),
            "date": formatted_date
        }
    else:
        return None


def reformat_data(data: list, year: str) -> list:
    current_date = ''
    current_time = ''
    current_day = ''
    structured_rows = []

    for row in data:
        new_row = row.copy()

        if "date" in new_row and new_row['date'] != "empty":
            date_parts = extract_date_parts(new_row["date"], year)
            if date_parts:
                current_date = date_parts["date"]
                current_day = date_parts["day"]

        if "time" in new_row:
            if new_row["time"]!="empty":
                current_time = new_row["time"].strip()
            else:
                new_row["time"] = current_time

        if len(row) == 1:
            continue

        new_row["day"] = current_day
        new_row["date"] = current_date

        scraper_timezone = "Europe/Berlin"
        if scraper_timezone and config.TARGET_TIMEZONE:
            new_row["time"] = convert_time_zone(current_date, current_time, scraper_timezone, config.TARGET_TIMEZONE)
        else:
            new_row["time"] = current_time

        new_row["currency"] = row.get("currency", "")
        new_row["impact"] = row.get("impact", "")
        new_row["event"] = row.get("event", "")
        new_row["detail"] = row.get("detail", "")
        new_row["actual"] = row.get("actual", "")
        new_row["forecast"] = row.get("forecast", "")
        new_row["previous"] = row.get("previous", "")
        new_row["source"] = row.get("source", "forex_factory")

        # Replace "empty" with ""
        for key, value in new_row.items():
            if value == "empty":
                new_row[key] = ""

        row = filter_row(new_row)
        if row:
            structured_rows.append(new_row)

    return structured_rows


def filter_row(row):
    """
    Filter row based on source-specific currency codes and impact colors.
    """
    source = row.get('source', 'forex_factory')

    # Must have an event name
    if not row.get('event') or row.get('event') == 'empty':
        return False

    # Use source-specific currency filter
    if source == 'energy_exch':
        # Energy Exchange doesn't have a separate currency column
        # The currency/country code is embedded in the event name (e.g., "US ISM Manufacturing")
        # Skip currency filtering for energy
        pass
    else:
        # Forex Factory has explicit currency column
        if row['currency'] not in config.ALLOWED_CURRENCY_CODES:
            return False

    # Impact filter applies to both calendars
    impact = row.get('impact', '')
    if impact and impact != 'empty' and impact.lower() not in config.ALLOWED_IMPACT_COLORS:
        return False

    return row

def save_csv(data, month, year, source="forex_factory"):
    """
    Save data to CSV file.

    Args:
        data: Raw scraped data
        month: Month name
        year: Year string
        source: Calendar source (forex_factory or energy_exch)

    Returns:
        True if successful, False otherwise
    """
    structured_rows = reformat_data(data, year)
    if not structured_rows:
        return False

    header = list(structured_rows[0].keys())
    df = pd.DataFrame(structured_rows, columns=header)
    os.makedirs("news", exist_ok=True)

    # Use source-specific filename
    if source == "energy_exch":
        filename = f"news/{month}_{year}_energy_news.csv"
    else:
        filename = f"news/{month}_{year}_news.csv"

    df.to_csv(filename, index=False)
    return True


def _storage_enabled(storage_method, target):
    """Check whether a storage backend is enabled.

    Supports single values and comma-separated values, e.g.
    DATA_STORAGE=postgres or DATA_STORAGE=csv,postgres.
    """
    methods = {method.strip().lower() for method in str(storage_method).split(",") if method.strip()}

    aliases = {
        "postgresql": "postgres",
        "pg": "postgres",
        "db": "postgres",
        "both": "csv,postgres",
        "all": "csv,postgres",
    }

    expanded_methods = set()
    for method in methods:
        expanded = aliases.get(method, method)
        expanded_methods.update(part.strip() for part in expanded.split(",") if part.strip())

    return target in expanded_methods


def save_data(data, month, year, storage_method="both", replace_existing=False, source="forex_factory"):
    """
    Enhanced save function that supports multiple storage methods.

    Args:
        data: Raw scraped data
        month: Month name
        year: Year string
        storage_method: "csv", "postgres", or comma-separated (e.g. "csv,postgres")
        replace_existing: If True, delete existing events before saving (PostgreSQL only)
        source: Calendar source (forex_factory or energy_exch)

    Returns:
        Dictionary with results from each storage method
    """
    results = {
        "csv": {"attempted": False, "success": False, "error": None},
        "postgres": {"attempted": False, "success": False, "error": None, "saved_count": 0}
    }

    # Save to CSV if requested
    if _storage_enabled(storage_method, "csv"):
        results["csv"]["attempted"] = True
        try:
            results["csv"]["success"] = save_csv(data, month, year, source)
        except Exception as e:
            results["csv"]["error"] = str(e)

    # Save to PostgreSQL if requested
    if _storage_enabled(storage_method, "postgres"):
        results["postgres"]["attempted"] = True
        try:
            from postgres_client import save_to_postgres

            structured_rows = reformat_data(data, year)
            postgres_result = save_to_postgres(structured_rows, month, year, replace_existing=replace_existing, source=source)

            results["postgres"]["success"] = postgres_result.get("success", False)
            results["postgres"]["saved_count"] = postgres_result.get("saved_count", 0)

            if not postgres_result.get("success", False):
                results["postgres"]["error"] = postgres_result.get("error", "Unknown error")

        except ImportError:
            results["postgres"]["error"] = "PostgreSQL client dependencies not available"
        except Exception as e:
            results["postgres"]["error"] = str(e)

    return results


def is_non_standard_time(time_str):
    """
    Check if time_str is a non-standard time format that shouldn't be converted.

    These include:
    - "All Day", "Tentative" - standard non-time markers
    - "Day 1", "Day 2", etc. - multi-day event markers (e.g., WEF meetings)
    - "Sep Data", "Oct Data", etc. - data period labels
    - "12th-15th", "1st-3rd", etc. - date ranges
    """
    time_lower = time_str.lower().strip()

    # Standard non-time markers
    if time_lower in ["all day", "tentative"]:
        return True

    # Multi-day event markers: "Day 1", "Day 2", etc.
    if re.match(r'^day\s+\d+$', time_lower):
        return True

    # Data period labels: "Sep Data", "Oct Data", "November Data", etc.
    if re.match(r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s+data$', time_lower):
        return True

    # Date ranges: "12th-15th", "1st-3rd", "2nd-5th", etc.
    if re.match(r'^\d{1,2}(st|nd|rd|th)[-–]\d{1,2}(st|nd|rd|th)$', time_lower):
        return True

    return False


def convert_time_zone(date_str, time_str, from_zone_str, to_zone_str):
    """
    Convert time from one timezone to another.
    - date_str: '01/07/2025'
    - time_str: '3:00am'
    """
    if not time_str or not date_str:
        return time_str

    if is_non_standard_time(time_str):
        return time_str

    try:
        from_zone = pytz.timezone(from_zone_str)
        to_zone = pytz.timezone(to_zone_str)

        naive_dt = datetime.strptime(
            f"{date_str} {time_str}", "%d/%m/%Y %I:%M%p")
        localized_dt = from_zone.localize(naive_dt)
        converted_dt = localized_dt.astimezone(to_zone)

        return converted_dt.strftime("%H:%M")
    except Exception as e:
        print(f"[WARN] Failed to convert '{time_str}' on {date_str}: {e}")
        return time_str

