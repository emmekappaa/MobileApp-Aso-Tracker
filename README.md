# Mobile ASO Tracker

**ASO ranking tracker** for monitoring app positions across Google Play and the App Store.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-latest-green.svg)](https://playwright.dev/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.txt)

## ✨ Features

- **Dual-store tracking** - Track both Google Play and the App Store
- **Multi-region support** - Track rankings across different countries
- **Batch processing** - Scan multiple keywords simultaneously
- **JSON export** - Automatically saves timestamped results
- **AI-powered analysis** - Turn raw rankings into an actionable ASO report using a local LLM

## 🚀 Quick Start (Docker)

The fastest way to run the full stack (scraper + local LLM). No separate Python, Playwright, or Ollama installation is needed.

### 1. Configure

Create a `settings.json` file in the project root:

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
| `platforms` | array | Platforms to scan: `"play"` (Google Play), `"app"` (App Store) |
| `android_id` | string | App package name (e.g., `"com.example.app"`) |
| `ios_id` | string | App Store numeric ID (e.g., `"1234567890"`) |
| `n_hits` | integer | Maximum search depth (default: `50`). Higher values are slower but may return more results |
| `keywords` | array | Search terms to track |
| `countries` | array | Country codes (e.g., `["us", "it", "de"]`) |

### 2. Run

```bash
docker compose up
```

That's it: Docker starts Ollama, pulls `qwen2.5:7b-instruct` on the first run, waits until the
model is ready, then runs a scan followed by the AI analysis. `settings.json` and `results/` are
bind-mounted into the `tracker` container, and the Ollama model is stored in a named volume so it
is downloaded only once. For later scans, once Ollama is already running:

```bash
docker compose run --rm tracker
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

## 🤖 About the AI Analysis

`analyze.py` turns the raw scan JSON into a natural-language ASO report. It compares the latest
scan to the previous one, computes per-keyword position deltas, and sends a compact summary (not
the raw JSON) to a local LLM to flag underperforming keywords, keywords worth reinforcing, and
unusual patterns (e.g. a sudden drop in a specific country/store, or an inconsistency between
iOS and Android). Runs fully offline via [Ollama](https://ollama.com/) - no API key, no cost. The
report is printed to console and saved as `results/analysis_YYYYMMDD_HHMMSS.txt`.

Use `--model` to try a different Ollama model, e.g. `python analyze.py --model qwen2.5:14b-instruct`.

## 🐍 Manual Installation (without Docker)

Prefer running natively? You'll need Python, [Ollama](https://ollama.com/) installed locally, and:

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

Create `settings.json` as described above, then:

```bash
python tracker.py

# optional: AI analysis of the results
ollama pull qwen2.5:7b-instruct
ollama serve
python analyze.py
```

## 🛠️ Tech Stack

- **[Playwright](https://playwright.dev/)** - Chromium browser automation for accurate web scraping
- **[Ollama](https://ollama.com/)** - Local LLM inference for AI-powered ASO analysis

## 📝 License

MIT
