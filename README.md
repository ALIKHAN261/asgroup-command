# AS GROUP Command — v1.3.0

Your team of AI agents + a live web workspace. **One agent, one job.**
Agents work 24/7; anything consequential waits in your **once-a-day
approval queue** — nothing sends, posts, or spends without your tap.

## How it fits together

```
Your PC (backend)                    Vercel (frontend)
┌─────────────────────┐              ┌──────────────────────┐
│  agents/ 1 file =   │   REST API   │  Live workspace:     │
│  1 agent            │ ◄──────────► │  agent cards (live    │
│  orchestrator runs  │  token auth  │  status), activity   │
│  each on schedule   │              │  feed, approval      │
│  approvals → queue  │              │  queue (approve ✕/✓) │
└─────────────────────┘              └──────────────────────┘
   phone/laptop reach it via Tailscale or home WiFi
```

## Agent roster

| Agent | Every | Job |
|---|---|---|
| `tube_watch` | 5 min | Checks your sites are up; queues approval if one is down |
| `tube_manager` | 6 hr | Checks YouTube channel uploads and flags channels inactive for 14 days |
| `scout` | 1 hr | Drafts one client-outreach message per run (never sends) → approval queue |
| `cash_track` | 1 hr | Summarizes income from `data/income.json` (today / month / top sources) |
| `briefer` | daily at 08:00 | Queues approvals count, agent errors, cash total, and YouTube highlights for review |
| `gig_watch` | 10 min | Drafts replies from pasted Fiverr messages; does not connect to Fiverr |
| `reporter` | weekly | Writes agent activity, approval outcomes, and income totals to a report for review |
| `content_studio` | 12 hr | Turns manually entered topics into outline and caption drafts for review; never publishes |
| `invoice_watch` | 6 hr | Finds overdue unpaid invoices in a local CSV and drafts polite follow-ups; never sends |
| `sys_watch` | 10 min | Disk space + load; queues approval if disk < 10% free |
| `screen_eye` | 10 min | Snapshot history of your screen (the dashboard shows it **live**) |

## Live screen

`GET /api/screen/live?token=...` streams the local PC's screen as MJPEG video.
Screen and screenshot routes accept requests only from the backend PC itself;
another computer cannot view its screen, even with the API token. Open the
dashboard on the backend PC and connect it to `localhost` for the private feed.
The `<img>` tag sends the live-stream token as a query parameter. Windows only
(needs a real display).

## Voice assistant 🎙

Tap the mic in the dashboard header (Chrome). It listens, sends your
command to the backend, and **speaks the answer back**.
Understood: `status`, `what's pending`, `run <agent> now`,
`take a screenshot`, `help`.
**Voice never approves** — approvals need your tap in the dashboard.
A spoken "yes" never counts.

## PC control — admin access, your rules 🖱

You granted the team admin access to your screen, mouse, and PC. It is
wired like this:

1. Agents **cannot** click/type directly. They call
   `ctx.request_control(action, params, reason)`, which queues a proposal
   **with a screenshot** of your screen at that moment.
2. The action runs **only when you tap "Approve & run"** in the dashboard.
3. `config.yaml → control.auto_allow` is your explicit allowlist of
   actions that may run without a tap (default: empty — everything
   needs you). Example: `auto_allow: ["screenshot"]`.
4. **Hard blocks** (never run, even allowlisted): anything about
   passwords, OTPs, 2FA, CAPTCHAs, or submitting logins. Agents must
   never drive logins or security checks — that path gets accounts banned.
5. pyautogui FAILSAFE is on: slam the mouse into any screen corner to
   abort a runaway action.

Actions: `click {x,y}`, `doubleclick {x,y}`, `type {text}`,
`hotkey {keys:[...]}`, `open_url {url}`, `screenshot`.
Windows only (`pip install pyautogui`); enable with
`control.enabled: true` in config.yaml.

## Setup on your PC (one click)

Double-click **`start.bat`** (in the project root). It checks Python,
creates the virtual environment, installs dependencies, generates your
`api_token` on first run, and starts the backend. That's it.

- `start.bat` — everything above, in one double-click. Keep the window
  open (minimize is fine); to run 24/7, put a shortcut of `start.bat`
  in Windows Startup (`Win+R` → `shell:startup`).
- `stop.bat` — stops the backend.

After start.bat, your token is in `backend\config.yaml` — enter it once
in the dashboard (⚙ gear → API token); the browser remembers it.

## Setup on your PC (manual, VS Code)

```bat
cd asgroup-command\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Edit `backend\config.yaml` — set `api_token` to a long random string
(generate: `python -c "import secrets; print(secrets.token_hex(32))"`).

```bat
python main.py
```
Open http://127.0.0.1:8000/docs to see the API. Leave this running.

## The dashboard (multi-device)

- **This PC:** open the Vercel dashboard URL, tap ⚙, enter
  `http://127.0.0.1:8000` + your token.
- **Phone / laptop anywhere:** install **Tailscale** on your PC and your
  phone (free), set backend `host: "0.0.0.0"` in config.yaml, then use
  `http://<your-PC-tailscale-IP>:8000` in the dashboard's ⚙ settings.
  Your traffic stays inside your private tailnet — nothing public.

