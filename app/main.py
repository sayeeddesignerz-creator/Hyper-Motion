"""
Application Entrypoint for Hyper Motion — Multi-Agent Content Engine.
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.api import router, orchestrator
from app.config import get_settings, PROJECT_ROOT, MEDIA_DIR
from app.scheduler import AutonomousScheduler

# ─────────────────────────────────────────────────────────────────────────────
# Suppress noisy default uvicorn/fastapi logs — rich handles display
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(name)s] %(message)s")
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logger = logging.getLogger("HyperMotion")

settings = get_settings()
scheduler = AutonomousScheduler(orchestrator)
DASHBOARD_PATH = PROJECT_ROOT / "dashboard" / "index.html"
BRAIN_PATH     = PROJECT_ROOT / "dashboard" / "brain.html"


# ─────────────────────────────────────────────────────────────────────────────
# Rich Terminal Banner & Status Panel
# ─────────────────────────────────────────────────────────────────────────────
def _print_banner() -> None:
    """Print a premium, coloured startup banner via Rich."""
    try:
        # Reconfigure stdout to UTF-8 in-place so box-drawing glyphs render on
        # Windows without closing the file handle that uvicorn needs later.
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table
        from rich import box
        from rich.rule import Rule
        from rich.padding import Padding
        import datetime

        console = Console(highlight=False)

        # ── ASCII-art logo (stored as escaped Unicode so the .py source stays
        #    ASCII-clean; the characters are the standard cp437 block glyphs)  ──
        LOGO_ROWS = [
            ("\u2588\u2588\u2557  \u2588\u2588\u2557 \u2588\u2588\u2557   \u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557 ", "bold #7C3AED"),
            ("\u2588\u2588\u2551  \u2588\u2588\u2551 \u255a\u2588\u2588\u2557 \u2588\u2588\u2554\u255d \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557 \u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557", "bold #7C3AED"),
            ("\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551  \u255a\u2588\u2588\u2588\u2588\u2554\u255d  \u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d \u2588\u2588\u2588\u2588\u2588\u2557   \u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d", "bold #9333EA"),
            ("\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551   \u255a\u2588\u2588\u2554\u255d   \u2588\u2588\u2554\u2550\u2550\u2550\u255d  \u2588\u2588\u2554\u2550\u2550\u255d   \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557", "bold #A855F7"),
            ("\u2588\u2588\u2551  \u2588\u2588\u2551    \u2588\u2588\u2551    \u2588\u2588\u2551      \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2551  \u2588\u2588\u2551", "bold #C084FC"),
            ("\u255a\u2550\u255d  \u255a\u2550\u255d    \u255a\u2550\u255d    \u255a\u2550\u255d      \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d  \u255a\u2550\u255d", "bold #DDD6FE"),
            ("", ""),
            ("\u2588\u2588\u2588\u2557   \u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2557   \u2588\u2588\u2557", "bold #7C3AED"),
            ("\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2551 \u2588\u2588\u2554\u2550\u2550\u2550\u2588\u2588\u2557 \u255a\u2550\u2550\u2588\u2588\u2554\u2550\u2550\u255d \u2588\u2588\u2551 \u2588\u2588\u2554\u2550\u2550\u2550\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2551", "bold #9333EA"),
            ("\u2588\u2588\u2554\u2588\u2588\u2588\u2588\u2554\u2588\u2588\u2551 \u2588\u2588\u2551   \u2588\u2588\u2551    \u2588\u2588\u2551    \u2588\u2588\u2551 \u2588\u2588\u2551   \u2588\u2588\u2551 \u2588\u2588\u2554\u2588\u2588\u2557 \u2588\u2588\u2551", "bold #A855F7"),
            ("\u2588\u2588\u2551\u255a\u2588\u2588\u2554\u255d\u2588\u2588\u2551 \u2588\u2588\u2551   \u2588\u2588\u2551    \u2588\u2588\u2551    \u2588\u2588\u2551 \u2588\u2588\u2551   \u2588\u2588\u2551 \u2588\u2588\u2551\u255a\u2588\u2588\u2557\u2588\u2588\u2551", "bold #C084FC"),
            ("\u2588\u2588\u2551 \u255a\u2550\u255d \u2588\u2588\u2551 \u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d    \u2588\u2588\u2551    \u2588\u2588\u2551 \u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d \u2588\u2588\u2551 \u255a\u2588\u2588\u2588\u2588\u2551", "bold #DDD6FE"),
            ("\u255a\u2550\u255d     \u255a\u2550\u255d  \u255a\u2550\u2550\u2550\u2550\u2550\u255d     \u255a\u2550\u255d    \u255a\u2550\u255d  \u255a\u2550\u2550\u2550\u2550\u2550\u255d  \u255a\u2550\u255d  \u255a\u2550\u2550\u2550\u255d", "#EDE9FE"),
        ]

        console.print()
        for txt, style in LOGO_ROWS:
            console.print(Text("  " + txt, style=style) if txt else Text(""))

        console.print()
        console.print(
            Padding(
                "[bold #A855F7]  Multi-Agent  ·  Content Research  ·  Scriptwriting  ·  SEO  ·  Facebook Growth[/]",
                (0, 0, 1, 2),
            )
        )

        # ── Status table ──────────────────────────────────────────────────────
        fb_token   = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
        fb_ok      = len(fb_token) > 20
        fb_status  = "[bold green]Configured[/]"  if fb_ok else "[bold red]Not set[/]"
        sim_mode   = os.getenv("FACEBOOK_SIMULATION_MODE", "false").lower() == "true"
        sim_label  = "[bold yellow]SIMULATION[/]" if sim_mode else "[bold green]LIVE[/]"
        autonomous = "[bold green]Enabled[/]"      if settings.autonomous_enabled else "[bold dim]Disabled[/]"

        tbl = Table(box=box.ROUNDED, border_style="#3B0764", show_header=False, padding=(0, 2))
        tbl.add_column("Key",   style="bold #9333EA", no_wrap=True)
        tbl.add_column("Value", style="#E9D5FF")

        tbl.add_row("Version",     "[bold white]1.0.0[/]")
        tbl.add_row("Environment", "[bold cyan]development[/]")
        tbl.add_row("Host",        f"[bold white]{settings.host}:{settings.port}[/]")
        tbl.add_row("Dashboard",   f"[bold #60A5FA]http://localhost:{settings.port}/[/]")
        tbl.add_row("API Docs",    f"[bold #60A5FA]http://localhost:{settings.port}/docs[/]")
        tbl.add_row("Facebook",    f"{fb_status}  |  Mode: {sim_label}")
        tbl.add_row("Autonomous",  autonomous)
        tbl.add_row("Started",     f"[dim]{datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}[/]")

        console.print(
            Panel(tbl, title="[bold #7C3AED]  Hyper Motion [/]", border_style="#6D28D9", expand=False)
        )
        console.print(Rule(style="#3B0764"))
        console.print("  [bold #A78BFA]Press [bold white]CTRL+C[/bold white] to stop the server[/]")
        console.print(Rule(style="#3B0764"))
        console.print()

    except Exception:
        # Plain-text fallback — always works
        print("\n=== Hyper Motion 1.0.0 ===")
        print(f"  Dashboard : http://localhost:{settings.port}/")
        print(f"  API Docs  : http://localhost:{settings.port}/docs")
        print("  Press CTRL+C to stop\n")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App Lifespan
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    try:
        from rich.console import Console
        console = Console(highlight=False)
        with console.status("[bold #9333EA]  Initializing agents & services...[/]", spinner="dots"):
            await orchestrator.initialize()
            if settings.autonomous_enabled:
                await scheduler.start()
            # Sync DB routes → live gateway routing table at startup
            try:
                from app.api import db as _api_db, _sync_routes_to_gateway
                await _sync_routes_to_gateway(action="startup")
            except Exception as _re:
                logger.warning("Route startup sync skipped: %s", _re)
        console.print("  [bold green]OK[/bold green] [bold white]All systems online — Hyper Motion is ready.[/]\n")
    except Exception:
        await orchestrator.initialize()
        if settings.autonomous_enabled:
            await scheduler.start()
        try:
            from app.api import _sync_routes_to_gateway
            await _sync_routes_to_gateway(action="startup")
        except Exception:
            pass

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    try:
        from rich.console import Console
        Console(highlight=False).print("\n  [bold #A855F7]Shutting down Hyper Motion...[/]\n")
    except Exception:
        pass

    await scheduler.stop()



# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Hyper Motion",
    description="Multi-Agent Automated Content Research, Fact-Checking, Scriptwriting, SEO & Facebook Growth Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.include_router(router)


@app.get("/")
async def serve_dashboard():
    if DASHBOARD_PATH.exists():
        return FileResponse(
            DASHBOARD_PATH,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"},
        )
    return {"status": "Hyper Motion is online", "docs": "/docs", "health": "/health"}


@app.get("/brain")
async def serve_brain():
    if BRAIN_PATH.exists():
        return FileResponse(
            BRAIN_PATH,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"},
        )
    return {"status": "Brain visualization is online", "docs": "/docs"}


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────
def _free_port(port: int) -> None:
    """Kill any process already listening on *port* so uvicorn can bind cleanly.

    Uses pure Python (subprocess + netstat) — works from any terminal or
    directory, regardless of how the script was invoked.
    """
    import subprocess
    import signal

    try:
        # netstat -ano lists all listening sockets with their owning PID
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            # Match lines like:  TCP  0.0.0.0:8500  ...  LISTENING  1234
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                pid = int(parts[-1])
                if pid == 0:
                    continue
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/F"],
                        capture_output=True, timeout=5
                    )
                    # Brief pause so Windows releases the socket fully
                    import time
                    time.sleep(1.2)
                except Exception:
                    pass
    except Exception:
        pass   # If netstat/taskkill fail, let uvicorn report the real error


def start():
    _free_port(settings.port)   # always clear the port first
    _print_banner()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="warning",   # keep uvicorn quiet — rich handles UI
        access_log=False,
    )



if __name__ == "__main__":
    start()
