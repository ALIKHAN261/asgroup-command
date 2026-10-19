"""Voice/text command parser. SAFE COMMANDS ONLY.

The voice assistant talks and takes commands, but it can never approve,
send, post, or spend. Approvals always need your tap in the dashboard —
a spoken "yes" never counts.
"""
import re
from core import store

def _agent_names():
    return [a["name"] for a in store.get_agents()]

def handle(text):
    t = (text or "").strip().lower()
    if not t:
        return "I didn't catch that. Say 'help' for commands."

    if t in ("help", "what can you do"):
        return ("Try: 'status' — how are my agents. 'What's pending' — "
                "approvals waiting. 'Run scout now'. 'Take a screenshot'.")

    if any(k in t for k in ("status", "how are", "agents doing")):
        agents = store.get_agents()
        if not agents:
            return "No agents registered yet."
        parts = [f"{a['name']}: {a['status']}" for a in agents]
        return "Agents — " + ", ".join(parts) + "."

    if any(k in t for k in ("pending", "approval", "waiting", "review")):
        items = store.get_approvals("pending")
        if not items:
            return "Nothing waiting — your approval queue is clear."
        lines = [f"#{a['id']}: {a['title']}" for a in items[:5]]
        more = f" (+{len(items) - 5} more)" if len(items) > 5 else ""
        return (f"{len(items)} waiting for your tap in the dashboard: "
                + "; ".join(lines) + more + ".")

    # Approve/reject by voice is refused by design — tap it in the dashboard.
    if any(k in t for k in ("approve", "reject", "yes", "confirm", "ok send")):
        return ("I can't approve by voice — that's your tap in the "
                "dashboard. Say 'what's pending' and I'll read the list.")

    if "screenshot" in t or "screen" in t:
        store.request_run("screen_eye")
        return "Capturing your screen now — check the Screen section."

    if t.startswith("run ") or t.startswith("start "):
        name = t.split(" ", 1)[1].strip()
        name = re.sub(r"\s+now$", "", name).strip().replace(" ", "_")
        if name in _agent_names():
            agent = next((item for item in store.get_agents()
                          if item["name"] == name), None)
            if agent and agent["status"] == "paused":
                return f"{name} is paused. Resume it in the dashboard before requesting a run."
            store.request_run(name)
            return f"Starting {name} now."
        return f"No agent called '{name}'. Say 'status' to hear the list."

    return ("Not sure what you mean. Say 'help' for what I understand.")
