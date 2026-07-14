#!/usr/bin/env python3
"""
Store Rank Scanner - Tracks app positions across iOS and Android stores.
"""
import json
import logging
import re
import sys
import time
import urllib.parse
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from tqdm import tqdm


logger = logging.getLogger("aso_tracker")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

ALLOWED_PLATFORMS = {"play", "app"}


class ConfigError(ValueError):
    pass


class ScrapeError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def load_config():
    try:
        raw = json.loads(Path("settings.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError("settings.json not found")
    except json.JSONDecodeError as exc:
        raise ConfigError(f"settings.json is not valid JSON: {exc.msg} (line {exc.lineno})")

    if not isinstance(raw, list) or not raw:
        raise ConfigError("root must be a non-empty JSON array")

    normalized = []
    has_active_task = False
    for i, task in enumerate(raw, start=1):
        if not isinstance(task, dict):
            raise ConfigError(f"task #{i} must be an object")

        active = task.get("active", True)
        if not isinstance(active, bool):
            raise ConfigError(f"task #{i}: 'active' must be boolean")

        stores = normalize_platforms(task.get("platforms", ["play"]))
        if not isinstance(stores, list) or not stores:
            raise ConfigError(f"task #{i}: 'platforms' must be a non-empty string or array")
        if any(not isinstance(s, str) for s in stores):
            raise ConfigError(f"task #{i}: every platform must be a string")
        stores = [s.strip().lower() for s in stores if s.strip()]
        if not stores:
            raise ConfigError(f"task #{i}: 'platforms' cannot be empty")

        unknown = [s for s in stores if s not in ALLOWED_PLATFORMS]
        if unknown:
            raise ConfigError(f"task #{i}: unsupported platforms {unknown}, allowed: {sorted(ALLOWED_PLATFORMS)}")

        keywords = task.get("keywords")
        if not isinstance(keywords, list) or not keywords:
            raise ConfigError(f"task #{i}: 'keywords' must be a non-empty array")
        if any(not isinstance(k, str) or not k.strip() for k in keywords):
            raise ConfigError(f"task #{i}: every keyword must be a non-empty string")

        countries = task.get("countries")
        if not isinstance(countries, list) or not countries:
            raise ConfigError(f"task #{i}: 'countries' must be a non-empty array")
        if any(not isinstance(c, str) or not c.strip() for c in countries):
            raise ConfigError(f"task #{i}: every country must be a non-empty string")

        n_hits = task.get("n_hits", 50)
        if not isinstance(n_hits, int) or n_hits <= 0:
            raise ConfigError(f"task #{i}: 'n_hits' must be an integer greater than 0")

        android_id = task.get("android_id", "")
        if "play" in stores and (not isinstance(android_id, str) or not android_id.strip()):
            raise ConfigError(f"task #{i}: 'android_id' is required when platform includes 'play'")

        ios_id = task.get("ios_id", "")
        ios_id_str = str(ios_id).strip()
        if "app" in stores and (not ios_id_str or not ios_id_str.isdigit()):
            raise ConfigError(f"task #{i}: 'ios_id' is required and must be numeric when platform includes 'app'")

        normalized.append({
            **task,
            "platforms": stores,
            "keywords": [k.strip() for k in keywords],
            "countries": [c.strip().lower() for c in countries],
            "n_hits": n_hits,
            "android_id": android_id.strip() if isinstance(android_id, str) else android_id,
            "ios_id": ios_id_str,
        })
        if active:
            has_active_task = True

    if not has_active_task:
        raise ConfigError("no active tasks found")

    return normalized


def scrape_ios(page, term, region, limit):
    url = f"https://apps.apple.com/{region}/iphone/search?term={urllib.parse.quote(term)}"
    try:
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)
    except PlaywrightTimeoutError as exc:
        raise ScrapeError("timeout", f"iOS timeout for term='{term}' region='{region}'") from exc
    except PlaywrightError as exc:
        raise ScrapeError("navigation", f"iOS navigation failure for term='{term}' region='{region}': {exc}") from exc
    
    found = []
    max_scrolls = max(8, limit // 15)
    for _ in range(max_scrolls):
        try:
            links = page.query_selector_all("a[href*='/app/'], a[href*='/id']")
            for el in links:
                href = el.get_attribute("href") or ""
                match = re.search(r"/id(\d+)", href)
                if match and match.group(1) not in found:
                    found.append(match.group(1))
                if len(found) >= limit:
                    return found
            page.evaluate("window.scrollBy(0, 1500)")
            time.sleep(0.4)
        except PlaywrightError as exc:
            raise ScrapeError("dom", f"iOS DOM failure for term='{term}' region='{region}': {exc}") from exc
    return found


def scrape_android(page, term, region, limit):
    lang = region.lower() if region.lower() in ("it", "de", "fr", "es", "pt") else "en"
    url = f"https://play.google.com/store/search?q={urllib.parse.quote(term)}&c=apps&gl={region.upper()}&hl={lang}"
    
    try:
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)
    except PlaywrightTimeoutError as exc:
        raise ScrapeError("timeout", f"Android timeout for term='{term}' region='{region}'") from exc
    except PlaywrightError as exc:
        raise ScrapeError("navigation", f"Android navigation failure for term='{term}' region='{region}': {exc}") from exc
    
    found = []
    max_scrolls = max(8, limit // 20)
    
    for _ in range(max_scrolls):
        try:
            links = page.query_selector_all("a[href*='/store/apps/details?id=']")
            for el in links:
                href = el.get_attribute("href") or ""
                match = re.search(r"id=([a-zA-Z0-9._]+)", href)
                if match and match.group(1) not in found:
                    found.append(match.group(1))
                if len(found) >= limit:
                    return found
            
            page.evaluate("window.scrollBy(0, 2000)")
            time.sleep(0.5)
        except PlaywrightError as exc:
            raise ScrapeError("dom", f"Android DOM failure for term='{term}' region='{region}': {exc}") from exc
    
    return found


def find_position(listing, target_id):
    for idx, app_id in enumerate(listing):
        if app_id == target_id:
            return idx + 1
    return 0


def normalize_platforms(platforms):
    if isinstance(platforms, str):
        return [platforms]
    return platforms


def count_searches(config):
    android_total = 0
    ios_total = 0
    
    for task in config:
        if not task.get("active", True):
            continue
        
        stores = normalize_platforms(task.get("platforms", ["play"]))
        total = len(task.get("keywords", [])) * len(task.get("countries", []))
        
        if "play" in stores:
            android_total += total
        if "app" in stores:
            ios_total += total
    
    return android_total, ios_total


def run_scan():
    try:
        config = load_config()
    except ConfigError as exc:
        sys.exit(f"Invalid settings.json: {exc}")

    output = []
    error_stats = defaultdict(int)
    
    android_searches, ios_searches = count_searches(config)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        android_pbar = tqdm(total=android_searches, desc="Android", unit="",
                           bar_format='{desc} |{bar}| {percentage:3.0f}%') if android_searches > 0 else None
        ios_pbar = tqdm(total=ios_searches, desc="iOS", unit="",
                       bar_format='{desc} |{bar}| {percentage:3.0f}%') if ios_searches > 0 else None

        for task in config:
            if not task.get("active", True):
                continue

            stores = normalize_platforms(task.get("platforms", ["play"]))
            android_id = task.get("android_id", "")
            ios_id = str(task.get("ios_id", ""))
            limit = task.get("n_hits", 50)

            for store in stores:
                target = ios_id if store == "app" else android_id
                store_label = "iOS" if store == "app" else "Android"
                pbar = ios_pbar if store == "app" else android_pbar

                for kw in task.get("keywords", []):
                    for region in task.get("countries", []):
                        try:
                            listing = scrape_ios(page, kw, region.lower(), limit) if store == "app" else scrape_android(page, kw, region.lower(), limit)
                            pos = find_position(listing, target)

                            output.append({
                                "store": store_label,
                                "keyword": kw,
                                "region": region.upper(),
                                "position": pos if pos > 0 else "-"
                            })
                        except ScrapeError as exc:
                            error_stats[exc.code] += 1
                            logger.warning(str(exc))
                            output.append({
                                "store": store_label,
                                "keyword": kw,
                                "region": region.upper(),
                                "position": "ERROR"
                            })
                        except Exception as exc:
                            error_stats["unexpected"] += 1
                            logger.exception("Unexpected scrape error for store='%s' region='%s' keyword='%s': %s", store_label, region.upper(), kw, exc)
                            output.append({
                                "store": store_label,
                                "keyword": kw,
                                "region": region.upper(),
                                "position": "ERROR"
                            })
                        finally:
                            if pbar:
                                pbar.update(1)

        if android_pbar:
            android_pbar.close()
        if ios_pbar:
            ios_pbar.close()

        browser.close()

    if error_stats:
        summary = ", ".join(f"{k}={v}" for k, v in sorted(error_stats.items()))
        logger.info("Scrape error summary: %s", summary)

    return output


def print_results(data):
    if not data:
        return
    
    print("\n" + "-" * 60)
    print(f"{'#':<4} {'Store':<8} {'Region':<6} {'Pos':<6} Keyword")
    print("-" * 60)
    
    for i, row in enumerate(data, 1):
        pos = row["position"]
        print(f"{i:<4} {row['store']:<8} {row['region']:<6} {str(pos):<6} {row['keyword'][:35]}")
    
    print("-" * 60)
    
    ranked = sum(1 for r in data if r["position"] not in ["-", "ERROR"])
    errors = sum(1 for r in data if r["position"] == "ERROR")
    not_found = sum(1 for r in data if r["position"] == "-")
    print(f"Total: {len(data)} | Ranked: {ranked} | Not found: {not_found} | Errors: {errors}\n")


def save_results(data):
    Path("results").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = Path(f"results/scan_{ts}.json")
    out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    results = run_scan()
    print_results(results)
    save_results(results)
