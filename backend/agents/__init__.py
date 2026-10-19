"""Agent plugin registry. ONE FILE PER AGENT — one agent, one job.

Add a new agent in agents/mywatcher.py:

    from agents import register
    from core import store

    @register("mywatcher", interval=600)   # run every 600 seconds
    def mywatcher(ctx):
        # ctx.log("message")            -> activity feed
        # ctx.queue_approval(title, detail) -> your daily approval queue
        # ctx.config                    -> config.yaml dict
        # return a short summary string shown on the dashboard card
        return "all good"

RULES (load-bearing):
- Agents READ and PREPARE. They never send, post, publish, buy, or change
  account settings by themselves.
- Anything consequential goes through ctx.queue_approval() — YOU decide
  in the dashboard (the once-a-day briefing).
- Catch your own errors where you can; the orchestrator marks unhandled
  crashes as status=error on your card.
"""
import datetime, importlib, pathlib

AGENTS = {}  # name -> {"fn": fn, "interval": seconds}

def register(name, interval=600, first_run_at=None):
    if first_run_at is not None:
        datetime.time.fromisoformat(first_run_at)
    def deco(fn):
        AGENTS[name] = {"fn": fn, "interval": interval,
                        "first_run_at": first_run_at}
        return fn
    return deco

def load_all():
    for p in pathlib.Path(__file__).parent.glob("*.py"):
        if p.name.startswith("_"):
            continue
        importlib.import_module(f"agents.{p.stem}")
