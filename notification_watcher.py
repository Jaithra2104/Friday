"""
notification_watcher.py — Watches Windows Phone Link notifications for incoming calls.
Reads from the Windows notification database (SQLite) by copying it to avoid lock issues.
"""
import os
import re
import time
import shutil
import sqlite3
import tempfile
import threading
import xml.etree.ElementTree as ET

NOTIF_DB = os.path.expandvars(
    r"%LOCALAPPDATA%\Microsoft\Windows\Notifications\wpndatabase.db"
)

_call_callback = None   # fn(caller_name: str)
_seen_ids = set()
_watching = False
_pending_call = None    # stores current caller so Friday can pick up / reject


def set_call_callback(fn):
    """Register a function to call when an incoming call is detected."""
    global _call_callback
    _call_callback = fn


def get_pending_call():
    return _pending_call


def clear_pending_call():
    global _pending_call
    _pending_call = None


def _copy_and_read_db():
    """Copy locked Windows notification DB to a temp file and read it."""
    if not os.path.exists(NOTIF_DB):
        return []
    tmp = tempfile.mktemp(suffix=".db")
    try:
        shutil.copy2(NOTIF_DB, tmp)
        conn = sqlite3.connect(tmp)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Id, HandlerId, Payload, ArrivalTime
            FROM Notification
            WHERE (HandlerId LIKE '%YourPhone%'
                OR HandlerId LIKE '%PhoneLink%'
                OR HandlerId LIKE '%yourphone%')
            ORDER BY ArrivalTime DESC
            LIMIT 20
        """)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"[NOTIF] DB read error: {e}")
        return []
    finally:
        try:
            os.unlink(tmp)
        except:
            pass


def _extract_caller(payload_bytes):
    """Parse the notification XML payload to find the caller name."""
    if not payload_bytes:
        return "Someone"
    try:
        payload_str = payload_bytes.decode("utf-8", errors="ignore") \
            if isinstance(payload_bytes, bytes) else str(payload_bytes)

        # Try XML parsing
        root = ET.fromstring(payload_str)
        texts = root.findall('.//{*}text')
        for t in texts:
            val = (t.text or "").strip()
            if val and val.lower() not in ["incoming call", "calling", "call", ""]:
                return val

        # Regex fallback
        match = re.search(r'>([^<]{2,40})<', payload_str)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"[NOTIF] Payload parse error: {e}")
    return "Someone"


def _is_call_notification(payload_bytes):
    """Returns True if the notification payload is about an incoming call."""
    if not payload_bytes:
        return False
    try:
        text = payload_bytes.decode("utf-8", errors="ignore") \
            if isinstance(payload_bytes, bytes) else str(payload_bytes)
        keywords = ["incoming call", "is calling", "calling you", "phone call", "incomingcall"]
        return any(kw in text.lower() for kw in keywords)
    except:
        return False


def _poll_loop():
    global _pending_call
    print("[NOTIF] Phone Link watcher started.")
    while _watching:
        try:
            rows = _copy_and_read_db()
            for (nid, handler, payload, arrival) in rows:
                if nid in _seen_ids:
                    continue
                _seen_ids.add(nid)

                if _is_call_notification(payload):
                    caller = _extract_caller(payload)
                    _pending_call = caller
                    print(f"[NOTIF] Incoming call detected from: {caller}")
                    if _call_callback:
                        _call_callback(caller)
        except Exception as e:
            print(f"[NOTIF] Poll error: {e}")

        time.sleep(3)


def start_watching():
    """Start the background notification watcher thread."""
    global _watching
    if _watching:
        return
    _watching = True
    t = threading.Thread(target=_poll_loop, daemon=True)
    t.start()


def stop_watching():
    global _watching
    _watching = False
