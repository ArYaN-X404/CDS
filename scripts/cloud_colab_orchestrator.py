#!/usr/bin/env python3
"""
EduVault CDS - Local Cloud Orchestrator & Live Monitoring Console
Run locally to dispatch batch manifests to the Cloud Worker (Google Colab / Linux VPS)
and view live real-time telemetry, speeds, and ETA on your local terminal.
"""

import os
import sys
import time
import json
import argparse
import webbrowser
from typing import Optional

# Setup import path
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
for candidate in [
    repo_root,
    os.path.join(repo_root, "ARYAN-TXT2LEECH__V2"),
    os.getcwd(),
    os.path.join(os.getcwd(), "ARYAN-TXT2LEECH__V2"),
]:
    if os.path.isdir(os.path.join(candidate, "engine")) and candidate not in sys.path:
        sys.path.insert(0, candidate)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.box import ROUNDED, DOUBLE_EDGE
from engine.cloud_bridge import CloudBridge

console = Console(highlight=False)

COLAB_NOTEBOOK_URL = (
    "https://colab.research.google.com/github/ArYaN-X404/CDS/blob/main/notebooks/CDS_Colab_Ingest.ipynb"
)


def render_dashboard(telemetry: Optional[dict]) -> Panel:
    """Renders the enterprise Rich monitoring panel based on live telemetry."""
    if not telemetry:
        table = Table.grid(padding=(0, 2))
        table.add_column("Key", style="bold yellow", justify="right")
        table.add_column("Val", style="bold white")
        table.add_row("☁️ Cloud Worker", "[yellow]WAITING FOR WORKER BEACON...[/yellow]")
        table.add_row("🔗 Colab Link", f"[underline cyan]{COLAB_NOTEBOOK_URL}[/underline cyan]")
        table.add_row("💡 Note", "Launch CDS_Colab_Ingest.ipynb in Colab or run 'python scripts/cloud_worker.py'")

        return Panel(
            table,
            title="[bold bright_white] ☁️ CLOUD ORCHESTRATION CONSOLE [/bold bright_white]",
            title_align="center",
            border_style="yellow",
            box=ROUNDED,
            padding=(1, 3)
        )

    is_alive = telemetry.get("is_alive", False)
    status_color = "bright_green" if is_alive else "bright_red"
    status_label = "🟢 ONLINE • STREAMING (2.5 Gbps)" if is_alive else f"🔴 OFFLINE ({telemetry.get('seconds_since_heartbeat', 0)}s ago)"

    stage = telemetry.get("stage", "IDLE")
    speed = telemetry.get("speed_mbps", 0.0)
    perc = telemetry.get("percentage", 0.0)
    task_idx = telemetry.get("task_idx", 0)
    total_tasks = telemetry.get("total_tasks", 0)
    title = telemetry.get("title", "No active task")
    active_bot = telemetry.get("active_bot", "Primary Bot")

    # Progress Bar formatting
    bar_width = 24
    filled = int((perc / 100) * bar_width) if perc else 0
    prog_bar = "█" * filled + "░" * max(0, bar_width - filled)

    table = Table.grid(padding=(0, 2))
    table.add_column("Icon", style="bold cyan", justify="right")
    table.add_column("Key", style="bold white", justify="left")
    table.add_column("Val", style="bright_white", justify="left")

    table.add_row("☁️", "Cloud Worker Status", f"[{status_color}]{status_label}[/{status_color}]")
    table.add_row("📦", "Active Batch", f"[yellow]{telemetry.get('batch_id', 'Unknown')}[/yellow]")
    table.add_row("📖", "Current Lecture", f"[bold bright_white]{title}[/bold bright_white]")
    table.add_row("⚡", "Stage / Operation", f"[bold cyan]{stage}[/bold cyan]")
    table.add_row("🚀", "Cloud Line Rate", f"[bold bright_green]{speed:.1f} MB/s[/bold bright_green]")
    table.add_row("📊", "Task Progress", f"[bright_yellow]{prog_bar}  {perc:.1f}%[/bright_yellow]  (#{task_idx}/{total_tasks})")
    table.add_row("🤖", "Worker Instance", f"[dim]{active_bot}[/dim]")

    if telemetry.get("error_msg"):
        table.add_row("⚠️", "Alert", f"[red]{telemetry['error_msg']}[/red]")

    return Panel(
        table,
        title="[bold bright_white] ☁️ CLOUD ORCHESTRATION CONSOLE • REAL-TIME TELEMETRY [/bold bright_white]",
        title_align="center",
        border_style="bright_green" if is_alive else "bright_yellow",
        box=ROUNDED,
        padding=(1, 3)
    )


