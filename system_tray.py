"""
system_tray.py — Windows system tray icon for Friday.
Runs silently in the background. Right-click to show/exit.
"""
import sys
import os
import threading
import subprocess
from PIL import Image, ImageDraw
import pystray

FRIDAY_DIR    = os.path.dirname(os.path.abspath(__file__))
FRIDAY_SCRIPT = os.path.join(FRIDAY_DIR, "friday.pyw")

_friday_proc = None


def _create_icon_image():
    """Generate a cyan arc-reactor style tray icon."""
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer ring
    draw.ellipse([2, 2, 61, 61], outline=(0, 220, 255), width=3)
    # Middle ring
    draw.ellipse([12, 12, 51, 51], outline=(0, 180, 220), width=2)
    # Inner glow
    draw.ellipse([22, 22, 41, 41], fill=(0, 220, 255), outline=(0, 255, 255), width=1)
    # Center dot
    draw.ellipse([28, 28, 35, 35], fill=(255, 255, 255))
    return img


def _launch_friday():
    global _friday_proc
    if _friday_proc and _friday_proc.poll() is None:
        print("[TRAY] Friday is already running.")
        return
    print("[TRAY] Launching Friday...")
    _friday_proc = subprocess.Popen(
        [sys.executable, FRIDAY_SCRIPT],
        cwd=FRIDAY_DIR
    )


def _stop_friday():
    global _friday_proc
    if _friday_proc and _friday_proc.poll() is None:
        _friday_proc.terminate()
        _friday_proc = None
        print("[TRAY] Friday stopped.")


def _on_show(icon, item):
    _launch_friday()


def _on_exit(icon, item):
    _stop_friday()
    icon.stop()
    os._exit(0)


def run_tray():
    """Create and run the system tray icon. Blocks until exit."""
    icon_img = _create_icon_image()

    menu = pystray.Menu(
        pystray.MenuItem("Show Friday", _on_show, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", _on_exit),
    )

    icon = pystray.Icon(
        name="Friday",
        icon=icon_img,
        title="Friday AI Assistant",
        menu=menu
    )

    print("[TRAY] System tray started. Double-click or right-click the icon.")
    icon.run()


if __name__ == "__main__":
    run_tray()
