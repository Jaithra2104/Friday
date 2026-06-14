"""
reminder_store.py — Persistent reminder storage for Friday.

Reminders survive PC restarts. When a reminder fires:
  - Always sends to Telegram + Email (works even if PC is off/locked)
  - Also speaks it via TTS if Friday is running

On startup: loads all pending reminders and re-schedules them.
"""

import os
import json
import time
import datetime
import threading
import sys

# Ensure we can import siblings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mobile_sender

REMINDERS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "reminders_data.json"
)

_speak_callback  = None   # set by friday.pyw: fn(text)
_ui_callback     = None   # set by friday.pyw: fn(text) for status bar
_lock            = threading.Lock()
_loaded_ids      = set()  # prevent double-firing


# ── Config ────────────────────────────────────────────────────────────────

def set_callbacks(speak_fn, ui_fn=None):
    global _speak_callback, _ui_callback
    _speak_callback = speak_fn
    _ui_callback    = ui_fn


# ── Persistence ───────────────────────────────────────────────────────────

def _load_all():
    if not os.path.exists(REMINDERS_FILE):
        return []
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def _save_all(reminders):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, indent=2, ensure_ascii=False)


# ── Add / list / delete ───────────────────────────────────────────────────

def add_reminder(text: str, target_dt: datetime.datetime) -> dict:
    """
    Save a new reminder to disk.
    Returns the reminder dict.
    """
    with _lock:
        reminders = _load_all()
        rid = f"{datetime.datetime.now().timestamp():.3f}"
        reminder = {
            "id":     rid,
            "text":   text,
            "target": target_dt.strftime("%Y-%m-%d %H:%M"),
            "sent":   False
        }
        reminders.append(reminder)
        _save_all(reminders)
        print(f"[REMINDER] Saved: '{text}' at {reminder['target']}")
        return reminder


def get_pending_reminders() -> list:
    """Return all unsent reminders."""
    return [r for r in _load_all() if not r.get("sent")]


def get_all_reminders() -> list:
    return _load_all()


def delete_reminder(rid: str):
    with _lock:
        reminders = [r for r in _load_all() if r["id"] != rid]
        _save_all(reminders)


def mark_sent(rid: str):
    with _lock:
        reminders = _load_all()
        for r in reminders:
            if r["id"] == rid:
                r["sent"] = True
        _save_all(reminders)


# ── Firing ────────────────────────────────────────────────────────────────

def _fire(reminder: dict):
    """Fire a reminder — speak it AND send to mobile."""
    if reminder["id"] in _loaded_ids:
        return
    _loaded_ids.add(reminder["id"])

    text  = reminder["text"]
    msg   = f"Friday Reminder: {text}"
    label = f"[REMINDER] {text}"

    print(f"[REMINDER] Firing: {text}")

    # 1. Always send to mobile (works even if PC is off/locked)
    try:
        mobile_sender.send_to_mobile(text=msg)
    except Exception as e:
        print(f"[REMINDER] Mobile send error: {e}")

    # 2. Speak it (if Friday is running and TTS is available)
    if _speak_callback:
        try:
            _speak_callback(label)
        except Exception as e:
            print(f"[REMINDER] Speak error: {e}")

    if _ui_callback:
        try:
            _ui_callback(label)
        except:
            pass

    mark_sent(reminder["id"])


# ── Scheduler loop ────────────────────────────────────────────────────────

def _scheduler_loop():
    print("[REMINDER] Scheduler started.")
    while True:
        now = datetime.datetime.now()
        reminders = _load_all()

        for r in reminders:
            if r.get("sent"):
                continue
            try:
                target = datetime.datetime.strptime(r["target"], "%Y-%m-%d %H:%M")
                if now >= target:
                    _fire(r)
            except Exception as e:
                print(f"[REMINDER] Parse error for '{r}': {e}")

        time.sleep(30)   # check every 30 seconds


def start():
    """Start the background scheduler. Call once at startup."""
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()


def announce_pending(speak_fn):
    """On startup, tell the user how many reminders are waiting."""
    pending = get_pending_reminders()
    if not pending:
        return
    count = len(pending)
    if count == 1:
        speak_fn(f"Sir, you have one pending reminder: {pending[0]['text']} "
                 f"due at {pending[0]['target']}.")
    else:
        names = ", ".join(r["text"] for r in pending[:3])
        speak_fn(f"Sir, you have {count} pending reminders. Including: {names}.")
