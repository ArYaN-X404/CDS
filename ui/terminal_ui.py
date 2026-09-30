"""
EduVault CDS Pipeline - Enterprise Terminal UI Engine
Powered by Rich with full Windows UTF-8 Terminal Support, Live Spinners, and Dynamic Progress Bars.
"""

import os
import sys
import time
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

# Windows Console UTF-8 Force Configuration
def _configure_utf8():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

_configure_utf8()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED, DOUBLE_EDGE, HEAVY, SIMPLE
from rich.traceback import install as install_rich_traceback
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    TaskID
)

# Initialize console
console = Console(highlight=False, legacy_windows=False)

# Install rich traceback formatting for enterprise crash reports
try:
    install_rich_traceback(console=console, show_locals=False, max_frames=8, word_wrap=True)
except Exception:
    pass

_BANNER_ASCII = (
    "  ███████╗██████╗ ██╗   ██╗██╗   ██╗ █████╗ ██╗   ████████╗\n"
    "  ██╔════╝██╔══██╗██║   ██║██║   ██║██╔══██╗██║   ╚══██╔══╝\n"
    "  █████╗  ██║  ██║██║   ██║██║   ██║███████║██║      ██║   \n"
    "  ██╔══╝  ██║  ██║██║   ██║╚██╗ ██╔╝██╔══██║██║      ██║   \n"
    "  ███████╗██████╔╝╚██████╔╝ ╚████╔╝ ██║  ██║███████╗ ██║   \n"
    "  ╚══════╝╚═════╝  ╚═════╝   ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═╝   "
)



