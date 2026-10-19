"""PC control plane — mouse, keyboard, screen. WINDOWS ONLY.

How it stays safe (your rules, enforced in code):
1. Agents can NEVER call these functions directly. They use
   ctx.request_control(action, params, reason), which only QUEUES a
   proposal with a screenshot of the current screen.
2. The action executes ONLY after you tap Approve in the dashboard.
3. config.yaml `control.auto_allow` is an explicit allowlist of action
   names that may run without approval (default: empty = everything
   needs your tap).
4. pyautogui FAILSAFE is on: shove the mouse into a screen corner to
   abort any runaway movement.
5. HARD BLOCKS (never auto-executed, even allowlisted): anything whose
   reason mentions password/otp/2fa/login-submit is refused. Agents
   must not drive logins, OTPs, or CAPTCHAs — platform bans live there.

Supported actions:
- click:      params {x, y, button="left"}
- doubleclick params {x, y}
- type:       params {text}            (types into the FOCUSED window)
- hotkey:     params {keys: ["ctrl","s"]}
- open_url:   params {url}             (opens in default browser)
- screenshot: params {}               (just captures)
"""
import time, pathlib

_enabled = False
_auto_allow = set()
_shot_dir = None
_pg = None

def configure(enabled, auto_allow, shot_dir):
    global _enabled, _auto_allow, _shot_dir, _pg
    _enabled = bool(enabled)
    _auto_allow = set(auto_allow or [])
    _shot_dir = pathlib.Path(shot_dir)
    _shot_dir.mkdir(parents=True, exist_ok=True)
    if _enabled:
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.4
            _pg = pyautogui
        except Exception:
            _pg = None  # headless / not installed -> control unavailable

def available():
    return _enabled and _pg is not None

def is_auto_allowed(action):
    return action in _auto_allow

_HARD_BLOCK_WORDS = ("password", "otp", "2fa", "two-factor", "captcha",
                     "login-submit", "sign-in-submit")

def hard_blocked(reason):
    r = (reason or "").lower()
    return any(w in r for w in _HARD_BLOCK_WORDS)

def capture(name=None):
    """Screenshot for approval cards. Returns filename or None."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.thumbnail((960, 960))
        fname = name or f"shot_{int(time.time())}.png"
        img.save(_shot_dir / fname)
        return fname
    except Exception:
        return None

def execute(action, params):
    """Run one approved control action. Returns (ok, message)."""
    if not available():
        return False, "control unavailable (needs Windows + pyautogui)"
    try:
        if action == "click":
            _pg.click(int(params.get("x", 0)), int(params.get("y", 0)),
                      button=params.get("button", "left"))
        elif action == "doubleclick":
            _pg.doubleClick(int(params.get("x", 0)), int(params.get("y", 0)))
        elif action == "type":
            _pg.write(str(params.get("text", "")), interval=0.02)
        elif action == "hotkey":
            _pg.hotkey(*params.get("keys", []))
        elif action == "open_url":
            import webbrowser
            webbrowser.open(str(params.get("url", "")))
        elif action == "screenshot":
            capture()
        else:
            return False, f"unknown action: {action}"
        return True, f"{action} executed"
    except Exception as e:
        return False, f"control failed: {type(e).__name__}: {e}"
