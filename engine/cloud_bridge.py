"""
EduVault CDS - Cloud Bridge & Telemetry Control Plane
Enables bidirectional communication, state synchronization, and live telemetry
between the remote Cloud Worker (Google Colab / Linux VPS) and the Local Monitoring Console.
"""

import os
import sys
import json
import time
import logging
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)

# Constants
DEFAULT_TELEMETRY_FILE = "cloud_telemetry.json"
DEFAULT_JOB_FILE = "cloud_job.json"


class CloudBridge:
    """Manages state, job dispatch, and real-time telemetry streaming."""

    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None, local_state_dir: str = "."):
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL", "https://fytemrmebqovsclumwqu.supabase.co")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.local_state_dir = local_state_dir
        self.telemetry_path = os.path.join(local_state_dir, DEFAULT_TELEMETRY_FILE)
        self.job_path = os.path.join(local_state_dir, DEFAULT_JOB_FILE)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }

    # -------------------------------------------------------------------------
    # Telemetry Transmission (Cloud Worker -> Local Monitor)
    # -------------------------------------------------------------------------
    def publish_telemetry(
        self,
        batch_id: str,
        task_idx: int,
        total_tasks: int,
        title: str,
        stage: str,
        speed_mbps: float = 0.0,
        percentage: float = 0.0,
        eta_seconds: int = 0,
        active_bot: str = "bot",
        error_msg: Optional[str] = None
    ) -> bool:
        """Pushes a live telemetry frame from the Cloud Worker."""
        payload = {
            "batch_id": batch_id,
            "task_idx": task_idx,
            "total_tasks": total_tasks,
            "title": title,
            "stage": stage,  # RESOLVING, DOWNLOADING, UPLOADING, SYNCING, IDLE, COMPLETE
            "speed_mbps": round(speed_mbps, 2),
            "percentage": round(percentage, 1),
            "eta_seconds": eta_seconds,
            "active_bot": active_bot,
            "error_msg": error_msg,
            "heartbeat": time.time(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # 1. Local / Shared File State
        try:
            with open(self.telemetry_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            log.debug(f"Failed to write local telemetry: {e}")

        # 2. Supabase Cloud Sync (if configured)
        if self.supabase_url and self.supabase_key:
            try:
                import requests
                url = f"{self.supabase_url}/rest/v1/batches?id=eq.{batch_id}"
                # Update batch metadata with live progress
                patch_payload = {
                    "is_active": True,
                    "title": title
                }
                requests.patch(url, json=patch_payload, headers=self._get_headers(), timeout=3)
            except Exception:
                pass

        return True

    def fetch_telemetry(self) -> Optional[Dict[str, Any]]:
        """Reads the latest telemetry frame for the Local Monitor."""
        if os.path.exists(self.telemetry_path):
            try:
                with open(self.telemetry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Check if telemetry is alive (heartbeat within 30s)
                hb = data.get("heartbeat", 0)
                data["is_alive"] = (time.time() - hb) < 30
                data["seconds_since_heartbeat"] = round(time.time() - hb, 1)
                return data
            except Exception:
                return None
        return None

    # -------------------------------------------------------------------------
    # Job Dispatch (Local Monitor -> Cloud Worker)
    # -------------------------------------------------------------------------
    def dispatch_job(self, manifest_data: Dict[str, Any]) -> bool:
        """Dispatches a new batch manifest job to the Cloud Worker."""
        job_payload = {
            "dispatched_at": time.time(),
            "status": "QUEUED",
            "manifest": manifest_data
        }
        try:
            with open(self.job_path, "w", encoding="utf-8") as f:
                json.dump(job_payload, f, indent=2)
            return True
        except Exception as e:
            log.error(f"Failed to dispatch job: {e}")
            return False

    def fetch_job(self) -> Optional[Dict[str, Any]]:
        """Cloud worker pulls the active job manifest."""
        if os.path.exists(self.job_path):
            try:
                with open(self.job_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def mark_job_status(self, status: str):
        """Updates the status of the current job (e.g. RUNNING, PAUSED, FINISHED)."""
        job = self.fetch_job()
        if job:
            job["status"] = status
            job["updated_at"] = time.time()
            try:
                with open(self.job_path, "w", encoding="utf-8") as f:
                    json.dump(job, f, indent=2)
            except Exception:
                pass
