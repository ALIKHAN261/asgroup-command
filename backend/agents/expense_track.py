"""Summarize manually logged expenses against income; never moves money."""
import csv
import datetime
import json
import pathlib
from decimal import Decimal, InvalidOperation

from agents import register

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
EXPENSE_FILE = DATA / "expenses.csv"
INCOME_FILE = DATA / "income.json"


def _amount(value):
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _read_expenses():
    if not EXPENSE_FILE.exists():
        EXPENSE_FILE.write_text(
            "date,amount,category,description\n"
            "# Add one expense per row; date format YYYY-MM-DD\n",
            encoding="utf-8")
    rows = []
    skipped = 0
    with EXPENSE_FILE.open(newline="", encoding="utf-8-sig") as source:
        lines = (line for line in source if not line.lstrip().startswith("#"))
        for row in csv.DictReader(lines):
            try:
                recorded = datetime.date.fromisoformat((row.get("date") or "").strip())
                amount = _amount(row.get("amount", ""))
                if amount is None or not amount.is_finite() or amount < 0:
                    raise ValueError("invalid expense amount")
            except ValueError:
                skipped += 1
                continue
            rows.append((recorded, amount))
    return rows, skipped


def _read_income():
    if not INCOME_FILE.exists():
        return [], False
    rows = json.loads(INCOME_FILE.read_text(encoding="utf-8") or "[]")
    if not isinstance(rows, list):
        raise ValueError("income.json must contain a list")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        recorded = datetime.date.fromisoformat(str(row.get("date", "")))
        amount = _amount(row.get("amount", 0))
        if amount is not None and amount.is_finite():
            result.append((recorded, amount))
    return result, True


@register("expense_track", interval=3600)
def expense_track(ctx):
    DATA.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today()
    month_key = today.strftime("%Y-%m")
    expenses, skipped = _read_expenses()
    income, has_income_file = _read_income()
    month_expenses = sum((amount for day, amount in expenses
                          if day.strftime("%Y-%m") == month_key), Decimal("0"))
    today_expenses = sum((amount for day, amount in expenses if day == today), Decimal("0"))
    month_income = sum((amount for day, amount in income
                        if day.strftime("%Y-%m") == month_key), Decimal("0"))
    if skipped:
        ctx.log(f"skipped {skipped} malformed expense row(s)", kind="warn")
    profit = month_income - month_expenses
    income_label = "income log missing" if not has_income_file else f"income {month_income:g}"
    return (f"today expenses {today_expenses:g} · {month_key} expenses {month_expenses:g} · "
            f"{income_label} · net {profit:g}")
