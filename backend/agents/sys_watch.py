"""Sys Watch — this PC's health. Read-only, never changes anything."""
import shutil, os
from agents import register

@register("sys_watch", interval=600)
def sys_watch(ctx):
    du = shutil.disk_usage(os.path.expanduser("~"))
    free_gb = du.free / 1e9
    pct = 100 * du.free / du.total
    load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0
    if pct < 10:
        ctx.queue_approval("Disk space low",
                           f"Only {free_gb:.1f} GB free ({pct:.0f}%). Free up space.")
        return f"disk LOW: {free_gb:.1f} GB free — queued for review"
    return f"disk {free_gb:.0f} GB free · load {load:.1f}"