The dashboard supports a saved dark/light theme and can be installed as a
Progressive Web App from a supported mobile or desktop browser. It caches the
static interface for offline loading; backend data and live screen access still
require a connection to your PC.

## Add a new agent (one file, one job)

`backend/agents/myjob.py`:
```python
from agents import register

@register("myjob", interval=600)   # seconds between runs
def myjob(ctx):
    ctx.log("checking…")                    # → activity feed
    ctx.queue_approval("Title", "details")  # → your approval queue
    return "short status for the dashboard card"
```
Restart `main.py`. Done — it appears on the dashboard automatically.

## YouTube upload monitoring

Add one YouTube channel URL per line to `backend/data/channels.txt`. Channel
ID URLs (`youtube.com/channel/UC...`), handles (`youtube.com/@name`), and
custom channel URLs are supported. `tube_manager` checks each channel's public
RSS feed every six hours, summarizes uploads from the last seven days, and
queues one pending approval when there have been no uploads for 14 days. The
agent only reads public pages and feeds; it never uploads or changes a channel.

## Daily briefing

`briefer` runs at 08:00 in the backend machine's local timezone. On startup,
its first run is scheduled for the next 08:00; use the existing `run briefer
now` command to request an immediate run. It queues one `☀️ Morning briefing`
approval per day containing the pending approval count, errored agents, current
month's `income.json` total, and recent `tube_manager` highlights. It prepares
the briefing for review and takes no external actions.

## Freelance message drafts

Paste Fiverr gig links one per line into `backend/data/gigs.txt`, then paste
buyer messages into `backend/data/messages.txt`, separating messages with a
blank line. `gig_watch` checks these files every 10 minutes and queues a reply
suggestion for each new message. It cannot log in to or monitor the Fiverr
inbox; you must paste new messages yourself. Previously processed messages are
tracked in `backend/data/gig_watch_seen.json` to avoid repeat drafts.

## Content briefs

Add one topic per line to `backend/data/content-ideas.txt`. `content_studio`
prepares a hook, outline, caption starter, and call to action for each new idea
and queues it for review. It only uses your local list and never records or
publishes content. Processed ideas are tracked locally to avoid duplicate drafts.

## Invoice follow-up drafts

Add invoices to `backend/data/invoices.csv` with the columns
`invoice_id,client,amount,due_date,status` and ISO dates such as `2026-10-19`.
`invoice_watch` queues one polite follow-up draft for each overdue invoice that
is not marked `paid`, `void`, or `cancelled`. It does not connect to email,
send messages, or collect payment. Mark invoices paid in the CSV to clear them.

## Screen privacy

Screen captures and live streaming (`/api/screen`, `/api/shots/*`, and
`/api/screen/live`) are restricted to requests from the backend machine itself.
Requests from another PC are denied, even with the API token. The dashboard
must access the backend through `localhost` on the machine whose screen is
being viewed; remote devices cannot view that machine's screen.

## Weekly report

`reporter` runs every seven days after its first scheduled 08:00 run. It reads
the previous week's activity and approval history from SQLite, totals income
entries from `backend/data/income.json`, writes `backend/data/weekly-report.md`,
and queues the report as `📊 Weekly report` for review. Use `run reporter now`
to prepare it immediately.

## Dashboard workspace

The static dashboard groups the private screen preview and activity highlights
on the left, system and agent status in the center, and Chats, Logs, Notes, and
Tasks on the right. Notes stay in the current browser. Commands use the safe
`/api/command` endpoint; approvals remain manual. Click an agent card to view
its recent activity and pause or resume it. Pause state is stored in SQLite;
the scheduler skips paused agents, and a run already in progress may finish.
Use the agent detail view's **Run now** button to request an immediate run;
paused agents must be resumed before they can run.

The authenticated `POST /api/agents/{name}/pause` endpoint accepts
`{"paused":true}` to pause and `{"paused":false}` to resume. Agent activity
can be filtered with `GET /api/activity?agent={name}`. Pausing does not stop
an agent function already running; the orchestrator skips its next run.

## The rules (load-bearing)

1. Agents READ and PREPARE. They never send, post, publish, buy, or
   change account settings on their own.
2. Consequential things go through `ctx.queue_approval()` — you decide,
   once a day, in the dashboard.
3. Agents can never approve their own queue items (server-enforced).
4. One crashing agent never stops the others (status shows `error`).

## Files

```
backend/main.py          FastAPI: /api/agents /api/activity /api/approvals
backend/core/store.py    SQLite: agent status, activity, approval queue
backend/core/orchestrator.py  runs each agent on its interval forever
backend/core/security.py token auth
backend/agents/*.py      one file per agent (the plugin system)
backend/data/            created on first run (income.json, niches.txt…)
frontend/                static dashboard → deploy to Vercel
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Dashboard says "unauthorized" | Token in ⚙ must exactly match `api_token` in config.yaml |
| Dashboard can't reach backend | Backend must be running; from phone use Tailscale IP, not localhost |
| An agent card shows `error` | Click it — activity feed has the traceback; fix `backend/agents/<name>.py`, restart |
| Port 8000 busy | Change `port:` in config.yaml |
