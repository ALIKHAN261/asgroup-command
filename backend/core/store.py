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
        CREATE TABLE IF NOT EXISTS agent_runs(
            id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL,
            started_at REAL NOT NULL, finished_at REAL, status TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS workspace_notes(
            note_id INTEGER PRIMARY KEY CHECK(note_id=1),
            content TEXT NOT NULL DEFAULT '', updated_at REAL NOT NULL);
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

def start_agent_run(agent):
    with _lock, _db:
        cur = _db.execute(
            "INSERT INTO agent_runs(agent,started_at,status) VALUES(?,?,?)",
            (agent, time.time(), "working"))
        _db.execute("DELETE FROM agent_runs WHERE id NOT IN"
                    " (SELECT id FROM agent_runs ORDER BY id DESC LIMIT 2000)")
        return cur.lastrowid

def finish_agent_run(run_id, status, summary):
    with _lock, _db:
        _db.execute(
            "UPDATE agent_runs SET finished_at=?,status=?,summary=? WHERE id=?",
            (time.time(), status, summary, run_id))

def get_agent_runs(agent, limit=20):
    with _lock:
        return [dict(row) for row in _db.execute(
            "SELECT id,agent,started_at,finished_at,status,summary "
            "FROM agent_runs WHERE agent=? ORDER BY id DESC LIMIT ?",
            (agent, limit))]

def get_workspace_note():
    with _lock:
        row = _db.execute(
            "SELECT content,updated_at FROM workspace_notes WHERE note_id=1").fetchone()
        return dict(row) if row else {"content": "", "updated_at": None}

def save_workspace_note(content):
    now = time.time()
    with _lock, _db:
        _db.execute(
            "INSERT INTO workspace_notes(note_id,content,updated_at) VALUES(1,?,?) "
            "ON CONFLICT(note_id) DO UPDATE SET content=excluded.content,"
            "updated_at=excluded.updated_at", (content, now))
    return {"content": content, "updated_at": now}

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

def queue_approval_once(agent, title, detail, kind="action"):
    with _lock, _db:
        row = _db.execute(
            "SELECT id FROM approvals WHERE agent=? AND title=? AND detail=? "
            "AND kind=? AND status='pending' ORDER BY id DESC LIMIT 1",
            (agent, title, detail, kind)).fetchone()
        if row:
            return row["id"], False
        cur = _db.execute(
            "INSERT INTO approvals(ts,agent,title,detail,kind) VALUES(?,?,?,?,?)",
            (time.time(), agent, title, detail, kind))
        return cur.lastrowid, True

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
