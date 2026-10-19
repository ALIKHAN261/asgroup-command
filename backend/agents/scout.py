"""Scout — client hunting. DRAFTS outreach, never sends.

Reads niches from data/niches.txt (one per line). Each run drafts one
outreach message for the next niche in rotation and queues it for your
daily approval. Sending happens only when YOU approve.
"""
import pathlib
from agents import register

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
NICHES_FILE = DATA / "niches.txt"
STATE_FILE = DATA / "scout_state.txt"
DEFAULT_NICHES = ["ecommerce stores", "real estate agents", "restaurants",
                  "clinics", "coaches"]

def _niches():
    if NICHES_FILE.exists():
        lines = [l.strip() for l in NICHES_FILE.read_text().splitlines()
                 if l.strip()]
        if lines:
            return lines
    DATA.mkdir(exist_ok=True)
    NICHES_FILE.write_text("\n".join(DEFAULT_NICHES) + "\n")
    return DEFAULT_NICHES

@register("scout", interval=3600)
def scout(ctx):
    niches = _niches()
    idx = int(STATE_FILE.read_text().strip()) if STATE_FILE.exists() else 0
    niche = niches[idx % len(niches)]
    STATE_FILE.write_text(str(idx + 1))
    draft = (
        f"Hi, I help {niche} get more customers with short-form video and "
        f"simple websites. I made a free 60-second audit of what I'd fix "
        f"first — want me to send it over?\n\n— Ali Raza, AS GROUP")
    ctx.queue_approval(f"Outreach draft — {niche}", draft)
    return f"drafted outreach for '{niche}' — waiting your approval"