class TerminalUIEngine:
    """Central state and interactive rendering manager for CDS Terminal."""
    
    def __init__(self, console_inst: Console):
        self.console = console_inst
        self._status = None
        self._upload_progress: Optional[Progress] = None
        self._upload_task_id: Optional[TaskID] = None
        self._upload_filename: str = ""
        self._upload_total: int = 0
        self._upload_tasks: Dict[str, TaskID] = {}
        self._upload_totals: Dict[str, int] = {}
        # Live Download Progress tracking
        self._download_progress: Optional[Progress] = None
        self._download_task_id: Optional[TaskID] = None
        self._download_filename: str = ""
        self._download_total: int = 0
        self._download_tasks: Dict[str, TaskID] = {}
        self._download_totals: Dict[str, int] = {}

    # -------------------------------------------------------------------------
    # Live Status Spinners
    # -------------------------------------------------------------------------
    @contextmanager
    def spinner(self, message: str, spinner_name: str = "dots"):
        """Context manager for live animated status spinners."""
        status = self.console.status(f"[bold cyan]{message}[/bold cyan]", spinner=spinner_name)
        status.start()
        try:
            yield status
        finally:
            try:
                status.stop()
            except Exception:
                pass

    def start_spinner(self, message: str, spinner_name: str = "dots"):
        """Starts a persistent spinner until explicitly stopped."""
        self.stop_spinner()
        try:
            self._status = self.console.status(f"[bold cyan]{message}[/bold cyan]", spinner=spinner_name)
            self._status.start()
        except Exception:
            self._status = None

    def update_spinner(self, message: str):
        """Updates the message on the currently active spinner."""
        if self._status:
            try:
                self._status.update(f"[bold cyan]{message}[/bold cyan]")
            except Exception:
                pass

    def stop_spinner(self):
        """Stops and clears any active spinner."""
        if self._status:
            try:
                self._status.stop()
            except Exception:
                pass
            self._status = None

    # -------------------------------------------------------------------------
    # Live Download Progress Bar
    # -------------------------------------------------------------------------
    def start_download_progress(self, filename: str, total_bytes: int):
        """Initializes a live progress bar for media downloading."""
        self._download_filename = filename
        self._download_total = total_bytes
        self._download_totals[filename] = total_bytes
        try:
            if self._download_progress is None:
                self._download_progress = Progress(
                    SpinnerColumn("dots", style="bright_yellow"),
                    TextColumn("  [bold bright_yellow]▌ DOWNLOAD   ▐[/bold bright_yellow] [bold white]{task.fields[filename]}[/bold white]"),
                    BarColumn(bar_width=22, style="yellow", complete_style="bright_yellow", finished_style="bold yellow"),
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    "•",
                    DownloadColumn(),
                    "•",
                    TransferSpeedColumn(),
                    "•",
                    TimeElapsedColumn(),
                    "•",
                    TimeRemainingColumn(),
                    console=self.console,
                    transient=True,
                )
                self._download_progress.start()

            short_name = filename[:32] + ("..." if len(filename) > 32 else "")
            task_id = self._download_progress.add_task(
                "download",
                total=total_bytes,
                filename=short_name
            )
            self._download_tasks[filename] = task_id
            self._download_task_id = task_id
        except Exception:
            pass

    def update_download_progress(self, current_bytes: int, total_bytes: Optional[int] = None, filename: Optional[str] = None):
        """Updates the live download progress with current transferred bytes."""
        if self._download_progress:
            try:
                task_id = None
                if filename and filename in self._download_tasks:
                    task_id = self._download_tasks[filename]
                elif self._download_task_id is not None:
                    task_id = self._download_task_id
                elif self._download_tasks:
                    task_id = list(self._download_tasks.values())[-1]

                if task_id is not None:
                    tot = total_bytes if total_bytes and total_bytes > 0 else self._download_totals.get(filename or "", self._download_total)
                    self._download_progress.update(task_id, completed=current_bytes, total=tot)
            except Exception:
                pass

    def stop_download_progress(self, filename: Optional[str] = None):
        """Stops the live download progress bar for a file, or all if unspecified."""
        if self._download_progress:
            try:
                if filename and filename in self._download_tasks:
                    task_id = self._download_tasks.pop(filename, None)
                    if task_id is not None:
                        self._download_progress.remove_task(task_id)
                    self._download_totals.pop(filename, None)
                else:
                    self._download_tasks.clear()
                    self._download_totals.clear()

                if not self._download_tasks:
                    self._download_progress.stop()
                    self._download_progress = None
                    self._download_task_id = None
            except Exception:
                self._download_progress = None
                self._download_task_id = None
                self._download_tasks.clear()

    # -------------------------------------------------------------------------
    # Live Upload Progress Bar
    # -------------------------------------------------------------------------
    def start_upload_progress(self, filename: str, total_bytes: int):
        """Initializes a live progress bar for file uploading. Supports concurrent uploads."""
        self._upload_filename = filename
        self._upload_total = total_bytes
        self._upload_totals[filename] = total_bytes
        try:
            if self._upload_progress is None:
                self._upload_progress = Progress(
                    SpinnerColumn("dots", style="bright_green"),
                    TextColumn("  [bold bright_green]▌ UPLOAD     ▐[/bold bright_green] [bold white]{task.fields[filename]}[/bold white]"),
                    BarColumn(bar_width=22, style="cyan", complete_style="bright_green", finished_style="bold green"),
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    "•",
                    DownloadColumn(),
                    "•",
                    TransferSpeedColumn(),
                    "•",
                    TimeElapsedColumn(),
                    "•",
                    TimeRemainingColumn(),
                    console=self.console,
                    transient=True,
                )
                self._upload_progress.start()

            short_name = filename[:32] + ("..." if len(filename) > 32 else "")
            task_id = self._upload_progress.add_task(
                "upload",
                total=total_bytes,
                filename=short_name
            )
            self._upload_tasks[filename] = task_id
            self._upload_task_id = task_id
        except Exception:
            pass

    def update_upload_progress(self, current_bytes: int, total_bytes: Optional[int] = None, filename: Optional[str] = None):
        """Updates the live upload progress with current transferred bytes."""
        if self._upload_progress:
            try:
                task_id = None
                if filename and filename in self._upload_tasks:
                    task_id = self._upload_tasks[filename]
                elif self._upload_task_id is not None:
                    task_id = self._upload_task_id
                elif self._upload_tasks:
                    task_id = list(self._upload_tasks.values())[-1]

                if task_id is not None:
                    tot = total_bytes if total_bytes and total_bytes > 0 else self._upload_totals.get(filename or "", self._upload_total)
                    self._upload_progress.update(task_id, completed=current_bytes, total=tot)
            except Exception:
                pass

    def stop_upload_progress(self, filename: Optional[str] = None):
        """Stops the live upload progress bar for a file, or all if unspecified."""
        if self._upload_progress:
            try:
                if filename and filename in self._upload_tasks:
                    task_id = self._upload_tasks.pop(filename, None)
                    if task_id is not None:
                        self._upload_progress.remove_task(task_id)
                    self._upload_totals.pop(filename, None)
                else:
                    self._upload_tasks.clear()
                    self._upload_totals.clear()

                if not self._upload_tasks:
                    self._upload_progress.stop()
                    self._upload_progress = None
                    self._upload_task_id = None
            except Exception:
                self._upload_progress = None
                self._upload_task_id = None
                self._upload_tasks.clear()


# Global engine instance
ui = TerminalUIEngine(console)


# -----------------------------------------------------------------------------
# Functional API (100% Backward Compatible)
# -----------------------------------------------------------------------------

def status_spinner(message: str, spinner_name: str = "dots"):
    """Context manager for live spinner."""
    return ui.spinner(message, spinner_name)

