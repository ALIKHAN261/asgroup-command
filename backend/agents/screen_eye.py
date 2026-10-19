"""Screen Eye — snapshot history of your PC screen.

The LIVE view is streamed by /api/screen/live (see main.py). This agent
keeps timestamped snapshots every 10 minutes as history. Read-only:
it never clicks, types, or controls anything.
"""
import time, pathlib
from agents import register

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "screenshots"
LATEST = DATA / "latest.png"

def _grab():
    from PIL import ImageGrab
    return ImageGrab.grab()

@register("screen_eye", interval=600)
def screen_eye(ctx):
    try:
        img = _grab()
    except Exception as e:
        # Headless servers have no screen — not an error, just idle.
        return f"no display available ({type(e).__name__})"
    DATA.mkdir(parents=True, exist_ok=True)
    # Downscale for fast phone viewing.
    img.thumbnail((960, 960))
    img.save(LATEST)
    # Keep a short history, prune the rest.
    stamp = DATA / f"{int(time.time())}.png"
    img.save(stamp)
    for old in sorted(DATA.glob("*.png"), reverse=True)[25:]:
        if old.name != "latest.png":
            old.unlink(missing_ok=True)
    return "screenshot captured — view it in the dashboard"

def latest_path():
    return LATEST if LATEST.exists() else None