def monitor_loop(bridge: CloudBridge):
    """
    Live terminal monitoring loop — TTY-aware.
    - Real TTY (Windows Terminal / Linux): Rich Live in-place redraw.
    - Non-TTY (raw PowerShell, CI, piped): simple line-per-update every 5s. No spam.
    """
    console.print("\n[bold cyan]⚡ Connecting to EduVault Cloud Bridge...[/bold cyan]")
    is_tty = sys.stdout.isatty()

    if is_tty:
        with Live(render_dashboard(None), refresh_per_second=1, console=console, transient=False) as live:
            try:
                while True:
                    telemetry = bridge.fetch_telemetry()
                    live.update(render_dashboard(telemetry))
                    if telemetry and telemetry.get("stage") == "COMPLETE":
                        time.sleep(2)
                        break
                    time.sleep(2)
            except KeyboardInterrupt:
                pass
    else:
        # Non-TTY fallback: one status line per poll, no redraw spam
        console.print("[dim yellow]ℹ️  Non-TTY terminal (PowerShell). Line-per-update mode (5s interval).[/dim yellow]")
        console.print(f"[dim]   Colab: {COLAB_NOTEBOOK_URL}[/dim]\n")
        last_line = None
        try:
            while True:
                telemetry = bridge.fetch_telemetry()
                if telemetry:
                    stage = telemetry.get("stage", "IDLE")
                    perc = telemetry.get("percentage", 0.0)
                    speed = telemetry.get("speed_mbps", 0.0)
                    title = telemetry.get("title", "")[:60]
                    alive = "🟢" if telemetry.get("is_alive") else "🔴"
                    line = f"{alive} [{stage}] {perc:.1f}% @ {speed:.1f} MB/s | {title}"
                    if line != last_line:
                        console.print(f"[{time.strftime('%H:%M:%S')}] {line}")
                        last_line = line
                    if stage == "COMPLETE":
                        break
                else:
                    console.print(f"[{time.strftime('%H:%M:%S')}] ⏳ Waiting for Colab beacon... (is Step 5 running?)")
                time.sleep(5)
        except KeyboardInterrupt:
            pass



def load_batch_manifest(file_path: str) -> dict:
    """Loads a batch from either a JSON manifest or a standard TXT2LEECH TXT file."""
    if file_path.lower().endswith(".json"):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Parse TXT batch file (Title:URL or Title \n URL)
    links = []
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line and not line.startswith("http"):
                parts = line.split(":", 1)
                t, u = parts[0].strip(), parts[1].strip()
                if u.startswith("//"):
                    u = "https:" + u
                links.append({"title": t, "url": u})
            elif line.startswith("http://") or line.startswith("https://"):
                links.append({"title": f"Lecture {len(links)+1}", "url": line})

    return {
        "batch_id": f"batch_{int(time.time())}",
        "batch_name": base_name,
        "links": links
    }


def main():
    parser = argparse.ArgumentParser(description="EduVault CDS Local Cloud Orchestrator")
    parser.add_argument("--manifest", type=str, help="Path to batch JSON or TXT manifest to dispatch to cloud")
    parser.add_argument("--open-colab", action="store_true", help="Automatically open Google Colab in default browser")
    parser.add_argument("--monitor-only", action="store_true", help="Attach to live cloud telemetry without dispatching")
    args = parser.parse_args()

    bridge = CloudBridge()
    manifest_to_dispatch = None

    if args.manifest and not args.monitor_only:
        is_placeholder = any(p in args.manifest.lower() for p in ["path\\to", "path/to", "batch.json", "batch.txt"]) and not os.path.exists(args.manifest)
        if is_placeholder or not os.path.exists(args.manifest):
            console.print(f"[bold yellow]⚠️ Manifest '{args.manifest}' not found. Searching for local batches...[/bold yellow]")
            candidates = []
            for s_dir in [
                os.getcwd(),
                ".",
                "..",
                os.path.join(os.getcwd(), "ARYAN-TXT2LEECH__V2"),
                os.path.join(repo_root, "ARYAN-TXT2LEECH__V2"),
                r"R:\ARYAN-TXT2LEECH__V2",
                r"D:\Projects\Content Delivery System (CDS)\ARYAN-TXT2LEECH__V2",
            ]:
                if os.path.exists(s_dir):
                    try:
                        for f in os.listdir(s_dir):
                            f_low = f.lower()
                            if (f_low.endswith(".json") or f_low.endswith(".txt")) and not any(
                                f_low.startswith(p) for p in ["cookie", "package", "cloud_", "checkpoint_", "requirements", "latest_"]
                            ):
                                full_p = os.path.join(s_dir, f)
                                if os.path.isfile(full_p):
                                    candidates.append(os.path.abspath(full_p))
                    except Exception:
                        pass
            candidates = list(dict.fromkeys(candidates))

            if candidates:
                console.print(f"[cyan]Found {len(candidates)} available batch file(s):[/cyan]")
                for idx, c in enumerate(candidates[:5], 1):
                    console.print(f"  [{idx}] {os.path.basename(c)}")
                manifest_to_dispatch = candidates[0]
                console.print(f"[bold green]Auto-dispatching: {os.path.basename(manifest_to_dispatch)}[/bold green]\n")
            else:
                console.print("[dim]No local batch files found. Cloud worker will await jobs via Colab or Telegram /upload.[/dim]\n")
        else:
            manifest_to_dispatch = args.manifest

    if manifest_to_dispatch:
        try:
            manifest_data = load_batch_manifest(manifest_to_dispatch)
            b_name = manifest_data.get("batch_name", os.path.basename(manifest_to_dispatch))
            total_items = len(manifest_data.get("links", []))
            console.print(f"[bold cyan]📤 Dispatching batch job '{b_name}' ({total_items} items) to Cloud Worker...[/bold cyan]")
            bridge.dispatch_job(manifest_data)
            console.print("[bold green]✅ Job successfully dispatched to Cloud Control Plane![/bold green]\n")
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not parse manifest: {e}[/yellow]\n")

    if args.open_colab:
        console.print(f"[bold cyan]🌐 Opening Google Colab Notebook in browser...[/bold cyan]")
        try:
            webbrowser.open(COLAB_NOTEBOOK_URL)
        except Exception as e:
            console.print(f"[yellow]Could not open browser automatically: {e}[/yellow]")

    # Start live terminal monitor
    monitor_loop(bridge)


if __name__ == "__main__":
    main()
