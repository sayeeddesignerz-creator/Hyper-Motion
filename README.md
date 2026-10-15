# ⚡ Hyper Motion (Mission Control)

**Hyper Motion** is a multi-agent autonomous content and social growth engine combining trend intelligence, factual verification, viral scriptwriting, and Facebook monetization automation. 

Designed specifically for **high-leverage content research, factual verification, strategic scriptwriting, and viral SEO growth** without the friction or overhead of local video rendering or direct YouTube OAuth publishing.

---

## 🚀 Key Weaponry & Capabilities

1. **Multi-Source Trend Radar**
   - Automatically monitors **Google Trends (daily momentum)**, **Google News RSS**, **Reddit Hot Posts**, and **YouTube Trending topics**.
   - Intelligent fuzzy deduplication using `rapidfuzz`.

2. **Rigorous Fact-Checking Lab**
   - Extracts discrete testable claims from breakout topics.
   - Cross-references facts against web consensus with confidence scoring (`verified`, `debunked`, `partially_true`).
   - Produces detailed evidence citations.

3. **Content Strategy & Evergreen Engine**
   - Automatically formulates the editorial angle, target emotional hook, and optimal format (`shorts` vs `long_form`).
   - Built-in evergreen topic generator for days when news cycles are quiet.

4. **Script Forge & Production Timeline**
   - Generates high-retention scripts broken down by seconds.
   - Provides concrete **visual cues (B-roll, graphic overlays)**, **on-screen text**, **audio tags**, and **conversion-focused CTAs**.

5. **SEO & Growth Matrix**
   - Generates an optimal primary title + **4 distinct A/B testing title variants** (Intrigue, Question, Statistic, Contrarian).
   - Generates full 200+ word YouTube descriptions with chapter timestamps, tags, hashtags, and a discoverability score.

6. **Audience Engagement & Idea Vault**
   - Analyzes viewer comment feedback and sentiment.
   - Mines viewer questions and extracts future video ideas.
   - Drafts high-engagement AI responses.

7. **Multi-Provider LLM Gateway with Fallback**
   - Supports **Google Gemini** (`gemini-2.5-flash`), **OpenAI** (`gpt-4o-mini`), and **OpenRouter**.
   - Automatic fallback to secondary provider if primary key or model encounters rate limits.

8. **Autonomous 24/7 Scheduler**
   - Background scheduler sweeps for trends, runs fact-checks, and drafts full production scripts on configurable intervals.

9. **Facebook Page Growth & Monetization Engine (Meta Graph API)**
   - **Deep Page Analysis & Audit**: Evaluates profile health, past post engagement, audience sentiment, and viral retention.
   - **Monetization Milestone Tracking**: Real-time progress meters for Facebook In-Stream Ads & Stars requirements (5,000 followers, 60,000 watch minutes, 5 active pieces, policy compliance).
   - **Viral Content Generation**: Automatically writes hook-optimized **Feed Posts**, interactive 3-slide **Stories**, and 60s **Reels scripts**.
   - **Automated AI Visuals**: Generates high-converting 1:1 post artwork and 9:16 vertical full-bleed story backgrounds.
   - **Live Publishing & Scheduling**: Directly publishes text, photos, and stories to your Facebook Page, or schedules them for automated release.
   - **Authentic Sandbox Mode**: Includes fully functional simulation mode so you can preview, test, and iterate even before adding live Meta API tokens.

10. **Live Mission Control Dashboard**
    - High-end dark mode Glassmorphic web UI accessible at `http://localhost:8500`.
    - Dedicated Facebook Growth Studio with live mockups, monetization gauges, and direct one-click publishing.
    - Real-time Server-Sent Events (SSE) telemetry feed.

---

## 🛠️ Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
The `.env` file comes pre-configured with your active Gemini & YouTube API keys:
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key
PORT=8500
AUTONOMOUS_ENABLED=true
AUTONOMOUS_INTERVAL_MINUTES=60

# Facebook Page & Monetization Settings (Optional - Sandbox mode works without keys)
FACEBOOK_PAGE_ID=your-page-id
FACEBOOK_PAGE_ACCESS_TOKEN=your-meta-page-access-token
FACEBOOK_SIMULATION_MODE=false
```

### 3. Run the Agent
```bash
python -m app.main
```
Open **[http://localhost:8500](http://localhost:8500)** in your browser to access Mission Control.

### 4. Run Tests
```bash
pytest tests/ -v
```

---

## 🔌 OmniRoute — Local AI Proxy & Provider Hub

**OmniRoute** is an open-source local proxy that sits between this agent and your LLM providers. It lets you pool keys, set per-provider rate limits, and route traffic — all from a local dashboard. The agent uses it as a high-priority fallback after Gemini and before OpenAI/OpenRouter.

### Install

OmniRoute is distributed as an npm package from the official repo at [github.com/diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute):

```bash
npm install -g omniroute
```

### Run

```bash
omniroute
```

The proxy starts on **port 20128** by default.

### Open the Dashboard

Navigate to **[http://localhost:20128](http://localhost:20128)** in your browser.

1. Connect your providers (Gemini, OpenAI, Groq, etc.) from the dashboard.
2. Generate an API key in the **API Keys** section.
3. Copy it — you'll need it in the next step.

> ⚠️ **Terms Notice**: You must review and comply with each connected provider's Terms of Service before routing traffic through OmniRoute. The agent itself does not modify provider terms.

### Fill `.env`

```env
OMNIROUTE_BASE_URL=http://localhost:20128/v1
OMNIROUTE_API_KEY=your-omniroute-api-key-here
OMNIROUTE_MODEL=auto
```

- `OMNIROUTE_BASE_URL` — defaults to `http://localhost:20128/v1`. If you point this at a remote host, the gateway logs a startup warning.
- `OMNIROUTE_API_KEY` — required when OmniRoute's auth is enabled.
- `OMNIROUTE_MODEL` — use `auto` to let OmniRoute pick the best available model, or specify one explicitly (e.g. `gemini-2.5-flash`).

### How fallback works

| Priority | Provider | Condition |
|----------|----------|-----------|
| 1 | Gemini | Primary — used unless rate-limited or circuit open |
| 2 | OmniRoute | Fallback — local proxy, always attempted |
| 3 | OpenAI | If `OPENAI_API_KEY` is set |
| 4 | OpenRouter | If `OPENROUTER_API_KEY` is set |

Fact-critical agents (`fact_checker`, `script_forge`, `strategist`) on a fallback model produce responses tagged `model_tier: "fallback"` and will have the **FALLBACK MODEL** badge in the dashboard.

### Provider Health API

```
GET /api/providers
```

Returns per-provider status, call counts, token counts (today UTC), and circuit-breaker state. **API keys are never included in the response.**

---
