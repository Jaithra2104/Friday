"""
mobile_sender.py — Send files and messages to mobile via Telegram Bot and Email.
"""
import os
import json
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders


def _load_config():
    try:
        with open("chira_preferences.json") as f:
            return json.load(f)
    except:
        return {}


# ── Telegram ──────────────────────────────────────────────────────────────

def send_telegram_message(text):
    """Send a plain text message via Telegram bot."""
    cfg = _load_config()
    token   = cfg.get("telegram_bot_token", "")
    chat_id = cfg.get("telegram_chat_id", "")

    if not token or not chat_id or "YOUR" in token:
        return False, "Telegram not configured in chira_preferences.json"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        if resp.ok:
            print("[TELEGRAM] Message sent.")
            return True, "Message sent via Telegram."
        return False, f"Telegram error: {resp.text}"
    except Exception as e:
        return False, f"Telegram exception: {e}"


def send_telegram_file(filepath, caption="Sent by Friday"):
    """Upload a file (doc, image, etc.) to Telegram."""
    cfg = _load_config()
    token   = cfg.get("telegram_bot_token", "")
    chat_id = cfg.get("telegram_chat_id", "")

    if not token or not chat_id or "YOUR" in token:
        return False, "Telegram not configured"

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(filepath, "rb") as f:
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (os.path.basename(filepath), f)},
                timeout=30
            )
        if resp.ok:
            print(f"[TELEGRAM] File sent: {filepath}")
            return True, "File sent via Telegram."
        return False, f"Telegram error: {resp.text}"
    except Exception as e:
        return False, f"Telegram exception: {e}"


def send_telegram_photo(filepath, caption="Screenshot from Friday"):
    """Send an image as a photo (compressed) via Telegram."""
    cfg = _load_config()
    token   = cfg.get("telegram_bot_token", "")
    chat_id = cfg.get("telegram_chat_id", "")

    if not token or not chat_id or "YOUR" in token:
        return False, "Telegram not configured"

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(filepath, "rb") as f:
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": (os.path.basename(filepath), f)},
                timeout=20
            )
        if resp.ok:
            print(f"[TELEGRAM] Photo sent: {filepath}")
            return True, "Photo sent via Telegram."
        return False, f"Telegram error: {resp.text}"
    except Exception as e:
        return False, f"Telegram exception: {e}"


# ── Email (Gmail) ─────────────────────────────────────────────────────────

def send_email_file(filepath, subject=None, body=None):
    """Send a file as email attachment via Gmail SMTP."""
    cfg = _load_config()
    sender   = cfg.get("email_sender", "")
    password = cfg.get("email_password", "")
    receiver = cfg.get("email_receiver", "")

    if not all([sender, password, receiver]) or "YOUR" in sender:
        return False, "Email not configured in chira_preferences.json"

    if not subject:
        subject = f"Friday sent: {os.path.basename(filepath)}"
    if not body:
        body = "This file was sent by Friday, your AI desktop assistant."

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with open(filepath, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{os.path.basename(filepath)}"'
        )
        msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())

        print(f"[EMAIL] File sent to {receiver}")
        return True, f"Email sent to {receiver}."
    except Exception as e:
        return False, f"Email error: {e}"


def send_email_text(text, subject="Message from Friday"):
    """Send a plain text email."""
    cfg = _load_config()
    sender   = cfg.get("email_sender", "")
    password = cfg.get("email_password", "")
    receiver = cfg.get("email_receiver", "")

    if not all([sender, password, receiver]) or "YOUR" in sender:
        return False, "Email not configured"

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(text, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        return True, f"Email sent to {receiver}."
    except Exception as e:
        return False, f"Email error: {e}"


# ── Unified sender ────────────────────────────────────────────────────────

def send_to_mobile(filepath=None, text=None):
    """
    Send a file or text to mobile via both Telegram AND Email.
    Returns a human-readable status string for Friday to speak.
    """
    results = []

    if filepath and os.path.exists(filepath):
        ext = os.path.splitext(filepath)[1].lower()

        # Telegram
        if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
            ok, msg = send_telegram_photo(filepath)
        else:
            ok, msg = send_telegram_file(filepath)
        results.append(f"Telegram {'succeeded' if ok else 'failed'}")

        # Email
        ok2, msg2 = send_email_file(filepath)
        results.append(f"email {'succeeded' if ok2 else 'failed'}")

    elif text:
        ok, msg = send_telegram_message(text)
        results.append(f"Telegram {'succeeded' if ok else 'failed'}")

        ok2, msg2 = send_email_text(text)
        results.append(f"email {'succeeded' if ok2 else 'failed'}")

    else:
        return "Nothing to send, sir."

    return "Sent via " + " and ".join(results) + "."
