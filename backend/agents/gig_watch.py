"""Drafts replies from manually pasted freelance messages; no inbox login."""
import hashlib
import json
import pathlib

from agents import register

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
GIGS_FILE = DATA / "gigs.txt"
MESSAGES_FILE = DATA / "messages.txt"
SEEN_FILE = DATA / "gig_watch_seen.json"


def _read_blocks(path):
    blocks = path.read_text(encoding="utf-8").split("\n\n")
    return [message for block in blocks
            if (message := "\n".join(line for line in block.splitlines()
                                     if not line.lstrip().startswith("#")).strip())]


def _digest(message):
    normalized = " ".join(message.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _save_seen(seen):
    temporary = SEEN_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(seen[-1000:]), encoding="utf-8")
    temporary.replace(SEEN_FILE)


@register("gig_watch", interval=600)
def gig_watch(ctx):
    DATA.mkdir(parents=True, exist_ok=True)
    if not GIGS_FILE.exists():
        GIGS_FILE.write_text(
            "# Paste one Fiverr gig link per line\n", encoding="utf-8")
    if not MESSAGES_FILE.exists():
        MESSAGES_FILE.write_text(
            "# Paste buyer messages here; separate messages with a blank line\n",
            encoding="utf-8")
    gigs = [line.strip() for line in GIGS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]
    messages = _read_blocks(MESSAGES_FILE)
    seen = json.loads(SEEN_FILE.read_text(encoding="utf-8")) if SEEN_FILE.exists() else []
    if not isinstance(seen, list) or any(not isinstance(item, str) for item in seen):
        raise ValueError("gig watcher state file is invalid")
    seen_set = set(seen)
    new_messages = [message for message in messages if _digest(message) not in seen_set]
    gig_context = "\n".join(f"- {url}" for url in gigs) if gigs else "No gig links provided."

    for message in new_messages:
        digest = _digest(message)
        title_text = " ".join(message.split())[:55]
        title = f"Fiverr reply draft - {title_text}" if title_text else "Fiverr reply draft"
        detail = (
            "Fiverr inbox is not connected. This draft was prepared from the pasted message.\n\n"
            f"Buyer message:\n{message}\n\n"
            "Suggested reply:\n"
            "Hi, thanks for reaching out about your project. I would be happy to learn more. "
            "Could you share the expected deliverables, deadline, and budget so I can confirm "
            "whether I am a good fit?\n\n"
            f"Your gig links for reference:\n{gig_context}"
        )
        ctx.queue_approval(title, detail)
        seen.append(digest)
        seen_set.add(digest)
        _save_seen(seen)

    if new_messages:
        ctx.log(f"prepared {len(new_messages)} reply draft(s) from pasted messages",
                kind="approval")
    return (f"Fiverr inbox is not connected; checked pasted files only. "
            f"{len(gigs)} gig link(s), {len(new_messages)} new reply draft(s)")
