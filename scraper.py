import time
import argparse
from datetime import datetime
from config import ALLOWED_ELEMENT_TYPES, ICON_COLOR_MAP, FOREX_FACTORY_URL, ENERGY_EXCH_URL
from utils import save_csv
import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Calendar source constants
SOURCE_FOREX = "forex_factory"
SOURCE_ENERGY = "energy_exch"


def init_driver(headless=True) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920x1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    print("Attempting to initialize WebDriver with ChromeDriverManager...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    print("WebDriver initialized successfully using ChromeDriverManager.")
    return driver


def scroll_to_end(driver):
    previous_position = None
    while True:
        current_position = driver.execute_script("return window.pageYOffset;")
        driver.execute_script("window.scrollTo(0, window.pageYOffset + 500);")
        time.sleep(2)
        if current_position == previous_position:
            break
        previous_position = current_position


def parse_table(driver, month, year, source=SOURCE_FOREX):
    """
    Parse calendar table from either Forex Factory or Energy Exchange.

    Args:
        driver: Selenium WebDriver instance
        month: Month name
        year: Year string
        source: Calendar source (SOURCE_FOREX or SOURCE_ENERGY)

    Returns:
        Tuple of (data list, month string)
    """
    data = []
    table = driver.find_element(By.CLASS_NAME, "calendar__table")

    # Determine base URL for detail links
    if source == SOURCE_ENERGY:
        base_url = ENERGY_EXCH_URL
    else:
        base_url = FOREX_FACTORY_URL

    for row in table.find_elements(By.TAG_NAME, "tr"):
        row_data = {"source": source}  # Add source to each row
        event_id = row.get_attribute("data-event-id")

        for element in row.find_elements(By.TAG_NAME, "td"):
            class_name = element.get_attribute('class')

            if class_name in ALLOWED_ELEMENT_TYPES:
                class_name_key = ALLOWED_ELEMENT_TYPES.get(
                    f"{class_name}", "cell")

                if "calendar__impact" in class_name:
                    impact_elements = element.find_elements(
                        By.TAG_NAME, "span")
                    color = None
                    for impact in impact_elements:
                        impact_class = impact.get_attribute("class")
                        color = ICON_COLOR_MAP.get(impact_class)
                    row_data[f"{class_name_key}"] = color if color else "impact"

                elif "calendar__detail" in class_name and event_id:
                    detail_url = f"{base_url}?month={month}#detail={event_id}"
                    row_data[f"{class_name_key}"] = detail_url

                elif element.text:
                    row_data[f"{class_name_key}"] = element.text
                else:
                    row_data[f"{class_name_key}"] = "empty"

        if row_data and len(row_data) > 1:  # More than just 'source' field
            data.append(row_data)

    save_csv(data, month, year, source)

    return data, month


def get_target_month(arg_month=None):
    now = datetime.now()
    month = arg_month if arg_month else now.strftime("%B")
    year = now.strftime("%Y")
    return month, year


def get_month_year_from_param(param):
    """Convert month parameter to month name and year."""
    if param == "this":
        now = datetime.now()
        month = now.strftime("%B")
        year = now.year
    elif param == "next":
        now = datetime.now()
        next_month = (now.month % 12) + 1
        year = now.year if now.month < 12 else now.year + 1
        month = datetime(year, next_month, 1).strftime("%B")
    else:
        month = param.capitalize()
        year = datetime.now().year
    return month, year


def scrape_single_source(driver, url, month, year, source):
    """
    Scrape a single calendar source.

    Args:
        driver: Selenium WebDriver instance
        url: Calendar URL
        month: Month name
        year: Year
        source: Source identifier (SOURCE_FOREX or SOURCE_ENERGY)

    Returns:
        List of scraped data or empty list on error
    """
    print(f"\n[INFO] Scraping {source}: {url}")
    try:
        driver.get(url)

        # Wait for page to fully load
        print(f"[INFO] Waiting for page to load...")
        time.sleep(10)

        # Verify table exists before scrolling
        tables = driver.find_elements(By.CLASS_NAME, "calendar__table")
        if not tables:
            print(f"[WARN] Calendar table not found, waiting longer...")
            time.sleep(10)

        scroll_to_end(driver)
        data, _ = parse_table(driver, month, str(year), source)
        print(f"[INFO] Scraped {len(data)} events from {source}")
        return data
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to scrape {source}: {e}")
        traceback.print_exc()
        return []


def scrape_all_calendars(driver, month_param):
    """
    Scrape both Forex Factory and Energy Exchange calendars.

    Args:
        driver: Selenium WebDriver instance
        month_param: Month parameter (this, next, or month name)

    Returns:
        Tuple of (combined_data, month, year)
    """
    month, year = get_month_year_from_param(month_param)
    all_data = []

    # Scrape Forex Factory
    forex_url = f"{FOREX_FACTORY_URL}?month={month_param}"
    forex_data = scrape_single_source(driver, forex_url, month, year, SOURCE_FOREX)
    all_data.extend(forex_data)

    # Scrape Energy Exchange
    energy_url = f"{ENERGY_EXCH_URL}?month={month_param}"
    energy_data = scrape_single_source(driver, energy_url, month, year, SOURCE_ENERGY)
    all_data.extend(energy_data)

    print(f"\n[INFO] Total events scraped: {len(all_data)} (Forex: {len(forex_data)}, Energy: {len(energy_data)})")
    return all_data, month, year


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Forex Factory and Energy Exchange calendars.")
    parser.add_argument("--months", nargs="+",
                        help='Target months: e.g., this next january')
    parser.add_argument("--source", choices=["forex", "energy", "all"], default="all",
                        help='Calendar source to scrape (default: all)')

    args = parser.parse_args()
    month_params = args.months if args.months else ["this"]

    for param in month_params:
        param = param.lower()
        month, year = get_month_year_from_param(param)

        driver = init_driver()

        # Detect timezone from browser (doesn't require page load)
        detected_tz = driver.execute_script("return Intl.DateTimeFormat().resolvedOptions().timeZone")
        print(f"[INFO] Browser timezone: {detected_tz}")
        config.SCRAPER_TIMEZONE = detected_tz

        print(f"\n[INFO] Scraping data for {month} {year}")

        if args.source == "all":
            scrape_all_calendars(driver, param)
        elif args.source == "forex":
            url = f"{FOREX_FACTORY_URL}?month={param}"
            scrape_single_source(driver, url, month, year, SOURCE_FOREX)
        elif args.source == "energy":
            url = f"{ENERGY_EXCH_URL}?month={param}"
            scrape_single_source(driver, url, month, year, SOURCE_ENERGY)

        driver.quit()
        time.sleep(3)


if __name__ == "__main__":
    main()
