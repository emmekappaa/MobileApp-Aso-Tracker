# Mobile ASO Tracker

**Real-time ASO tracking tool** for monitoring app positions across Google Play Store and Apple App Store.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-latest-green.svg)](https://playwright.dev/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.txt)

## ✨ Features

- **Dual-store tracking** - Monitor both iOS App Store and Google Play
- **Multi-region support** - Track rankings across different countries
- **Batch processing** - Scan multiple keywords simultaneously
- **JSON export** - Automatic timestamped result saving

## 🚀 Quick Start

### Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### Configuration

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

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `active` | boolean | Enable/disable this tracking task |
| `platforms` | array | Stores to scan: `"play"` (Google Play), `"app"` (App Store) |
| `android_id` | string | App package name (e.g., `"com.example.app"`) |
| `ios_id` | string | App Store numeric ID (e.g., `"1234567890"`) |
| `n_hits` | integer | Search depth (default: `50`) higher = slower but deeper |
| `keywords` | array | Search terms to track |
| `countries` | array | Country codes (e.g., `["us", "it", "de"]`) |

### Run

```bash
python tracker.py
```

## 📈 Example Output

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

Results automatically saved in `results/scan_YYYYMMDD_HHMMSS.json`

## 🛠️ Tech Stack

- **[Playwright](https://playwright.dev/)** - Chromium browser automation for accurate web scraping

## 📝 License

MIT
