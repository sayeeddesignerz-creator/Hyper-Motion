"""
hypermotion_cli.py — The `hypermotion` command-line interface.

Commands
--------
  hypermotion init    — Set up a fresh Hyper-Motion workspace in the current directory
  hypermotion start   — Start the Hyper-Motion server
  hypermotion version — Print version info
"""
from __future__ import annotations

import os
import sys
import shutil
import argparse
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _c(text: str, code: str) -> str:
    """Wrap text in an ANSI colour code (no-op on Windows without ANSI support)."""
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7
            )
        except Exception:
            pass
    return f"\033[{code}m{text}\033[0m"

GREEN  = lambda t: _c(t, "32")
YELLOW = lambda t: _c(t, "33")
CYAN   = lambda t: _c(t, "36")
BOLD   = lambda t: _c(t, "1")
DIM    = lambda t: _c(t, "2")
RED    = lambda t: _c(t, "31")


def _ok(msg: str)   -> None: print(f"  {GREEN('✔')}  {msg}")
def _warn(msg: str) -> None: print(f"  {YELLOW('⚠')}  {msg}")
def _info(msg: str) -> None: print(f"  {CYAN('→')}  {msg}")
def _err(msg: str)  -> None: print(f"  {RED('✘')}  {msg}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# `hypermotion init`
# ─────────────────────────────────────────────────────────────────────────────

FRESH_DIRS = [
    "data",
    "output/facebook_media",
    "output/quizzes",
    ".cache",
    "config",
]

GITIGNORE_CONTENT = """\
# Hyper-Motion — auto-generated .gitignore
# ─────────────────────────────────────────
# SECRETS — never commit these
.env
.env.*
!.env.example

# Runtime databases (per-user, not shared)
data/

# Generated media output (can be large)
output/

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
venv/
.venv/
env/

# Cache
.cache/

# IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db
"""


def cmd_init(dest: Path, force: bool = False) -> None:
    """Scaffold a clean Hyper-Motion workspace — zero secrets, zero user data."""
    print()
    print(BOLD("  ⚡ Hyper-Motion — workspace initializer"))
    print(DIM("  ─────────────────────────────────────────"))
    print()

    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)

    # ── 1. Create fresh runtime directories ──────────────────────────────────
    for rel in FRESH_DIRS:
        p = dest / rel
        p.mkdir(parents=True, exist_ok=True)
        # Drop a .gitkeep so git tracks the empty directory
        keep = p / ".gitkeep"
        if not keep.exists():
            keep.touch()
    _ok("Created runtime directories  (data/, output/, .cache/, config/)")

    # ── 2. Copy .env.example → .env if not already present ───────────────────
    env_path = dest / ".env"
    example_src = _find_env_example()

    if env_path.exists() and not force:
        _warn(".env already exists — skipping (use --force to overwrite)")
    else:
        if example_src and example_src.exists():
            shutil.copy2(example_src, env_path)
            _ok("Created .env from template  (fill in your API keys)")
        else:
            # Fallback: write a minimal template inline
            env_path.write_text(_MINIMAL_ENV_TEMPLATE, encoding="utf-8")
            _ok("Created .env  (minimal template — fill in your API keys)")

    # ── 3. Write .gitignore ───────────────────────────────────────────────────
    gi = dest / ".gitignore"
    if gi.exists() and not force:
        _warn(".gitignore already exists — skipping")
    else:
        gi.write_text(GITIGNORE_CONTENT, encoding="utf-8")
        _ok("Created .gitignore  (secrets & output excluded)")

    # ── 4. Summary ────────────────────────────────────────────────────────────
    print()
    print(BOLD("  Next steps:"))
    print()
    print(f"    1.  Edit  {CYAN(str(dest / '.env'))}")
    print(f"        Add your API keys (Gemini, OpenAI, Facebook, etc.)")
    print()
    print(f"    2.  {BOLD('hypermotion start')}  — Launch the server")
    print()
    print(f"    3.  Open  {CYAN('http://localhost:8500')}  in your browser")
    print()


