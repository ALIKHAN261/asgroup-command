"""Daily status briefing, prepared for human review."""
import datetime
import json
import pathlib

from agents import register
from core import store

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
INCOME_FILE = DATA / "income.json"
TITLE = "☀️ Morning briefing"


def _month_total(today):
    if not INCOME_FILE.exists():
        return 0
    rows = json.loads(INCOME_FILE.read_text(encoding="utf-8") or "[]")
    month = today.strftime("%Y-%m")
    return sum(float(row.get("amount", 0) or 0) for row in rows
               if str(row.get("date", "")).startswith(month))


def _tube_highlights(now):
    since = now.timestamp() - 24 * 60 * 60
    highlights = [row["message"] for row in store.get_activity(500)
                  if row["agent"] == "tube_manager" and row["ts"] >= since
                  and row["kind"] in ("ok", "warn", "approval")
                  and row["message"].startswith("run finished:")]
    if highlights:
        return "\n".join(f"- {line.removeprefix('run finished: ')}"
                         for line in highlights[:5])
    agent = next((row for row in store.get_agents()
                  if row["name"] == "tube_manager"), None)
    if agent and agent.get("last_summary"):
        return agent["last_summary"]
    return "No recent tube_manager run recorded."


@register("briefer", interval=86400, first_run_at="08:00")
def briefer(ctx):
    now = datetime.datetime.now().astimezone()
    today = now.date()
    pending_count = len(store.get_approvals("pending"))
    errors = [row["name"] for row in store.get_agents()
              if row["status"] == "error"]
    month_total = _month_total(today)
    tube_summary = _tube_highlights(now)
    detail = (
        f"Morning briefing for {today.isoformat()}\n\n"
        f"Pending approvals: {pending_count}\n"
        f"Agents in error: {', '.join(errors) if errors else 'none'}\n"
        f"Cash Track month total ({today.strftime('%Y-%m')}): {month_total:g}\n"
        f"Tube Manager highlights:\n{tube_summary}"
    )

    approvals = [*store.get_approvals("pending"),
                 *store.get_approvals("approved"),
                 *store.get_approvals("rejected")]
    already_queued = any(
        row["agent"] == "briefer" and row["title"] == TITLE
        and datetime.datetime.fromtimestamp(row["ts"]).astimezone().date() == today
        for row in approvals)
    if already_queued:
        return f"morning briefing already queued for {today.isoformat()}"
    ctx.queue_approval(TITLE, detail)
    return f"morning briefing queued for {today.isoformat()}"
