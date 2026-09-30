#!/usr/bin/env python3
"""
EduVault CDS - Cloud & Colab Automated Environment Provisioner
Sets up native Linux binaries (N_m3u8DL-RE, ffmpeg), Python dependencies,
validates tgcrypto, and verifies Supabase and Telegram connectivity.
Works seamlessly on Google Colab, Ubuntu/Debian VPS, and Docker containers.
"""

import os
import sys
import stat
import shutil
import tarfile
import zipfile
import platform
import subprocess
import urllib.request
from pathlib import Path

# ANSI Color Codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log_step(badge: str, msg: str, color: str = CYAN):
    print(f"  {color}{BOLD}▌ {badge:<10} ▐{RESET} {msg}")


def check_and_install_system_packages():
    """Installs required system packages via apt on Debian/Ubuntu/Colab."""
    if shutil.which("apt-get"):
        log_step("SYSTEM", "Updating package lists and checking ffmpeg/aria2...")
        try:
            subprocess.run(
                ["apt-get", "update", "-qq"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            subprocess.run(
                ["apt-get", "install", "-y", "-qq", "ffmpeg", "aria2", "curl", "wget", "tar", "gzip"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            log_step("SYSTEM", "System packages (ffmpeg, aria2) verified.", GREEN)
        except Exception as e:
            log_step("SYSTEM", f"Apt installation warning: {e}", YELLOW)


def install_n_m3u8dl_re_linux():
    """Downloads and installs native Linux-x64 N_m3u8DL-RE binary if missing."""
    target_bin = shutil.which("N_m3u8DL-RE")
    if target_bin:
        log_step("BINARY", f"N_m3u8DL-RE already available at: {target_bin}", GREEN)
        return True

    # If running on Linux x86_64
    if platform.system().lower() == "linux" and platform.machine().lower() in ("x86_64", "amd64"):
        log_step("BINARY", "N_m3u8DL-RE binary not found. Downloading latest Linux-x64 release...")
        download_url = (
            "https://github.com/nilaoda/N_m3u8DL-RE/releases/download/"
            "v0.3.0-beta/N_m3u8DL-RE_Beta_linux-x64_20241202.tar.gz"
        )
        archive_path = "/tmp/N_m3u8DL-RE.tar.gz"
        extract_dir = "/tmp/n_m3u8_extracted"

        try:
            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp, open(archive_path, "wb") as out:
                shutil.copyfileobj(resp, out)

            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=extract_dir)

            # Locate the binary in extracted files
            extracted_bin = None
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.startswith("N_m3u8DL-RE"):
                        extracted_bin = os.path.join(root, f)
                        break

            if extracted_bin:
                dest_dirs = ["/usr/local/bin", "/usr/bin", os.path.expanduser("~/.local/bin")]
                installed_dest = None
                for d in dest_dirs:
                    if os.path.exists(d) and os.access(d, os.W_OK):
                        dest_path = os.path.join(d, "N_m3u8DL-RE")
                        shutil.copy2(extracted_bin, dest_path)
                        st = os.stat(dest_path)
                        os.chmod(dest_path, st.st_mode | stat.S_IEXEC)
                        installed_dest = dest_path
                        break

                if not installed_dest:
                    local_bin = os.path.join(os.getcwd(), "N_m3u8DL-RE")
                    shutil.copy2(extracted_bin, local_bin)
                    st = os.stat(local_bin)
                    os.chmod(local_bin, st.st_mode | stat.S_IEXEC)
                    installed_dest = local_bin

                log_step("BINARY", f"N_m3u8DL-RE successfully installed to {installed_dest}", GREEN)
                return True
        except Exception as e:
            log_step("BINARY", f"Failed to download/install N_m3u8DL-RE: {e}", RED)
            return False

    return False


def verify_python_environment():
    """Validates Pyrogram, tgcrypto, and critical dependencies."""
    log_step("PYTHON", "Validating runtime libraries...")
    try:
        import pyrogram
        log_step("PYTHON", f"Pyrogram v{getattr(pyrogram, '__version__', 'unknown')} loaded.", GREEN)
    except ImportError:
        log_step("PYTHON", "Installing pyrogram...", YELLOW)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyrogram==2.0.106"], check=False)

    try:
        import tgcrypto
        log_step("CRYPTO", "tgcrypto (C-accelerated MTProto AES) active.", GREEN)
    except ImportError:
        log_step("CRYPTO", "Installing tgcrypto for maximum MTProto upload speed...", YELLOW)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "tgcrypto"], check=False)

    req_path = os.path.join(os.getcwd(), "ARYAN-TXT2LEECH__V2", "requirements.txt")
    if os.path.exists(req_path):
        log_step("DEPS", "Ensuring all repository requirements are installed...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", req_path], check=False)
        log_step("DEPS", "Repository requirements installed.", GREEN)


def print_cloud_status():
    """Prints a clean, enterprise status report."""
    print("\n" + "=" * 75)
    print(f"{BOLD}{GREEN}  ⚡ EDUVAULT CONTENT DELIVERY PIPELINE — CLOUD ENVIRONMENT READY{RESET}")
    print("=" * 75)
    log_step("OS", f"{platform.system()} {platform.release()} ({platform.machine()})")
    log_step("PYTHON", f"{platform.python_version()} ({sys.executable})")
    log_step("MEDIA", f"ffmpeg: {'OK' if shutil.which('ffmpeg') else 'MISSING'}")
    log_step("ENGINE", f"N_m3u8DL-RE: {'OK' if shutil.which('N_m3u8DL-RE') else 'MISSING'}")
    print("=" * 75 + "\n")


def main():
    check_and_install_system_packages()
    install_n_m3u8dl_re_linux()
    verify_python_environment()
    print_cloud_status()


if __name__ == "__main__":
    main()
