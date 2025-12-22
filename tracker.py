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
import google_play_scraper


def log(msg, level="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"info": ".", "ok": "+", "warn": "!", "err": "x"}.get(level, ".")
    print(f"[{ts}] ({prefix}) {msg}")


def load_config():
    return json.loads(Path("settings.json").read_text(encoding="utf-8"))


def scrape_ios(page, term, region, limit):
    url = f"https://apps.apple.com/{region}/iphone/search?term={urllib.parse.quote(term)}"
    try:
        page.goto(url, timeout=20000)
        page.wait_for_timeout(3000)
    except Exception as e:
        log(f"iOS load failed: {e}", "warn")
        return []
    
    found = []
    max_scrolls = max(8, limit // 15)
    for i in range(max_scrolls):
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
    return found


def scrape_android(term, region, limit):
    """Use google-play-scraper API for Android."""
    try:
        lang = region.lower() if region.lower() in ("it", "de", "fr", "es", "pt") else "en"
        results = google_play_scraper.search(term, lang=lang, country=region.upper(), n_hits=limit)
        return [r["appId"] for r in results]
    except Exception as e:
        log(f"Android API failed: {e}", "warn")
        return []


def find_position(listing, target_id):
    for idx, app_id in enumerate(listing):
        if app_id == target_id:
            return idx + 1
    return 0


def run_scan():
    config = load_config()
    output = []
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        
        for task in config:
            if not task.get("active", True):
                continue
            
            stores = task.get("platforms", ["play"])
            if isinstance(stores, str):
                stores = [stores]
            
            android_id = task.get("android_id", "")
            ios_id = str(task.get("ios_id", ""))
            limit = task.get("n_hits", 50)
            
            for store in stores:
                target = ios_id if store == "app" else android_id
                store_label = "iOS" if store == "app" else "Android"
                log(f"Scanning {store_label}: {target}")
                
                for kw in task.get("keywords", []):
                    for region in task.get("countries", []):
                        
                        if store == "app":
                            listing = scrape_ios(page, kw, region.lower(), limit)
                        else:
                            listing = scrape_android(kw, region, limit)
                        
                        log(f"  Found {len(listing)} apps for '{kw}' in {region.upper()}", "info")
                        if len(listing) > 0 and len(listing) < 5:
                            log(f"    IDs: {listing[:5]}", "info")
                        pos = find_position(listing, target)
                        
                        output.append({
                            "store": store_label,
                            "keyword": kw,
                            "region": region.upper(),
                            "position": pos if pos > 0 else "-"
                        })
                        
                        if pos > 0:
                            log(f"  {kw} [{region.upper()}] -> #{pos}", "ok")
                        else:
                            log(f"  {kw} [{region.upper()}] -> not found", "warn")
        
        browser.close()
    
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
    
    ranked = sum(1 for r in data if r["position"] != "-")
    print(f"Total: {len(data)} | Ranked: {ranked} | Not found: {len(data) - ranked}\n")


def save_results(data):
    Path("results").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = Path(f"results/scan_{ts}.json")
    out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log(f"Results saved to {out_file}", "ok")


if __name__ == "__main__":
    log("Starting scan...")
    results = run_scan()
    print_results(results)
    save_results(results)
    log("Done.")
