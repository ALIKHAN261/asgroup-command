# Changelog

## Unreleased
- Added `content_studio` to prepare reviewable briefs from local topic lists.
- Added `invoice_watch` to draft overdue invoice follow-ups from a local CSV.
- Added authenticated `POST /api/agents/{name}/run` and an agent-detail Run now button.
- Improved light-theme contrast across chat, logs, approvals, and agent details.
- Added a persistent dark/light theme toggle to the dashboard.
- Added a PWA manifest, app icon, and service-worker caching for offline shell loading.
- Added agent detail views with recent activity and pause/resume controls;
  pause state persists in SQLite and the orchestrator skips paused agents.
- Added a weekly `reporter` agent that writes an activity, approval, and income
  report to `data/weekly-report.md` and queues it for review.
- Redesigned the static dashboard as a responsive operations workspace with
  working Chats, Logs, Notes, Tasks, agent, activity, settings, and local-screen panels.
- Added `gig_watch` for pasted Fiverr links and buyer messages; it drafts
  suggested replies for approval without logging in to Fiverr.
- Restricted screenshot and live screen endpoints to loopback clients so
  another PC cannot view the backend machine's screen.
- Added a daily `briefer` agent and 08:00 first-run scheduling support in the
  orchestrator. It queues a consolidated approval and deduplicates same-day runs.
- Added `tube_manager`, which checks configured YouTube channels through their
  public RSS feeds, summarizes recent uploads, and queues review for channels
  inactive for 14 days.

## 1.3.0
- LIVE screen streaming: /api/screen/live (MJPEG, ~5 fps, token in query
  param since <img> can't send headers); dashboard Screen section now
  shows real-time video with a LIVE badge. screen_eye keeps snapshot
  history.

## 1.2.0
- PC control plane (admin grant): agents propose mouse/keyboard actions
  with a screenshot; "Approve & run" executes; auto_allow allowlist in
  config; hard blocks on passwords/OTPs/CAPTCHAs/logins; pyautogui
  failsafe on. Windows only.
- Voice assistant: mic button (SpeechRecognition), spoken replies (TTS),
  POST /api/command safe parser (status/pending/run/screenshot/help).
  Voice can never approve — dashboard tap required.

## 1.1.0
- screen_eye agent: scheduled screenshots, viewable in dashboard
- /api/screen endpoint

## 1.0.1
- `start.bat`: one-click Windows launcher (Python check, venv, deps, first-run token generation, starts backend) — the README referenced it but it was missing
- `stop.bat`: stops the backend
- README: one-click setup section + fixed dangling start.bat reference

## 1.0.0
- Backend: FastAPI + orchestrator + SQLite store + token auth
- Agent plugin system: one file per agent (`@register(name, interval)`)
- 4 starter agents: tube_watch, scout (draft-only), cash_track, sys_watch
- Approval queue API (agents can never self-approve)
- Frontend: live workspace dashboard (agent cards, activity feed, approvals)

