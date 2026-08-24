#!/usr/bin/env python
"""Sandbox Garbage Collection and Cleanup Utility (TRD Section 23, Section 29.1).

Reaps orphaned sovereign-sandbox containers and sweeps stale temporary workspace directories.
"""

import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging

logger = logging.getLogger("sovereign_workbench.scripts.sandbox_gc")


def reap_orphaned_containers() -> int:
    """Find and terminate any orphaned Docker containers with label app=sovereign-sandbox."""
    print("=" * 60)
    print("SOVEREIGN SANDBOX CONTAINER GARBAGE COLLECTION")
    print("=" * 60)

    try:
        res = subprocess.run(
            ["docker", "ps", "-a", "--filter", "label=app=sovereign-sandbox", "--format", "{{.ID}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            print(f"Docker command failed: {res.stderr.strip()}")
            return 0

        container_ids = [c.strip() for c in res.stdout.splitlines() if c.strip()]
        if not container_ids:
            print("No orphaned sovereign-sandbox containers found.")
            return 0

        print(f"Found {len(container_ids)} container(s) to reap: {', '.join(container_ids)}")
        for cid in container_ids:
            subprocess.run(["docker", "rm", "-f", cid], capture_output=True, check=False)
            print(f"  - Reaped container {cid}")

        return len(container_ids)

    except Exception as e:
        print(f"Error during container garbage collection: {e}")
        return 0


def cleanup_stale_workspaces(max_age_hours: float = 24.0) -> int:
    """Remove sandbox workspace directories older than max_age_hours."""
    sandbox_dir = Path(settings.paths.data_dir) / "sandbox"
    if not sandbox_dir.exists():
        return 0

    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    removed = 0

    for item in sandbox_dir.iterdir():
        if item.is_dir():
            try:
                mtime = item.stat().st_mtime
                if mtime < cutoff:
                    shutil.rmtree(item, ignore_errors=True)
                    print(f"  - Removed stale workspace: {item.name}")
                    removed += 1
            except Exception as e:
                logger.warning(f"Failed to inspect/remove workspace {item}: {e}")

    return removed


def main():
    setup_logging()
    reaped = reap_orphaned_containers()
    stale_dirs = cleanup_stale_workspaces()
    print(f"\nGC Summary: {reaped} containers reaped, {stale_dirs} stale workspace directories removed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
