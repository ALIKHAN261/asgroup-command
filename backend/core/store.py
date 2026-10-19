"""SQLite state: agent status, activity log, approval queue."""
import sqlite3, threading, time, pathlib

_lock = threading.Lock()
_db = None

def init(db_path):
    global _db
    pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    _db = sqlite3.connect(db_path, check_same_thread=False)
    _db.row_factory = sqlite3.Row
    with _lock, _db:
        _db.executescript("""
        CREATE TABLE IF NOT EXISTS agent_state(
            name TEXT PRIMARY KEY, status TEXT, last_run REAL, last_summary TEXT,
            paused INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS activity(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, agent TEXT,
            kind TEXT, message TEXT);
        CREATE TABLE IF NOT EXISTS approvals(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, agent TEXT,
            title TEXT, detail TEXT, status TEXT DEFAULT 'pending',
            decided_at REAL);
        CREATE TABLE IF NOT EXISTS run_requests(
            agent TEXT PRIMARY KEY, ts REAL);
        """)
    # Migration: approvals.kind (default 'action'; 'control' for PC control)
    try:
        _db.execute("ALTER TABLE approvals ADD COLUMN kind TEXT DEFAULT 'action'")
    except Exception:
        pass  # already migrated
    try:
        _db.execute("ALTER TABLE agent_state ADD COLUMN paused INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass
    return _db

def set_agent(name, status, summary=""):
    with _lock, _db:
        _db.execute(
            "INSERT INTO agent_state(name,status,last_run,last_summary)"
            " VALUES(?,?,?,?) ON CONFLICT(name) DO UPDATE SET"
            " status=excluded.status, last_run=excluded.last_run,"
            " last_summary=excluded.last_summary",
            (name, status, time.time(), summary))

def get_agents():
    with _lock:
        return [dict(r) for r in _db.execute(
            "SELECT name,CASE WHEN paused=1 THEN 'paused' ELSE status END AS status,"
            "last_run,last_summary,paused FROM agent_state ORDER BY name")]

def is_agent_paused(name):
    with _lock:
        row = _db.execute("SELECT paused FROM agent_state WHERE name=?", (name,)).fetchone()
        return bool(row and row["paused"])

def set_agent_paused(name, paused):
    now = time.time()
    status = "paused" if paused else "idle"
    summary = "paused by user" if paused else "resumed; waiting for next run"
    with _lock, _db:
        _db.execute(
            "INSERT INTO agent_state(name,status,last_run,last_summary,paused)"
            " VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET"
            " paused=excluded.paused,status=excluded.status,last_run=excluded.last_run,"
            " last_summary=excluded.last_summary",
            (name, status, now, summary, int(paused)))
    return True

def log(agent, kind, message):
    with _lock, _db:
        _db.execute("INSERT INTO activity(ts,agent,kind,message) VALUES(?,?,?,?)",
                    (time.time(), agent, kind, message))
        _db.execute("DELETE FROM activity WHERE id NOT IN"
                    " (SELECT id FROM activity ORDER BY id DESC LIMIT 500)")

def get_activity(limit=80, agent=None):
    with _lock:
        if agent:
            return [dict(r) for r in _db.execute(
                "SELECT ts,agent,kind,message FROM activity WHERE agent=? "
                "ORDER BY id DESC LIMIT ?", (agent, limit))]
        return [dict(r) for r in _db.execute(
            "SELECT ts,agent,kind,message FROM activity ORDER BY id DESC LIMIT ?",
            (limit,))]

def get_activity_since(since):
    with _lock:
        return [dict(r) for r in _db.execute(
            "SELECT ts,agent,kind,message FROM activity WHERE ts>=? ORDER BY id DESC",
            (since,))]

def queue_approval(agent, title, detail, kind="action"):
    with _lock, _db:
        cur = _db.execute(
            "INSERT INTO approvals(ts,agent,title,detail,kind) VALUES(?,?,?,?,?)",
            (time.time(), agent, title, detail, kind))
        return cur.lastrowid

def get_approvals(status="pending"):
    with _lock:
        return [dict(r) for r in _db.execute(
            "SELECT id,ts,agent,title,detail,kind,status FROM approvals"
            " WHERE status=? ORDER BY id DESC", (status,))]

def get_approvals_since(since):
    with _lock:
        return [dict(r) for r in _db.execute(
            "SELECT id,ts,agent,title,detail,kind,status,decided_at FROM approvals"
            " WHERE ts>=? OR decided_at>=? ORDER BY id DESC", (since, since))]

def get_approval(approval_id):
    with _lock:
        r = _db.execute("SELECT id,ts,agent,title,detail,kind,status FROM approvals"
                        " WHERE id=?", (approval_id,)).fetchone()
        return dict(r) if r else None

def decide_approval(approval_id, decision):
    assert decision in ("approved", "rejected")
    with _lock, _db:
        cur = _db.execute(
            "UPDATE approvals SET status=?, decided_at=? WHERE id=? AND status='pending'",
            (decision, time.time(), approval_id))
        return cur.rowcount > 0

def request_run(agent):
    with _lock, _db:
        _db.execute(
            "INSERT INTO run_requests(agent,ts) VALUES(?,?)"
            " ON CONFLICT(agent) DO UPDATE SET ts=excluded.ts",
            (agent, time.time()))

def pop_run_request(agent):
    with _lock, _db:
        cur = _db.execute("DELETE FROM run_requests WHERE agent=?", (agent,))
        return cur.rowcount > 0
