# App Rank Tracker

Track app rankings on Google Play Store and Apple App Store.

## Technologies

- **Web scraping**: [Playwright](https://playwright.dev/) (Chromium browser automation)

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

### Example Output

```
Android |███████████████████████████████████████████████████████████| 100%
iOS |███████████████████████████████████████████████████████████████| 100%

------------------------------------------------------------
#    Store    Region Pos    Keyword
------------------------------------------------------------
1    Android  US     1      clash of clans
2    Android  IT     1      clash of clans
3    Android  US     3      supercell
4    Android  IT     7      supercell
5    Android  US     5      strategy game
6    Android  IT     8      strategy game
7    iOS      US     1      clash of clans
8    iOS      IT     1      clash of clans
9    iOS      US     3      supercell
10   iOS      IT     8      supercell
11   iOS      US     -      strategy game
12   iOS      IT     4      strategy game
------------------------------------------------------------
Total: 12 | Ranked: 11 | Not found: 1 | Errors: 0
```

Results saved in `results/`.
