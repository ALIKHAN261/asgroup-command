"""Tube Watch — monitors your web properties. Read-only, never changes anything."""
import urllib.request
from agents import register

SITES = {
    "AR Studio": "https://ytcm-public.vercel.app",
    "YTCM Studio": "https://ytcm-studio.vercel.app",
    "NEXORA Hub": "https://nexora-lxcrdeav1-ut-tech.vercel.app",
    "ClientFlow AI": "https://ar-clientflow-ai-ut-tech.vercel.app",
    "Video Maker page": "https://video-maker-ut-tech.vercel.app",
}

@register("tube_watch", interval=300)
def tube_watch(ctx):
    down = []
    for name, url in SITES.items():
        try:
            req = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "ASGROUP/1.0"})
            code = urllib.request.urlopen(req, timeout=15).status
            if code >= 400:
                down.append(f"{name} ({code})")
        except Exception as e:
            down.append(f"{name} ({type(e).__name__})")
    if down:
        ctx.log("sites down: " + ", ".join(down), kind="warn")
        ctx.queue_approval(
            "Sites need attention",
            "These sites did not respond:\n" + "\n".join("• " + d for d in down))
        return f"{len(down)} site(s) down — queued for review"
    return f"all {len(SITES)} sites up"
