"""Prepare content briefs from manually supplied ideas; never publish."""
import hashlib
import json
import pathlib

from agents import register

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
IDEAS_FILE = DATA / "content-ideas.txt"
SEEN_FILE = DATA / "content_studio_seen.json"


def _read_ideas():
    if not IDEAS_FILE.exists():
        IDEAS_FILE.write_text(
            "# Add one content topic per line; drafts are queued for review\n",
            encoding="utf-8")
    return [line.strip() for line in IDEAS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def _key(idea):
    normalized = " ".join(idea.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _brief(idea):
    return (
        f"Topic: {idea}\n\n"
        "Suggested short-form content brief (review and edit before use):\n"
        f"Hook: Ask a specific question about {idea}.\n"
        "Outline:\n"
        "1. State the audience's problem in one sentence.\n"
        "2. Share three practical points or steps.\n"
        "3. Close with one takeaway.\n\n"
        f"Caption starter: A practical guide to {idea}.\n"
        "Call to action: Invite viewers to share their experience.\n\n"
        "Prepared as a draft only; nothing has been recorded, posted, or published."
    )


@register("content_studio", interval=43200)
def content_studio(ctx):
    DATA.mkdir(parents=True, exist_ok=True)
    ideas = _read_ideas()
    seen = json.loads(SEEN_FILE.read_text(encoding="utf-8")) if SEEN_FILE.exists() else []
    if not isinstance(seen, list) or any(not isinstance(item, str) for item in seen):
        raise ValueError("content studio state file is invalid")
    seen_set = set(seen)
    fresh = [idea for idea in ideas if _key(idea) not in seen_set]
    for idea in fresh:
        key = _key(idea)
        ctx.queue_approval(f"Content brief - {' '.join(idea.split())[:60]}", _brief(idea))
        seen.append(key)
        seen_set.add(key)
        temporary = SEEN_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(seen[-1000:]), encoding="utf-8")
        temporary.replace(SEEN_FILE)
    return f"checked {len(ideas)} content idea(s); prepared {len(fresh)} new brief(s); never publishes"
