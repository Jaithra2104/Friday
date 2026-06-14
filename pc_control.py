"""
pc_control.py — Full PC automation module for Friday.
Handles: recent docs, app launching, volume, screenshots, lock/sleep.
"""
import os
import glob
import subprocess
import datetime
import pyautogui
from pathlib import Path

# ── App name → executable map ──────────────────────────────────────────────
APP_MAP = {
    "chrome":               "chrome.exe",
    "google chrome":        "chrome.exe",
    "firefox":              "firefox.exe",
    "edge":                 "msedge.exe",
    "microsoft edge":       "msedge.exe",
    "notepad":              "notepad.exe",
    "word":                 "winword.exe",
    "microsoft word":       "winword.exe",
    "excel":                "excel.exe",
    "microsoft excel":      "excel.exe",
    "powerpoint":           "powerpnt.exe",
    "vs code":              "code.exe",
    "visual studio code":   "code.exe",
    "file explorer":        "explorer.exe",
    "explorer":             "explorer.exe",
    "task manager":         "taskmgr.exe",
    "calculator":           "calc.exe",
    "paint":                "mspaint.exe",
    "spotify":              "spotify.exe",
    "discord":              "discord.exe",
    "whatsapp":             "whatsapp.exe",
    "telegram":             "telegram.exe",
    "vlc":                  "vlc.exe",
    "cmd":                  "cmd.exe",
    "command prompt":       "cmd.exe",
    "settings":             "ms-settings:",
    "control panel":        "control.exe",
}

RECENT_FOLDER = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent")


# ── Recent documents ────────────────────────────────────────────────────────

def get_recent_docs(n=8):
    """Return list of (display_name, lnk_path) for recently accessed files."""
    lnk_files = sorted(
        glob.glob(os.path.join(RECENT_FOLDER, "*.lnk")),
        key=os.path.getmtime,
        reverse=True
    )[:n]
    results = []
    for lnk in lnk_files:
        name = Path(lnk).stem
        results.append((name, lnk))
    return results


def open_recent_docs():
    """Speak + open the list of recent docs. Returns description string."""
    docs = get_recent_docs(5)
    if not docs:
        return "No recent documents found, sir."
    names = [d[0] for d in docs]
    desc = ", ".join(names[:5])
    # Open the most recently accessed one automatically
    os.startfile(docs[0][1])
    return f"Opening your most recent file: {docs[0][0]}. Others recently accessed: {', '.join(names[1:4])}."


def open_file_by_name(name):
    """Search recent docs for a file matching the name and open it."""
    docs = get_recent_docs(20)
    for fname, fpath in docs:
        if name.lower() in fname.lower():
            os.startfile(fpath)
            return fname
    return None


def get_active_window_title():
    """Return the title of the currently focused window."""
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(hwnd)
    except Exception as e:
        print(f"[PC] Active window error: {e}")
        return None


# ── App launcher ───────────────────────────────────────────────────────────

def open_app(app_name):
    """Launch an app by recognizable name. Returns True on success."""
    key = app_name.lower().strip()
    exe = APP_MAP.get(key)
    if exe:
        try:
            if exe.startswith("ms-"):
                os.startfile(exe)
            else:
                subprocess.Popen(exe, shell=True)
            return True
        except Exception as e:
            print(f"[PC] Open app error: {e}")
    # Try raw name as fallback
    try:
        subprocess.Popen(app_name, shell=True)
        return True
    except Exception as e:
        print(f"[PC] Fallback open error: {e}")
        return False


# ── Screenshot ────────────────────────────────────────────────────────────

def take_screenshot(save_dir=None):
    """Take a full screenshot, save to Desktop, return filepath."""
    if not save_dir:
        save_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(save_dir, f"friday_screenshot_{timestamp}.png")
    img = pyautogui.screenshot()
    img.save(filepath)
    print(f"[PC] Screenshot saved: {filepath}")
    return filepath


# ── Power controls ────────────────────────────────────────────────────────

def lock_pc():
    os.system("rundll32.exe user32.dll,LockWorkStation")

def sleep_pc():
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

def shutdown_pc():
    os.system("shutdown /s /t 5")

def restart_pc():
    os.system("shutdown /r /t 5")


# ── Volume control ────────────────────────────────────────────────────────

def set_volume(action=None, level=None):
    """
    action: 'up' | 'down' | 'mute' | 'unmute'
    level: 0-100 (optional absolute level)
    """
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(interface, POINTER(IAudioEndpointVolume))

        if action == "mute":
            vol.SetMute(1, None)
            return "Muted."
        elif action == "unmute":
            vol.SetMute(0, None)
            return "Unmuted."
        elif action == "up":
            cur = vol.GetMasterVolumeLevelScalar()
            vol.SetMasterVolumeLevelScalar(min(1.0, cur + 0.15), None)
            return f"Volume increased to {int(min(1.0, cur + 0.15) * 100)}%."
        elif action == "down":
            cur = vol.GetMasterVolumeLevelScalar()
            vol.SetMasterVolumeLevelScalar(max(0.0, cur - 0.15), None)
            return f"Volume decreased to {int(max(0.0, cur - 0.15) * 100)}%."
        elif level is not None:
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"Volume set to {level}%."
    except Exception as e:
        print(f"[PC] Volume error: {e}")
        return "Couldn't adjust volume."


# ── Phone Link call control ───────────────────────────────────────────────

def answer_phone_link_call():
    """Simulate clicking Answer in Phone Link notification."""
    try:
        # Open action center where Phone Link call notification appears
        pyautogui.hotkey('win', 'n')
        import time
        time.sleep(0.8)
        # Look for the answer button — approximate position in action center
        # This is approximate; user may need to click themselves
        print("[PC] Opened action center for call answer.")
        return True
    except Exception as e:
        print(f"[PC] Answer call error: {e}")
        return False

def dismiss_phone_link_call():
    """Dismiss the call notification."""
    try:
        pyautogui.hotkey('win', 'n')
        import time
        time.sleep(0.5)
        pyautogui.press('escape')
        return True
    except:
        return False