def _find_env_example() -> Path | None:
    """Locate .env.example bundled with the installed package."""
    # When installed via pip the package data lives next to this file's parent
    candidates = [
        Path(__file__).parent / ".env.example",
        Path(__file__).parent.parent / ".env.example",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


_MINIMAL_ENV_TEMPLATE = """\
# === Hyper Motion — Environment Configuration ===
# Fill in your API keys and settings below.
# Copy this file to .env and never commit it to version control.

# ── LLM Providers ─────────────────────────────────────────────────────────────
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_API_KEYS=your-gemini-key-1,your-gemini-key-2

OPENAI_API_KEY=your-openai-api-key-here
OPENROUTER_API_KEY=your-openrouter-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GROQ_API_KEY=your-groq-api-key-here

# ── Models ────────────────────────────────────────────────────────────────────
GEMINI_MODEL=gemini-2.5-flash
OPENAI_MODEL=gpt-4o-mini
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free


# ── Intelligence APIs (optional) ──────────────────────────────────────────────
YOUTUBE_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=hypermotion/1.0

# ── Server ────────────────────────────────────────────────────────────────────
PORT=8500
HOST=0.0.0.0
DASHBOARD_API_KEY=

# ── Channel Branding ──────────────────────────────────────────────────────────
CHANNEL_NAME=Your Channel Name
TARGET_AUDIENCE=Your Target Audience
CONTENT_TONE=Analytical, Engaging, Energetic

# ── Autonomous Scheduler ──────────────────────────────────────────────────────
AUTONOMOUS_ENABLED=true
AUTONOMOUS_INTERVAL_MINUTES=60

# ── Facebook / Meta Graph API ─────────────────────────────────────────────────
FACEBOOK_PAGE_ID=
FACEBOOK_PAGE_ACCESS_TOKEN=
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_GRAPH_VERSION=v21.0
FACEBOOK_SIMULATION_MODE=false
FACEBOOK_WEBHOOK_VERIFY_TOKEN=hypermotion_webhook_secret
"""


# ─────────────────────────────────────────────────────────────────────────────
# `hypermotion start`
# ─────────────────────────────────────────────────────────────────────────────

def cmd_start(workdir: Path | None = None) -> None:
    """Start the Hyper-Motion FastAPI server."""
    if workdir:
        os.chdir(workdir)

    env_file = Path.cwd() / ".env"
    if not env_file.exists():
        _warn("No .env found — run  hypermotion init  first to create one.")
        print()

    # Ensure runtime directories exist (in case init was skipped)
    for rel in FRESH_DIRS:
        (Path.cwd() / rel).mkdir(parents=True, exist_ok=True)

    try:
        from app.main import start
        start()
    except ModuleNotFoundError:
        _err("Could not import app.main.")
        _info("Make sure you're running from the Hyper-Motion project directory,")
        _info("or that the package was installed correctly via:  pip install hypermotion")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# `hypermotion version`
# ─────────────────────────────────────────────────────────────────────────────

def cmd_version() -> None:
    try:
        from app.config import get_app_version
        v = get_app_version()
    except Exception:
        try:
            from importlib.metadata import version
            v = version("hypermotion")
        except Exception:
            v = "1.0.2"
    print(f"hypermotion {BOLD(v)}")


# ─────────────────────────────────────────────────────────────────────────────
# Argument parser
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hypermotion",
        description="⚡ Hyper-Motion — Multi-Agent Content & Growth Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  hypermotion init             # scaffold .env + dirs in current directory
  hypermotion init ./myproject # scaffold into a specific folder
  hypermotion start            # start the server
  hypermotion version          # show version
        """,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # init
    p_init = sub.add_parser("init", help="Set up a fresh Hyper-Motion workspace")
    p_init.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Target directory (default: current directory)",
    )
    p_init.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing .env and .gitignore",
    )

    # start
    p_start = sub.add_parser("start", help="Start the Hyper-Motion server")
    p_start.add_argument(
        "--dir", "-d",
        default=None,
        help="Project directory (default: current directory)",
    )

    # version
    sub.add_parser("version", help="Show version information")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "init":
        cmd_init(Path(args.directory), force=args.force)

    elif args.command == "start":
        workdir = Path(args.dir) if args.dir else None
        cmd_start(workdir)

    elif args.command == "version":
        cmd_version()

    else:
        # No subcommand — show help
        parser.print_help()
        print()
        print(BOLD("  Quick start:"))
        print(f"    {CYAN('hypermotion init')}     — scaffold a fresh workspace")
        print(f"    {CYAN('hypermotion start')}    — launch the server")
        print()


if __name__ == "__main__":
    main()
