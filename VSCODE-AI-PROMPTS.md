# VS Code AI Prompts — extend your agent team

Open the `asgroup-command` folder in VS Code, paste the prompt into
Copilot Chat / Cursor / your AI extension, then ask for ONE item at a time.

---

```
You are working in "asgroup-command" — AS GROUP's agent team.
Backend: Python FastAPI (backend/main.py). Frontend: static dashboard
(frontend/) deployed on Vercel, talking to the backend's REST API.

ARCHITECTURE (do not change):
- backend/agents/*.py — ONE FILE PER AGENT. Register with:
    from agents import register
    @register("name", interval=600)   # seconds
    def name(ctx):
        ctx.log("msg")                        # activity feed
        ctx.queue_approval("title", "detail") # approval queue
        return "dashboard status line"
- backend/core/orchestrator.py — runs agents on intervals, tracks
  idle/working/error per agent. One crash never stops others.
- backend/core/store.py — SQLite: agent_state, activity, approvals.
- backend/core/security.py — X-API-Token auth on every endpoint.
- API: GET /api/agents, GET /api/activity, GET /api/approvals,
  POST /api/approvals/{id} {"decision":"approved"|"rejected"}.

STRICT RULES:
1. Agents READ and PREPARE only. Never send/post/publish/buy/change
   account settings inside an agent — use ctx.queue_approval() instead.
2. New backend logic goes in the right core module, not in agents.
3. Frontend stays vanilla HTML/CSS/JS (no build step, Vercel static).
4. pathlib for paths (Windows-compatible). Minimal new dependencies.
5. Update README.md + CHANGELOG.md for every feature.
6. Test: restart backend, curl the endpoints, show the dashboard card
   output. Report what you verified.

BUILD, one at a time (say "next" for the following):

1. YOUTUBE AGENT (tube_manager) — reads a data/channels.txt list
   (one YouTube channel URL per line), checks each channel's uploads
   feed for new videos in the last 7 days (YouTube RSS:
   https://www.youtube.com/feeds/videos.xml?channel_id=...), and posts
   a per-channel activity summary. Queue an approval if a channel has
   zero uploads in 14 days ("channel may be dead").

2. DAILY BRIEFING AGENT (briefer) — every morning at 08:00 (add simple
   daily scheduling to the orchestrator: interval + first-run-at-time),
   compiles: pending approvals count, agents in error, cash_track
   month total, tube_manager highlights → one approval item titled
   "☀️ Morning briefing" so the whole day is reviewed in one tap.

3. FREELANCE WATCHER (gig_watch) — monitors Fiverr inbox WITHOUT bot
   login: it can't. Instead: watch a data/gigs.txt file where you paste
   gig links + a data/messages.txt where you paste new buyer messages;
   drafts reply suggestions into the approval queue. Honest about the
   limit in its status line.

4. CONTENT REPORTER (reporter) — weekly: reads approvals history +
   activity log from SQLite and writes data/weekly-report.md
   (what agents did, what you approved, income totals). Queue the
   report as an approval item titled "📊 Weekly report".

5. DASHBOARD: agent detail view — clicking an agent card opens its
   recent activity lines + a Pause/Resume button (add
   POST /api/agents/{name}/pause). Paused agents show status=paused
   and are skipped by the orchestrator.

6. DASHBOARD: dark/light theme toggle + PWA manifest so it installs
   on your phone like an app.

Start with item 1. Implement fully, test it, then stop and wait.
```
