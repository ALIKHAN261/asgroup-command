"""Queue polite follow-up drafts for manually tracked overdue invoices."""
import csv
import datetime
import hashlib
import json
import pathlib

from agents import register

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
INVOICES_FILE = DATA / "invoices.csv"
SEEN_FILE = DATA / "invoice_watch_seen.json"
PAID_STATES = {"paid", "void", "cancelled", "canceled"}


def _signature(row):
    values = "|".join(str(row.get(field, "")).strip()
                      for field in ("invoice_id", "due_date", "amount"))
    return hashlib.sha256(values.casefold().encode("utf-8")).hexdigest()


def _load_overdue(today):
    if not INVOICES_FILE.exists():
        INVOICES_FILE.write_text(
            "invoice_id,client,amount,due_date,status\n"
            "# Replace this line with invoice rows; statuses: unpaid, paid\n",
            encoding="utf-8")
    overdue = []
    with INVOICES_FILE.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(line for line in source if not line.lstrip().startswith("#")):
            invoice_id = (row.get("invoice_id") or "").strip()
            due_text = (row.get("due_date") or "").strip()
            if not invoice_id or not due_text:
                continue
            due_date = datetime.date.fromisoformat(due_text)
            if due_date < today and (row.get("status") or "").strip().casefold() not in PAID_STATES:
                overdue.append(row)
    return overdue


def _draft(row, due_date):
    client = (row.get("client") or "your client").strip()
    amount = (row.get("amount") or "the outstanding amount").strip()
    invoice_id = row["invoice_id"].strip()
    return (
        "Draft follow-up only. No email or payment request was sent.\n\n"
        f"Subject: Follow-up on invoice {invoice_id}\n\n"
        f"Hi {client},\n\n"
        f"I hope you are well. I am following up on invoice {invoice_id} for "
        f"{amount}, which was due on {due_date.isoformat()}. Could you let me "
        "know when I can expect payment, or tell me if you need another copy?\n\n"
        "Thank you."
    )


@register("invoice_watch", interval=21600)
def invoice_watch(ctx):
    DATA.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today()
    overdue = _load_overdue(today)
    seen = json.loads(SEEN_FILE.read_text(encoding="utf-8")) if SEEN_FILE.exists() else []
    if not isinstance(seen, list) or any(not isinstance(item, str) for item in seen):
        raise ValueError("invoice watcher state file is invalid")
    outstanding = {_signature(row) for row in overdue}
    seen_set = set(seen)
    fresh = [row for row in overdue if _signature(row) not in seen_set]
    for row in fresh:
        due_date = datetime.date.fromisoformat(row["due_date"].strip())
        ctx.queue_approval(f"Invoice follow-up draft - {row['invoice_id'].strip()}",
                           _draft(row, due_date))
    updated = (seen_set & outstanding) | {_signature(row) for row in fresh}
    if updated != seen_set:
        temporary = SEEN_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(sorted(updated)), encoding="utf-8")
        temporary.replace(SEEN_FILE)
    return f"checked {len(overdue)} overdue invoice(s); prepared {len(fresh)} new drafts; sends nothing"
