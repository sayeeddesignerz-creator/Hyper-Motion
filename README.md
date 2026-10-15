<div align="center">

# ⚡ Hyper Motion

**Multi-Agent Autonomous Content Research · Scriptwriting · SEO · Facebook Growth Engine**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Hyper--Motion-181717?style=for-the-badge&logo=github)](https://github.com/sayeeddesignerz-creator/Hyper-Motion)

</div>

---

## 🚀 Install in One Command

```bash
pip install hypermotion
```

> Requires **Python 3.10+**. A virtual environment is strongly recommended.

---

## ⚙️ Quick Start

### 1 — Install

```bash
pip install hypermotion
```

### 2 — Initialize a fresh workspace

```bash
# Creates .env template + empty data/output dirs — nothing from anyone else
hypermotion init
```

Or into a specific folder:

```bash
hypermotion init ./my-hypermotion
cd my-hypermotion
```

### 3 — Add your API keys

Edit the generated `.env` file:

```env
# Minimum required — pick at least one LLM provider
GEMINI_API_KEY=your-gemini-key-here

# Optional extras (adds fallback & image generation)
OPENAI_API_KEY=
OPENROUTER_API_KEY=

# Facebook Growth Engine (sandbox mode works without these)
FACEBOOK_PAGE_ID=
FACEBOOK_PAGE_ACCESS_TOKEN=
```

> 🔒 `.env` is listed in `.gitignore` — it is **never** committed or shared.

### 4 — Start the server

```bash
hypermotion start
```

Open **[http://localhost:8500](http://localhost:8500)** — Mission Control loads instantly.

---

## 🧩 CLI Reference

| Command | Description |
|---|---|
| `hypermotion init` | Scaffold a clean workspace (fresh `.env`, empty dirs) |
| `hypermotion init ./path --force` | Re-scaffold, overwriting existing files |
| `hypermotion start` | Start the FastAPI server |
| `hypermotion start --dir ./path` | Start from a specific project directory |
| `hypermotion version` | Print version |

---

## 🛡️ Fresh Install Guarantee

Every `hypermotion init` creates:

```
your-project/
├── .env                ← YOUR keys only (generated from template)
├── .gitignore          ← Secrets & output excluded automatically
├── data/               ← Empty — YOUR runtime DB only
├── output/             ← Empty — YOUR generated media only
│   ├── facebook_media/
│   └── quizzes/
├── .cache/             ← Empty — YOUR cache only
└── config/             ← Empty — YOUR YAML config only
```

**No API keys, images, databases, or any data from other users is ever included.**

---

## 🔋 What's Inside

| Capability | Details |
|---|---|
| **Trend Radar** | Google Trends · Google News RSS · Reddit Hot · YouTube Trending |
| **Fact-Checking Lab** | Claim extraction · Web consensus scoring · Evidence citations |
| **Script Forge** | Second-by-second scripts · B-roll cues · CTAs |
| **SEO Matrix** | 4 A/B title variants · 200+ word descriptions · Tags & hashtags |
| **Facebook Engine** | Feed posts · Stories · Reels · AI visuals · Live publishing |
| **LLM Gateway** | Gemini → OmniRoute → OpenAI → OpenRouter (auto-fallback) |
| **Autonomous Scheduler** | Runs every N minutes, hands-free 24/7 |
| **Mission Control UI** | Dark glassmorphic dashboard at `localhost:8500` |

---

## 🔌 Optional: OmniRoute (Local AI Proxy)

Pool multiple API keys and route them intelligently:

```bash
npm install -g omniroute
omniroute
```

Then in `.env`:

```env
OMNIROUTE_BASE_URL=http://localhost:20128/v1
OMNIROUTE_API_KEY=your-omniroute-key
OMNIROUTE_MODEL=auto
```

---

## 🛠️ Manual / Development Setup

```bash
git clone https://github.com/sayeeddesignerz-creator/Hyper-Motion.git
cd Hyper-Motion
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -e ".[dev]"
hypermotion init
hypermotion start
```

Run tests:

```bash
pytest tests/ -v
```

---

## ⚠️ Security

- **Never commit `.env`** — it is excluded by `.gitignore`
- All output (`data/`, `output/`) is local to your machine
- Facebook tokens are stored only in your `.env` — not logged or transmitted anywhere except the Meta Graph API
- Rotate any API key that was accidentally exposed

---

## 📄 License

MIT © [sayeeddesignerz-creator](https://github.com/sayeeddesignerz-creator)
