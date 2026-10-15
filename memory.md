# 🧠 Hyper Motion — Project Memory

> **This file is the single source of truth for project state and history.**
> **⚠️ RULE — UPDATE THIS FILE AFTER EVERY COMPLETED TASK:**
> add an entry to [§8 Task Log](#8-task-log), then adjust the other sections if
> anything changed (structure, status, known issues, next steps).
> Keep entries short, dated, factual.

| | |
|---|---|
| **Project** | Hyper Motion — Multi-Agent Autonomous Content Research · Scriptwriting · SEO · Facebook Growth Engine |
| **Version** | 1.0.2 (`pyproject.toml`) |
| **Stack** | Python 3.10+ (dev machine: 3.14.7) · FastAPI · Uvicorn · SQLite (aiosqlite) · APScheduler · Rich · SSE |
| **Repo** | `F:\Workshop\Automation\Hyper-Motion` · GitHub: `sayeeddesignerz-creator/Hyper-Motion` · branch `main` |
| **Last updated** | 2026-10-15 |

---

## 1. What This Is

An autonomous, multi-agent content engine. It hunts trends, fact-checks claims,
writes second-by-second scripts, produces SEO bundles (titles/descriptions/tags),
generates Facebook posts · stories · reels · quiz images (AI visuals), and can
publish/engage on a real Facebook Page — all coordinated by an orchestrator and
an optional 24/7 scheduler. Everything is controlled from a local "Mission
Control" dashboard.

---

## 2. Quick Reference — Run It

```powershell
python hypermotion.py          # dev start (or double-click hypermotion.bat)
hypermotion                    # global shim (runs `python -m app.main` from project dir)
hypermotion init / start / version   # CLI (hypermotion_cli.py)
pytest tests/ -v               # test suite (pytest.ini → asyncio_mode = auto)
pip install -e ".[dev]"        # editable install with dev deps
```

| URL | What |
|---|---|
| http://localhost:8500/ | Mission Control dashboard + AI Command Center (`dashboard/index.html`) |
| http://localhost:8500/docs | OpenAPI docs |
| /api/webhook/facebook | Meta Graph webhook (verify token in `.env`) |

---

## 3. Repository Map

```
Hyper-Motion/
├── app/                  # FastAPI application (core)
│   ├── main.py           # entrypoint, Rich banner, serves dashboard
│   ├── api.py            # all REST + SSE endpoints
│   ├── orchestrator.py   # multi-agent pipeline coordinator
│   ├── scheduler.py      # APScheduler — autonomous recurring runs
│   ├── db.py             # SQLite layer → data/ultimate.db
│   ├── events.py         # SSE event bus (live UI updates)
│   ├── models.py         # Pydantic models
│   ├── config.py         # settings, paths, channel config (env + YAML)
│   ├── agents/           # 11 agents: trend_hunter, fact_checker, strategist,
│   │                     #   script_forge, seo_optimizer, audience_miner,
│   │                     #   learner, facebook_growth, facebook_content,
│   │                     #   engagement, base
│   ├── llm/              # gateway (multi-provider cascade, circuit
│   │                     #   breaker, DB provider sync) + gemini/openai providers
│   └── tools/            # trends, news, reddit, youtube_search, webfetch,
│                         #   facebook, image_generator, quiz_generator,
│                         #   cache, conversation_library
├── dashboard/            # index.html = Mission Control + AI Command Center
├── data/                 # ultimate.db (app state) · gateway_state.db (LLM state) — gitignored
├── output/               # facebook_media/ · quizzes/ — generated media — gitignored
├── config/               # YAML channel config (optional)
├── scripts/              # ops utilities (check_comments.py)
├── tests/                # pytest suite (pipeline, gateway, facebook)
├── hypermotion.py        # python launcher
├── hypermotion_cli.py    # `hypermotion` console script (init/start/version)
├── hypermotion.bat       # Windows double-click launcher
└── memory.md             # ← this file
```

---

## 4. Environment & Secrets

- All secrets live in **`.env`** (never committed; template: `.env.example`).
- Key variables: `GEMINI_API_KEY(S)` · `OPENAI_API_KEY` · `OPENROUTER_API_KEY` ·
  `GROQ_API_KEY` · `ANTHROPIC_API_KEY` · `YOUTUBE_API_KEY` · `REDDIT_*` ·
  `FACEBOOK_PAGE_ID` · `FACEBOOK_PAGE_ACCESS_TOKEN` · `FACEBOOK_APP_ID/SECRET` ·
  `FACEBOOK_SIMULATION_MODE` (sandbox publishing) · `DASHBOARD_API_KEY` ·
  `PORT`/`HOST` · `CHANNEL_NAME`/`TARGET_AUDIENCE`/`CONTENT_TONE` ·
  `AUTONOMOUS_ENABLED`/`AUTONOMOUS_INTERVAL_MINUTES`.
- `hypermotion init` scaffolds a fresh workspace (`.env` template + empty dirs).

---

## 5. Known Issues / TODO

| # | Severity | Item |
|---|---|---|
| 1 | 🔴 **SECURITY** | **Facebook credential rotation — USER ACTION REQUIRED.** `exchange_token.py` (hardcoded user token + app secret) was purged from git history on 2026-10-15 with `git filter-repo` — all commit hashes rewritten locally. **Force-push still pending** (`git push --force-with-lease origin main`). Rotate the FB app secret, user token and page token; regenerate `FACEBOOK_PAGE_ACCESS_TOKEN` in `.env`. |
| 2 | 🟡 | **YouTube Studio endpoints return mock data** (`/api/youtube/*` in `api.py`) — static numbers, not wired to the real YouTube Data API. Deferred by choice on 2026-10-15. |
| 3 | 🟢 | The on-PATH `hypermotion` command is an npm-folder shim (runs `python -m app.main`), not the pip console script. |
| 4 | 🟢 | `OmniRoute` API endpoints (`/api/omniroute/*`) still exist for provider management — kept intentionally; providers saved there now register as **live gateway handles** (incl. Groq) via `LLMGateway.sync_providers_from_db()`. |

---

## 6. Housekeeping Rules

1. **Never commit:** `.env*`, `data/`, `output/`, `.cache/`, `__pycache__/`, `dist/`, `*.egg-info/` (all covered by `.gitignore` — keep it that way).
2. **Keep the root clean:** no one-off debug/validation scripts. Reusable tooling goes in `scripts/`; throwaways get deleted when the task is done.
3. **Generated media stays in** `output/facebook_media/` and `output/quizzes/` only — never at `output/` root, never in git.
4. **After every completed task:** update §8 Task Log here; bump "Last updated"; adjust §5 if an issue is fixed/added.

---

## 7. Git Notes

- Branch: `main` (tracks `origin/main`). All commits so far dated 2026-10-15.
- ⚠️ **History rewritten 2026-10-15** with `git filter-repo` to purge `exchange_token.py` from all commits — local commit hashes changed; the `origin` remote was re-added but **NOT force-pushed yet**.
- Recent work direction: unifying dashboard into "AI Command Center" (node-graph studio + AI Brain), LLM router resilience, Facebook growth engine, backlog completion session.

---

## 8. Task Log

> Newest first. Format: `### YYYY-MM-DD — title ✅` + bullets (what changed, follow-ups).

### 2026-10-15 — Backlog completion (report items 1–13, YouTube skipped) ✅
**Goal:** finish every item in the unfinished-work report except YouTube Studio (deferred by choice).
- 🧹 **Repo cleanup committed:** the 141-entry staged cleanup + untracked the last 4 `tests/__pycache__/*.pyc` + `LICENSE` committed.
- 🗑️ **History purge:** `exchange_token.py` (leaked FB secrets) removed from ALL commits via `git filter-repo`; origin remote re-added — **force-push is a user action** (see §5 #1).
- 🔧 **Bug fixes:** `app/orchestrator.py` `self.logger` crash → module `logger`; duplicate routes removed (`/api/events` ×2, `/api/facebook/messenger/history` ×2 — now DB-first with live-Graph fallback); app version now single-sourced via `app.config.get_app_version()` (banner, FastAPI, `/health`, CLI all report `1.0.2`).
- ✨ **SEO Matrix tab finished:** new `GET /api/seo/bundles` → `db.get_recent_seo_bundles()` (JOINed script titles); `loadSEO()` renders A/B variants, description, tags, hashtags with copy buttons; loads on tab open.
- 🔌 **Provider wiring:** `LLMGateway.sync_providers_from_db()` registers dashboard-saved providers (Gemini/OpenAI/OpenRouter/Groq/custom) as live handles at startup and after provider save/delete; `groq`/`groq_fast` aliases added; routes with unknown providers warn and fall back to `gemini`; env-configured handles remain the baseline.
- 🗑️ **Dead code removed:** `app/llm/omnirouter.py` (+ export, + its test), `dashboard/brain.html` (+ `/brain` route). `/api/brain/*` endpoints kept — they power the AI Command Center.
- 🧹 **Tidying:** `.env.example` header renamed; `requirements.txt` notes pyproject as source of truth; `tests/test_facebook.py` simulation-pin fix committed.
- 🧪 **Tests:** 16/16 pass — removed OmniRouter test; added DB-provider sync + unknown-provider fallback tests; extended CRUD test with SEO bundle list assertions.
- ⏭️ **Follow-ups (user):** rotate FB credentials; `git push --force-with-lease origin main`; YouTube Studio endpoints still mock (see §5 #2).

### 2026-10-15 — Full repository organization & cleanup ✅
**Goal:** professional file/folder structure, remove unused files, add memory.md.
- 🗑️ **Deleted (caches/build artifacts):** all `__pycache__/` dirs, `.pytest_cache/`, `dist/` (1.0.2 wheel+sdist), `hypermotion.egg-info/` — all regeneratable.
- 🗑️ **Deleted (stale):** `dashboard/index.html.bak` (pre-fix backup), `data/hypermotion.db` (0-byte, unreferenced).
- 🗑️ **Deleted (11 one-off debug scripts):** `check_all_scripts.js`, `check_brain_tags.js`, `check_div_balance.js`, `find_dup_lines.js`, `find_duplicates.js`, `find_tab_brain.js`, `list_panels.js`, `search_tabs.py`, `trace_brain_divs.js`, `validate_html_tags.js`, `validate_js.js` (leftovers from the dashboard-HTML debugging sessions; unreferenced).
- 🗑️ **Deleted (dev scratch in `output/` root):** `test_box.png`, `test_flux.jpg`, `test_photo_quiz.png`, `test_quiz.png`, `test_runner.jpg`, `visual_quiz_final.png`, `visual_quiz_perfect.png`.
- 🔴 **Deleted `exchange_token.py`** (hardcoded FB secrets) from disk **and** git index → rotation flagged in §5 #1.
- 📦 **Moved:** `check_comments.py` → `scripts/check_comments.py` (renamed in git index).
- 🧹 **Git untracking:** 139 `.pyc` files + generated media (`output/facebook_media/*`, `output/quizzes/quiz_*.png`) removed from git tracking — **kept on disk**; repo now matches its own `.gitignore` policy.
- ➕ **Created:** `memory.md` (this file), `LICENSE` (MIT — README badge/link referenced it but the file was missing), `scripts/` folder.
- 🧪 **Fixed test isolation:** `tests/test_facebook.py::test_facebook_client_simulation` now pins sandbox mode after client construction — previously a real FB token in `.env` leaked into the "simulation" test and made it fail with a live Graph API 400. Full suite re-run: **15/15 pass**.
- ✅ Staged cleanup ready (141 entries); none committed — user reviews & commits.
- ⏭️ **Follow-ups:** rotate FB credentials (§5 #1); commit cleanup; fix version string (§5 #2).

### 2026-10-14/15 — Pre-memory history (from git log, for context)
- `8524fc4` fix: AI Command Center blank screen (natural layout flow)
- `8b0803b` fix: edge-to-edge layout, node graph fills full width
- `bc36e69` feat: merge Node Graph Studio + AI Brain → unified AI Command Center
- `9e52cba` fix(llm): resilient json codeblock parser
- `4ed3dfe` feat(ai): ConversationSkills library (adaptive formality, human persona)
- `d52bd19` fix(ui): duplicate tab header, node load, modal close
- `6cb7654` feat(ui): Node Graph Studio (DaVinci/Blender-style)
- `dc3c746` refactor: remove OmniRoute proxy vendor; direct provider routing
- `32ff96d` feat: pip install support + `hypermotion` CLI
- `f7ce01f` Initial commit — Hyper-Motion automation platform
