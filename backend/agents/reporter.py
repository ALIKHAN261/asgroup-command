"""Writes a weekly activity and income report for human review."""
import datetime
import json
import pathlib
from collections import defaultdict

from agents import register
from core import store

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
INCOME_FILE = DATA / "income.json"
REPORT_FILE = DATA / "weekly-report.md"
TITLE = "📊 Weekly report"


def _income_summary(start_date, end_date):
    if not INCOME_FILE.exists():
        return 0.0, {}
    rows = json.loads(INCOME_FILE.read_text(encoding="utf-8") or "[]")
    totals = defaultdict(float)
    for row in rows:
        recorded = datetime.date.fromisoformat(str(row.get("date", "")))
        if start_date <= recorded <= end_date:
            source = str(row.get("source", "unknown"))
            totals[source] += float(row.get("amount", 0) or 0)
    return sum(totals.values()), dict(totals)


def _report(now, activities, approvals, total_income, income_by_source):
    since = now - datetime.timedelta(days=7)
    lines = [
        "# Weekly report",
        f"Period: {since.strftime('%Y-%m-%d %H:%M %Z')} to {now.strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        "## Agent activity",
    ]
    grouped = defaultdict(list)
    for item in activities:
        grouped[item["agent"]].append(item)
    if not grouped:
        lines.append("No activity was recorded during this period.")
    for agent, items in sorted(grouped.items()):
        lines.append(f"### {agent} ({len(items)} entries)")
        for item in items[:5]:
            message = item["message"].splitlines()[0][:240]
            timestamp = datetime.datetime.fromtimestamp(item["ts"]).astimezone()
            lines.append(f"- {timestamp:%Y-%m-%d %H:%M} [{item['kind']}] {message}")

    lines.extend(["", "## Approval outcomes"])
    outcomes = [item for item in approvals
                if item["status"] in ("approved", "rejected")
                and item["decided_at"] is not None
                and item["decided_at"] >= since.timestamp()]
    if outcomes:
        for item in outcomes:
            decided = datetime.datetime.fromtimestamp(item["decided_at"]).astimezone()
            lines.append(f"- {decided:%Y-%m-%d %H:%M}: {item['status']} - {item['title']} ({item['agent']})")
    else:
        lines.append("No approvals were decided during this period.")

    lines.extend(["", "## Approval items queued"])
    queued = [item for item in approvals if item["ts"] >= since.timestamp()]
    if queued:
        for item in queued:
            created = datetime.datetime.fromtimestamp(item["ts"]).astimezone()
            lines.append(f"- {created:%Y-%m-%d %H:%M}: {item['title']} ({item['agent']}; {item['status']})")
    else:
        lines.append("No approval items were queued during this period.")

    lines.extend(["", "## Income", f"Weekly total: {total_income:g}"])
    if income_by_source:
        for source, amount in sorted(income_by_source.items()):
            lines.append(f"- {source}: {amount:g}")
    else:
        lines.append("No income entries were recorded during this period.")
    return "\n".join(lines) + "\n"


@register("reporter", interval=604800, first_run_at="08:00")
def reporter(ctx):
    now = datetime.datetime.now().astimezone()
    since = now - datetime.timedelta(days=7)
    activities = store.get_activity_since(since.timestamp())
    approvals = store.get_approvals_since(since.timestamp())
    total, by_source = _income_summary(since.date(), now.date())
    report = _report(now, activities, approvals, total, by_source)
    DATA.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(report, encoding="utf-8")

    already_queued = any(
        item["agent"] == "reporter" and item["title"] == TITLE
        and item["ts"] >= since.timestamp()
        for item in approvals)
    if already_queued:
        return f"weekly report updated; already queued in the last 7 days ({REPORT_FILE.name})"
    ctx.queue_approval(TITLE, report)
    return f"weekly report written and queued for review ({REPORT_FILE.name})"
