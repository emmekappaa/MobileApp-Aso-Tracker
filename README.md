# App Rank Tracker

Track app rankings on Google Play Store and Apple App Store.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install playwright google-play-scraper
playwright install chromium
```

## Configuration

Create `settings.json`:

```json
[
  {
    "platforms": ["play", "app"],
    "android_id": "com.example.app",
    "ios_id": "1234567890",
    "n_hits": 100,
    "keywords": ["keyword1", "keyword2"],
    "countries": ["us", "it"]
  }
]
```

## Usage

```bash
python tracker.py
```

Results saved in `results/`.
