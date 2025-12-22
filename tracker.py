#!/usr/bin/env python3
"""
Store Rank Scanner - Tracks app positions across iOS and Android stores.
"""
import json
import re
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright
from tqdm import tqdm


def load_config():
    return json.loads(Path("settings.json").read_text(encoding="utf-8"))


def scrape_ios(page, term, region, limit):
    url = f"https://apps.apple.com/{region}/iphone/search?term={urllib.parse.quote(term)}"
    try:
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)
    except Exception:
        return []
    
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
        except Exception:
            break
    return found


def scrape_android(page, term, region, limit):
    lang = region.lower() if region.lower() in ("it", "de", "fr", "es", "pt") else "en"
    url = f"https://play.google.com/store/search?q={urllib.parse.quote(term)}&c=apps&gl={region.upper()}&hl={lang}"
    
    try:
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)
    except Exception:
        return []
    
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
        except Exception:
            break
    
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
    config = load_config()
    output = []
    
    android_searches, ios_searches = count_searches(config)
    
    try:
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
                            except Exception:
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
    except Exception:
        raise
    
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
