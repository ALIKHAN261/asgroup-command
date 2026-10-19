"""Cash Track — income log + daily summary. Read-only reporting.

Add income in data/income.json:
    [{"date": "2026-10-18", "source": "Fiverr", "amount": 150},
     {"date": "2026-10-18", "source": "YouTube", "amount": 12}]
"""
import json, datetime, pathlib
from agents import register

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
INCOME_FILE = DATA / "income.json"

@register("cash_track", interval=3600)
def cash_track(ctx):
    if not INCOME_FILE.exists():
        DATA.mkdir(exist_ok=True)
        INCOME_FILE.write_text("[]\n")
        return "no income.json yet — created template, add your income"
    rows = json.loads(INCOME_FILE.read_text() or "[]")
    today = datetime.date.today().isoformat()
    month = today[:7]
    t = sum(r.get("amount", 0) for r in rows if r.get("date") == today)
    m = sum(r.get("amount", 0) for r in rows
            if str(r.get("date", "")).startswith(month))
    by_src = {}
    for r in rows:
        by_src[r.get("source", "?")] = by_src.get(r.get("source", "?"), 0) + r.get("amount", 0)
    top = ", ".join(f"{k}: {v}" for k, v in sorted(by_src.items(), key=lambda x: -x[1])[:3])
    return f"today {t} · {month} {m} · top: {top or '—'}"
