"""Runs every registered agent on its own interval, forever.

Each agent cycles: idle -> working -> idle (or error). Status is visible
live on the dashboard. One crashing agent never stops the others.
"""
import datetime, threading, time, traceback
from core import store

class Ctx:
    def __init__(self, agent_name, config):
        self.agent_name = agent_name
        self.config = config

    def log(self, message, kind="info"):
        store.log(self.agent_name, kind, message)

    def queue_approval(self, title, detail):
        aid, created = store.queue_approval_once(self.agent_name, title, detail)
        message = (f"queued for your review: {title} (#{aid})" if created
                   else f"already waiting for review: {title} (#{aid})")
        store.log(self.agent_name, "approval", message)
        return aid

    def request_control(self, action, params, reason):
        """Ask to control the PC. Queues a proposal with a screenshot —
        it runs ONLY after you tap Approve. Returns approval id or None."""
        from core import control
        if not control.available():
            self.log("control unavailable (enable in config + Windows only)",
                     kind="warn")
            return None
        if control.hard_blocked(reason):
            self.log(f"control refused by policy: {action} ({reason})",
                     kind="error")
            return None
        shot = control.capture()
        import json
        detail = json.dumps({"action": action, "params": params or {},
                             "reason": reason, "shot": shot})
        aid = store.queue_approval(
            self.agent_name,
            f"🖱 Control: {action} — {reason}", detail, kind="control")
        self.log(f"control proposed: {action} (#{aid}) — waiting your tap",
                 kind="approval")
        return aid

def _wait(name, seconds, stop):
    deadline = time.monotonic() + max(0, seconds)
    while not stop.is_set():
        if store.is_agent_paused(name):
            store.pop_run_request(name)
            return "paused"
        if store.pop_run_request(name):
            store.log(name, "info", "run requested; starting now")
            return "requested"
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return "elapsed"
        time.sleep(min(1, remaining))
    return "stopped"


def _seconds_until(time_text):
    run_time = datetime.time.fromisoformat(time_text)
    now = datetime.datetime.now().astimezone()
    target = datetime.datetime.combine(now.date(), run_time, tzinfo=now.tzinfo)
    if target <= now:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()


def _loop(name, spec, config, stop):
    ctx = Ctx(name, config)
    first_run_at = spec.get("first_run_at")
    waiting = (f"waiting for first run at {first_run_at}"
               if first_run_at else "waiting for first run")
    if not store.is_agent_paused(name):
        store.set_agent(name, "idle", waiting)
    # Small stagger so all agents don't fire at once on startup.
    initial_wait = _wait(name, 3, stop)
    if initial_wait == "stopped":
        return
    if first_run_at and initial_wait != "requested":
        while not stop.is_set():
            scheduled_wait = _wait(name, _seconds_until(first_run_at), stop)
            if scheduled_wait == "stopped":
                return
            if scheduled_wait == "paused":
                while store.is_agent_paused(name) and not stop.is_set():
                    store.pop_run_request(name)
                    time.sleep(1)
                continue
            break
    while not stop.is_set():
        if store.is_agent_paused(name):
            store.pop_run_request(name)
            time.sleep(1)
            continue
        try:
            store.set_agent(name, "working", "running…")
            summary = spec["fn"](ctx) or "done"
            store.set_agent(name, "idle", str(summary)[:200])
            store.log(name, "ok", f"run finished: {str(summary)[:200]}")
        except Exception as e:
            store.set_agent(name, "error", f"{type(e).__name__}: {e}"[:200])
            store.log(name, "error", f"crashed: {e}\n{traceback.format_exc()[-500:]}")
        # Sleep in small chunks so shutdown is fast and "run now"
        # requests (voice/dashboard) are picked up within ~2 seconds.
        for _ in range(int(spec["interval"])):
            if stop.is_set():
                break
            if store.is_agent_paused(name):
                store.pop_run_request(name)
                break
            if store.pop_run_request(name):
                store.log(name, "info", "run requested — starting now")
                break
            time.sleep(1)

def start(agents, config):
    stop = threading.Event()
    for name, spec in agents.items():
        t = threading.Thread(target=_loop, args=(name, spec, config, stop),
                             daemon=True, name=f"agent-{name}")
        t.start()
    return stop
