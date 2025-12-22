# App Rank Tracker

Track app rankings on Google Play Store and Apple App Store.

## Technologies

- **iOS App Store**: Web scraping with [Playwright](https://playwright.dev/) (Chromium browser automation)
- **Google Play Store**: [google-play-scraper](https://github.com/JoMingyu/google-play-scraper) API

## Setup

```bash
python -m venv .venv

# Activate virtual environment:
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

## Configuration

Create `settings.json`:

```json
[
  {
    "active": true,
    "platforms": ["play", "app"],
    "android_id": "com.example.app",
    "ios_id": "1234567890",
    "n_hits": 100,
    "keywords": ["keyword1", "keyword2"],
    "countries": ["us", "it"]
  }
]
```

### Configuration Parameters

- **`active`**: `true`/`false` - Enable or disable this tracking task
- **`platforms`**: `["play", "app"]` - Stores to scan (`"play"` = Google Play, `"app"` = App Store)
- **`android_id`**: Your app's package name on Google Play (e.g., `"com.example.app"`)
- **`ios_id`**: Your app's numeric ID on App Store (e.g., `"1234567890"`)
- **`n_hits`**: Number of search results to analyze (default: `50`)
  - Higher values = deeper search but slower execution
  - Example: `100` checks top 100 positions, `200` checks top 200
  - If your app is ranked beyond this number, it will show as "not found"
- **`keywords`**: Array of search terms to track
- **`countries`**: Array of country codes (e.g., `["us", "it", "de", "fr"]`)

## Usage

```bash
python tracker.py
```

Results saved in `results/`.