def start_status(message: str):
    ui.start_spinner(message)

def update_status(message: str):
    ui.update_spinner(message)

def stop_status():
    ui.stop_spinner()

def start_download_progress(filename: str, total_bytes: int):
    ui.start_download_progress(filename, total_bytes)

def update_download_progress(current_bytes: int, total_bytes: Optional[int] = None, filename: Optional[str] = None):
    ui.update_download_progress(current_bytes, total_bytes, filename)

def stop_download_progress(filename: Optional[str] = None):
    ui.stop_download_progress(filename)

def start_upload_progress(filename: str, total_bytes: int):
    ui.start_upload_progress(filename, total_bytes)

def update_upload_progress(current_bytes: int, total_bytes: Optional[int] = None, filename: Optional[str] = None):
    ui.update_upload_progress(current_bytes, total_bytes, filename)

def stop_upload_progress(filename: Optional[str] = None):
    ui.stop_upload_progress(filename)


def print_startup_banner():
    """Prints a high-tech, professional startup banner."""
    try:
        import pyfiglet
        ascii_art = pyfiglet.figlet_format("EDUVAULT", font="slant")
        content = Text(ascii_art, style="bold bright_cyan")
    except Exception:
        content = Text(_BANNER_ASCII + "\n\n", style="bold bright_cyan")
    content.append("⚡ EDUVAULT CONTENT DELIVERY PIPELINE\n", style="bold bright_cyan")
    content.append("Enterprise Automated Ingestion & Cloud Transcoding Engine • v3.0\n\n", style="bright_white")
    content.append("  🟢 Cloud Database : ", style="bold white")
    content.append("Supabase Cloud Connected (PostgreSQL)\n", style="bold green")
    content.append("  🟢 Storage Target : ", style="bold white")
    content.append("Telegram Storage Channel (-1004460495677)\n", style="bold yellow")
    content.append("  🚀 Transcoding    : ", style="bold white")
    content.append("Adaptive Multi-Quality (1080p / 720p / 480p)\n", style="bold magenta")
    content.append("  ⚡ Media Engine   : ", style="bold white")
    content.append("N_m3u8DL-RE + Pyrogram 4-Worker MTProto Streamer", style="bold cyan")

    banner = Panel(
        content,
        box=ROUNDED,
        border_style="bright_blue",
        padding=(1, 3),
        title="[bold bright_white] SYSTEM READY [/bold bright_white]",
        title_align="center",
    )
    console.print(banner)


def print_batch_overview(batch_id: str, batch_name: str, total_items: int, start_index: int, qualities: list, db_count: int = 0, pipeline_mode: str = None):
    """Prints a clean summary card for the batch that just started."""
    table = Table.grid(padding=(0, 2))
    table.add_column("Key", style="bold bright_cyan", justify="right")
    table.add_column("Value", style="bright_white")

    q_str = " + ".join([f"{q}p" if not str(q).endswith("p") else q for q in (qualities or ['720p'])])

    table.add_row("📦 Batch ID", f"[yellow]{batch_id}[/yellow]")
    table.add_row("📚 Batch Name", f"[bold white]{batch_name}[/bold white]")
    table.add_row("📊 Total Lectures", f"{total_items} items")
    table.add_row("💾 Cloud Database", f"[green]{db_count} items already completed[/green] ({total_items - db_count} remaining)")
    table.add_row("⏩ Start Index", f"[bold green]#{start_index}[/bold green] of {total_items}")
    table.add_row("🎬 Quality Profile", f"[bold magenta]{q_str}[/bold magenta]")
    if pipeline_mode:
        table.add_row("⚡ Ingestion Mode", f"[bold cyan]{pipeline_mode}[/bold cyan]")

    panel = Panel(
        table,
        box=ROUNDED,
        border_style="cyan",
        title="[bold bright_white] ACTIVE BATCH SPECIFICATIONS [/bold bright_white]",
        title_align="center",
        padding=(1, 2)
    )
    console.print(panel)


def print_task_header(count: int, total: int, title: str, subject: str = None, topic: str = None, extra_info: dict = None):
    """Prints an enterprise-grade, clean task header without heavy panel boxing."""
    perc = int((count / total) * 100) if total else 0
    bar_width = 16
    filled = int((perc / 100) * bar_width)
    prog_bar = "█" * filled + "░" * max(0, bar_width - filled)

    console.print()
    console.rule(
        f"[bold bright_cyan]TASK #{count:03d} / {total:03d}[/bold bright_cyan]  [dim]•[/dim]  [bold bright_yellow]{prog_bar} {perc:>3d}%[/bold bright_yellow]",
        style="bright_blue"
    )

    # Clean 2-line metadata output
    console.print(f"  [bold bright_white]📖  {title}[/bold bright_white]")

    meta_parts = []
    if subject:
        meta_parts.append(f"[dim]Subject:[/dim] [bright_yellow]{subject}[/bright_yellow]")
    if topic:
        meta_parts.append(f"[dim]Topic:[/dim] [bright_blue]{topic}[/bright_blue]")
    if extra_info:
        for k, v in extra_info.items():
            meta_parts.append(f"[dim]{k}:[/dim] {v}")

    if meta_parts:
        console.print(f"  [dim]│[/dim] " + "  [dim]•[/dim]  ".join(meta_parts))


def log_step(badge: str, msg: str, color: str = "bright_cyan"):
    """Prints a standardized color-coded pill badge with uniform column alignment."""
    badge_str = f"▌ {badge:<9} ▐"
    console.print(f"  [{color}]{badge_str}[/{color}] {msg}")


def log_resolve(msg: str):
    log_step("RESOLVE", msg, "bold cyan")


def log_download(quality: str, msg: str):
    q_label = f"{quality}p" if not str(quality).endswith("p") else quality
    log_step("DOWNLOAD", f"[{q_label}] {msg}", "bold bright_yellow")


def log_upload(quality: str, msg: str):
    q_label = f"{quality}p" if not str(quality).endswith("p") else quality
    log_step("UPLOAD", f"[{q_label}] {msg}", "bold bright_green")


def log_cloud_sync(lecture_id: str, quality: str, tg_msg_id: int):
    q_label = f"{quality}p" if not str(quality).endswith("p") else quality
    log_step("DB SYNC", f"Recorded {q_label} in Supabase & local DB (Msg ID: #{tg_msg_id})", "bold bright_magenta")


def log_skip(msg: str):
    log_step("SKIP", msg, "dim cyan")


def log_success(msg: str):
    log_step("SUCCESS", msg, "bold green")


def log_warn(msg: str):
    log_step("WARNING", msg, "bold yellow")


def log_error(msg: str):
    log_step("FAILED", msg, "bold red")


def log_pool(msg: str):
    log_step("POOL", msg, "bold bright_yellow")


def log_info(msg: str):
    log_step("INFO", msg, "bright_cyan")


def print_batch_summary(total: int, succeeded: int, failed: int, mapping_path: str = None):
    """Prints a clean, professional summary card upon batch completion."""
    console.print()
    if failed == 0 and total > 0:
        content = Text()
        content.append("🎉 BATCH INGESTION COMPLETE\n\n", style="bold bright_white")
        content.append(f"  ✅  {succeeded} / {total} lectures successfully ingested\n", style="bold green")
        content.append(f"  📊  0 failures • 100.0% success rate\n", style="bold bright_cyan")
        if mapping_path:
            content.append(f"  📁  Asset mapping: {mapping_path}\n", style="dim white")
        content.append("  ☁️  All assets live on EduVault Web & Supabase Cloud", style="bold bright_magenta")

        console.print(Panel(
            content,
            title="[bold bright_white] SYSTEM STATUS [/bold bright_white]",
            title_align="center",
            border_style="bright_green",
            box=ROUNDED,
            padding=(1, 3)
        ))
    else:
        table = Table(box=ROUNDED, border_style="green", padding=(0, 2))
        table.add_column("Status Metric", style="bold white")
        table.add_column("Count", justify="right", style="bold")
        table.add_column("Percentage", justify="right")

        succ_perc = f"{(succeeded / total * 100):.1f}%" if total else "0%"
        fail_perc = f"{(failed / total * 100):.1f}%" if total else "0%"

        table.add_row("✅ Total Completed", f"[green]{succeeded}[/green]", f"[green]{succ_perc}[/green]")
        if failed > 0:
            table.add_row("❌ Failed Tasks", f"[red]{failed}[/red]", f"[red]{fail_perc}[/red]")
        else:
            table.add_row("❌ Failed Tasks", "[dim]0[/dim]", "[dim]0.0%[/dim]")
        table.add_row("📦 Total Processed", f"{total}", "100.0%")

        console.print(Panel(
            table,
            title="[bold bright_white] BATCH INGESTION SUMMARY [/bold bright_white]",
            title_align="center",
            border_style="bright_yellow" if failed > 0 else "bright_green",
            padding=(1, 2)
        ))

        if mapping_path:
            console.print(f"  📊 [bold cyan]Asset Mapping JSON:[/bold cyan] [underline]{mapping_path}[/underline]")
            console.print(f"  ☁️  [bold magenta]All assets are live on EduVault Web & Supabase Cloud.[/bold magenta]")

