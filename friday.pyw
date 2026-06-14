import sys
import os

# Force UTF-8 output so special chars don't crash on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import re
import json
import time
import threading
import datetime
import webbrowser
import requests
import wikipedia

import speech_recognition as sr
import pyttsx3

from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

from hologram_ui       import HologramUI
from fullscreen_ui     import FullscreenUI
from voice_auth        import verify_voice
import pc_control
import doc_handler
import mobile_sender
import notification_watcher

import time as t

# ────────────────────────────────────────────────────────────────────────────
#  PREFERENCES
# ────────────────────────────────────────────────────────────────────────────

def _load_prefs():
    try:
        with open("chira_preferences.json") as f:
            return json.load(f)
    except:
        return {}

prefs       = _load_prefs()
DEFAULT_CITY = prefs.get("city", "Hyderabad")

# ────────────────────────────────────────────────────────────────────────────
#  AI CONFIG
# ────────────────────────────────────────────────────────────────────────────

# API keys loaded from chira_preferences.json (NEVER hardcode here)
GEMINI_API_KEY = prefs.get("gemini_api_key", "YOUR_GEMINI_API_KEY")
GROQ_API_KEY   = prefs.get("groq_api_key",   "YOUR_GROQ_API_KEY")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"

WEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"
NEWS_API_KEY    = "YOUR_NEWSAPI_KEY"

FRIDAY_SYSTEM_PROMPT = (
    "You are Friday, a witty and highly intelligent AI assistant inspired by Iron Man's F.R.I.D.A.Y. "
    "You speak concisely and naturally like a real voice assistant, not a chatbot. "
    "Keep responses short (1-3 sentences max) unless the user explicitly asks for detail or a document. "
    "Address the user as 'sir'. Be helpful, smart, and occasionally add dry humour. "
    "When asked to create document content, use markdown headers (##), bullet points (-), and proper structure."
)

DOC_SYSTEM_PROMPT = (
    "You are Friday, an AI assistant. Generate comprehensive, well-structured document content. "
    "Use markdown: # for main title, ## for sections, ### for subsections, - for bullets. "
    "Be thorough and informative. Include introduction, main sections, and conclusion."
)

conversation_history = []
MAX_HISTORY = 10

# ────────────────────────────────────────────────────────────────────────────
#  UI
# ────────────────────────────────────────────────────────────────────────────

ui      = HologramUI()
fs_ui   = FullscreenUI()
ui.show()

# Wire maximize button → fullscreen
def _on_maximize():
    last_reply = conversation_history[-1]["text"] if conversation_history else "Friday is ready, sir."
    fs_ui.show_response(last_reply)

ui.maximize_callback = _on_maximize

assistant_running = True

# ────────────────────────────────────────────────────────────────────────────
#  VOICE ENGINE
# ────────────────────────────────────────────────────────────────────────────

friday_tts = pyttsx3.init()
friday_tts.setProperty('rate', 165)

try:
    voices = friday_tts.getProperty('voices')
    female = [v for v in voices if 'female' in v.name.lower()]
    friday_tts.setProperty('voice', female[0].id if female else voices[0].id)
except Exception as e:
    print(f"[TTS] Voice selection error: {e}")

conversation_context = {}
reminders = []

# ────────────────────────────────────────────────────────────────────────────
#  SPEAK / LISTEN
# ────────────────────────────────────────────────────────────────────────────

def speak(text, priority=False, show_fullscreen=False):
    print(f"Friday: {text}")
    ui.update_status(text)
    ui.set_state("speaking")

    if show_fullscreen:
        fs_ui.show_response(text)

    friday_tts.say(text)
    friday_tts.runAndWait()
    ui.set_state("idle")


def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            r.adjust_for_ambient_noise(source, duration=0.5)
            ui.set_state("listening")
            print("Listening...")
            audio = r.listen(source, timeout=5, phrase_time_limit=8)
        except sr.WaitTimeoutError:
            ui.set_state("idle")
            return ""
    try:
        command = r.recognize_google(audio).lower()
        ui.set_state("idle")
        ui.update_status("Responding...")
        print(f"You: {command}")
        conversation_context["last_command"] = command
        return command
    except:
        ui.set_state("idle")
        return ""


def greet():
    speak("Hello sir, I am Friday. All systems are online.")
    ui.update_status("Ready for commands")

# ────────────────────────────────────────────────────────────────────────────
#  REAL-TIME WEB SEARCH
# ────────────────────────────────────────────────────────────────────────────

REALTIME_KEYWORDS = [
    "today", "now", "latest", "current", "live", "recently", "just",
    "score", "result", "winner", "match", "final", "ipl", "cricket",
    "news", "happened", "who won", "standings", "2025", "2026",
    "weather", "stock", "price", "update", "election", "release",
    "trending", "launched", "announced"
]


def needs_realtime(text):
    t = text.lower()
    return any(kw in t for kw in REALTIME_KEYWORDS)


def fetch_web_context(query):
    try:
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        resp = requests.get(url, timeout=8, headers={"User-Agent": "FridayAssistant/1.0"})
        data = resp.json()
        snippets = []

        if data.get("AbstractText"):
            snippets.append(data["AbstractText"])
        for item in data.get("RelatedTopics", [])[:4]:
            if isinstance(item, dict) and item.get("Text"):
                snippets.append(item["Text"])

        if snippets:
            return " | ".join(snippets[:4])

        # HTML fallback
        import re as _re
        nr = requests.get(
            f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
            timeout=8, headers={"User-Agent": "Mozilla/5.0"}
        )
        hits = _re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', nr.text)
        if hits:
            clean = [_re.sub(r'<.*?>', '', h).strip() for h in hits[:3]]
            return " | ".join(clean)
    except Exception as e:
        print(f"[WEB SEARCH] {e}")
    return None

# ────────────────────────────────────────────────────────────────────────────
#  AI BRAIN
# ────────────────────────────────────────────────────────────────────────────

def ask_gemini(message, system_prompt=None):
    try:
        contents = []
        for turn in conversation_history[-MAX_HISTORY:]:
            contents.append({"role": turn["role"], "parts": [{"text": turn["text"]}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt or FRIDAY_SYSTEM_PROMPT}]},
            "contents": contents
        }
        resp = requests.post(GEMINI_URL, params={"key": GEMINI_API_KEY},
                             json=payload, timeout=20)
        resp.raise_for_status()
        parts = resp.json()["candidates"][0]["content"]["parts"]
        reply = " ".join(p.get("text", "") for p in parts).strip()
        print(f"[GEMINI] {reply[:80]}...")
        return reply
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        return None


def ask_groq(message, system_prompt=None):
    try:
        messages = [{"role": "system", "content": system_prompt or FRIDAY_SYSTEM_PROMPT}]
        for turn in conversation_history[-MAX_HISTORY:]:
            messages.append({"role": turn["role"], "content": turn["text"]})
        messages.append({"role": "user", "content": message})

        payload = {"model": GROQ_MODEL, "messages": messages,
                   "max_tokens": 1000, "temperature": 0.7}
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}",
                   "Content-Type": "application/json"}
        resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"].strip()
        print(f"[GROQ] {reply[:80]}...")
        return reply
    except Exception as e:
        print(f"[GROQ ERROR] {e}")
        return None


def ask_ai(message, system_prompt=None, for_doc=False):
    enriched = message

    if not for_doc and needs_realtime(message):
        ui.update_status("Searching the web...")
        context = fetch_web_context(message)
        if context:
            enriched = (
                f"[LIVE WEB DATA]: {context}\n\n"
                f"User question: {message}\n"
                f"Answer using the above data concisely."
            )

    conversation_history.append({"role": "user", "text": message})

    sp = DOC_SYSTEM_PROMPT if for_doc else (system_prompt or FRIDAY_SYSTEM_PROMPT)
    reply = ask_gemini(enriched, sp) or ask_groq(enriched, sp)

    if not reply:
        reply = get_summary_from_wikipedia(message)

    conversation_history.append({"role": "model", "text": reply})
    return reply

# ────────────────────────────────────────────────────────────────────────────
#  UTILITIES
# ────────────────────────────────────────────────────────────────────────────

def search_web(query):
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Searching Google for {query}"


def evaluate_math(expression):
    try:
        expression = expression.replace("x", "*").replace("divided by", "/")
        expression = expression.replace("to the power of", "**")
        expression = re.sub(r'[^0-9\+\-\*/\(\)\.\s\^]', '', expression)
        return f"The answer is {eval(expression)}"
    except ZeroDivisionError:
        return "You can't divide by zero."
    except:
        return None


def get_summary_from_wikipedia(query):
    try:
        return wikipedia.summary(query, sentences=2)
    except:
        return "Sorry, I couldn't find anything relevant."


def get_weather(city=None):
    city = city or DEFAULT_CITY
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        data = requests.get(url).json()
        if data.get("cod") != "404":
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            return f"In {city}, it's {temp}°C with {desc}."
    except:
        pass
    return f"Couldn't fetch weather for {city}."


def get_news(topic="general"):
    try:
        url = f"https://newsapi.org/v2/top-headlines?q={topic}&apiKey={NEWS_API_KEY}&pageSize=3"
        data = requests.get(url).json()
        if data.get("status") == "ok":
            return ". ".join(a["title"] for a in data["articles"])
    except:
        pass
    return "Couldn't fetch news."


def set_reminder(text, delay_min):
    time_str = (datetime.datetime.now() + datetime.timedelta(minutes=delay_min)).strftime("%I:%M %p")
    reminders.append({"text": text, "time": time_str})
    threading.Timer(delay_min * 60, lambda: speak(f"[REMINDER] {text}", priority=True)).start()
    return f"Reminder set for {time_str}"


def play_youtube_video(query):
    try:
        options = Options()
        options.add_argument("--disable-infobars")
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        options.add_argument("--start-maximized")
        driver = webdriver.Chrome(options=options)
        driver.get(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
        t.sleep(3)
        first_video = driver.find_element(By.ID, "video-title")
        driver.execute_script("arguments[0].click();", first_video)
        t.sleep(2)
        driver.execute_script("document.querySelector('video').muted = false;")
        driver.execute_script("document.querySelector('video').play();")
        speak(f"Playing {query} on YouTube.")
    except Exception as e:
        speak("Something went wrong with YouTube.")
        print(e)

# ────────────────────────────────────────────────────────────────────────────
#  COMMAND HANDLER
# ────────────────────────────────────────────────────────────────────────────

_last_created_doc   = None   # track last doc path for "send this"
_last_screenshot    = None   # track last screenshot path

def handle_command(cmd):
    global assistant_running, _last_created_doc, _last_screenshot

    # ── Math ──────────────────────────────────────────────────────────────
    if any(op in cmd for op in ["+", "-", "x", "times", "to the power of", "divided by"]):
        result = evaluate_math(cmd)
        if result:
            speak(result)
            return

    # ── Time / Date ───────────────────────────────────────────────────────
    if "time" in cmd and "youtube" not in cmd:
        speak("It's " + datetime.datetime.now().strftime("%I:%M %p"))

    elif "date" in cmd:
        speak("Today is " + datetime.datetime.now().strftime("%A, %B %d, %Y"))

    # ── PC Control ────────────────────────────────────────────────────────
    elif any(k in cmd for k in ["open recent", "recent doc", "recent file", "recently opened"]):
        result = pc_control.open_recent_docs()
        speak(result)

    elif "open" in cmd and any(app in cmd for app in pc_control.APP_MAP):
        app_name = next((app for app in pc_control.APP_MAP if app in cmd), None)
        if app_name:
            pc_control.open_app(app_name)
            speak(f"Opening {app_name}, sir.")

    elif "screenshot" in cmd or "screen shot" in cmd:
        path = pc_control.take_screenshot()
        _last_screenshot = path
        speak("Screenshot taken and saved to your Desktop, sir.")

    elif "lock" in cmd and ("pc" in cmd or "computer" in cmd or "screen" in cmd):
        speak("Locking your PC, sir.")
        pc_control.lock_pc()

    elif "sleep" in cmd and ("pc" in cmd or "computer" in cmd):
        speak("Putting your PC to sleep, sir.")
        pc_control.sleep_pc()

    elif "volume up" in cmd or "increase volume" in cmd or "louder" in cmd:
        result = pc_control.set_volume(action="up")
        speak(result or "Volume increased.")

    elif "volume down" in cmd or "decrease volume" in cmd or "quieter" in cmd:
        result = pc_control.set_volume(action="down")
        speak(result or "Volume decreased.")

    elif "mute" in cmd and "unmute" not in cmd:
        pc_control.set_volume(action="mute")
        speak("Muted.")

    elif "unmute" in cmd:
        pc_control.set_volume(action="unmute")
        speak("Unmuted.")

    # ── Document Automation ───────────────────────────────────────────────
    elif any(k in cmd for k in ["make a doc", "create a doc", "write a doc",
                                 "make a document", "create a document",
                                 "make a file", "write about", "make a report"]):
        topic = ""
        for split_word in ["about", "on", "for", "regarding"]:
            if split_word in cmd:
                topic = cmd.split(split_word, 1)[-1].strip()
                break
        if not topic:
            topic = re.sub(
                r"(make|create|write|a|doc|document|file|report|detailed|full|info)",
                "", cmd
            ).strip()
        if not topic:
            speak("What topic should I write about, sir?")
            topic = listen()
        if topic:
            speak(f"Generating a document about {topic}. Give me a moment, sir.")
            ui.update_status(f"Writing doc: {topic}...")
            content = ask_ai(
                f"Write a comprehensive, well-structured document about: {topic}. "
                f"Include an introduction, main sections with ## headers, bullet points, and a conclusion.",
                for_doc=True
            )
            path = doc_handler.create_doc_from_content(topic.title(), content, open_after=True)
            _last_created_doc = path
            speak(f"Document created and opened, sir. It's saved as {os.path.basename(path)}.")

    elif "append" in cmd or ("add" in cmd and "doc" in cmd):
        text_to_add = cmd.replace("append", "").replace("add to doc", "").replace("add to the doc", "").strip()
        if not text_to_add:
            speak("What should I add to the document, sir?")
            text_to_add = listen()
        path = doc_handler.append_to_last_doc(text_to_add)
        if path:
            speak("Added to the document, sir.")
        else:
            speak("No document found to append to, sir.")

    # ── Mobile Sending ────────────────────────────────────────────────────
    elif any(k in cmd for k in ["send to my mobile", "send to my phone", "send this to mobile",
                                  "send to telegram", "send by email", "send this",
                                  "send it to my phone", "send it to mobile"]):
        # Determine what to send
        target_path = None
        if _last_screenshot and "screenshot" in cmd:
            target_path = _last_screenshot
        elif _last_created_doc:
            target_path = _last_created_doc
        else:
            target_path = doc_handler.get_last_created_doc()

        if target_path and os.path.exists(target_path):
            speak(f"Sending {os.path.basename(target_path)} to your mobile, sir.")
            result = mobile_sender.send_to_mobile(filepath=target_path)
            speak(result)
        else:
            speak("Nothing to send. Try taking a screenshot or creating a document first, sir.")

    elif "send message" in cmd or "send text" in cmd:
        msg = cmd.replace("send message", "").replace("send text", "").strip()
        if not msg:
            speak("What message should I send, sir?")
            msg = listen()
        result = mobile_sender.send_to_mobile(text=msg)
        speak(result)

    # ── Fullscreen / UI ───────────────────────────────────────────────────
    elif any(k in cmd for k in ["big screen", "full screen", "fullscreen", "maximize",
                                  "show me on screen", "show on big", "large screen"]):
        last_reply = conversation_history[-1]["text"] if conversation_history else "Friday is ready, sir."
        fs_ui.show_response(last_reply)
        speak("Showing on the big screen, sir.")

    elif any(k in cmd for k in ["minimize", "small screen", "close screen",
                                  "close fullscreen", "close the screen"]):
        fs_ui.hide_overlay()
        speak("Minimized, sir.")

    # ── Phone call responses ──────────────────────────────────────────────
    elif any(k in cmd for k in ["pick up", "answer the call", "yes pick",
                                  "pick the call", "answer call"]):
        notification_watcher.clear_pending_call()
        pc_control.answer_phone_link_call()
        speak("Opening the call for you, sir.")

    elif any(k in cmd for k in ["reject", "decline", "no reject", "ignore the call"]):
        notification_watcher.clear_pending_call()
        pc_control.dismiss_phone_link_call()
        speak("Call declined, sir.")

    # ── YouTube ───────────────────────────────────────────────────────────
    elif "play" in cmd and "youtube" in cmd:
        query = cmd.split("play")[-1].replace("on youtube", "").replace("youtube", "").strip()
        play_youtube_video(query)

    elif "open youtube" in cmd or ("youtube" in cmd and "open" in cmd):
        webbrowser.open("https://youtube.com")
        speak("Opening YouTube, sir.")

    # ── Web search ────────────────────────────────────────────────────────
    elif "search for" in cmd or "search" in cmd and "google" in cmd:
        query = cmd.split("search for")[-1].strip() if "search for" in cmd \
                else cmd.split("search")[-1].strip()
        speak(search_web(query))

    # ── Weather ───────────────────────────────────────────────────────────
    elif "weather" in cmd:
        city = cmd.split("in")[-1].strip() if " in " in cmd else DEFAULT_CITY
        speak(get_weather(city))

    # ── News ──────────────────────────────────────────────────────────────
    elif "news" in cmd:
        topic = "sports" if "sports" in cmd else "technology" if "tech" in cmd else "general"
        speak(get_news(topic))

    # ── Reminders ─────────────────────────────────────────────────────────
    elif "remind me to" in cmd:
        try:
            parts = cmd.split("remind me to")[1].split(" in ")
            task = parts[0].strip()
            mins = int(''.join(filter(str.isdigit, parts[1])))
            speak(set_reminder(task, mins))
        except:
            speak("Try: remind me to take medicine in 30 minutes.")

    elif "list reminders" in cmd:
        if reminders:
            for r in reminders:
                speak(f"At {r['time']}: {r['text']}")
        else:
            speak("No reminders set, sir.")

    # ── Power ─────────────────────────────────────────────────────────────
    elif "shutdown" in cmd and "pc" in cmd:
        speak("Shutting down in 5 seconds, sir.")
        pc_control.shutdown_pc()

    elif "restart" in cmd and "pc" in cmd:
        speak("Restarting in 5 seconds, sir.")
        pc_control.restart_pc()

    elif "bye" in cmd or "exit" in cmd or "goodbye" in cmd:
        speak("Goodbye sir. I'll keep running in the background.")
        ui.update_status("Sleeping...")
        time.sleep(2)
        os._exit(0)

    # ── AI Brain (fallback) ───────────────────────────────────────────────
    else:
        ai_reply = ask_ai(cmd)
        # Show long replies on big screen automatically
        show_big = len(ai_reply) > 200
        speak(ai_reply, show_fullscreen=show_big)

# ────────────────────────────────────────────────────────────────────────────
#  BACKGROUND TASKS
# ────────────────────────────────────────────────────────────────────────────

def background_tasks():
    while True:
        now = datetime.datetime.now().strftime("%I:%M %p")
        for r in reminders[:]:
            if r["time"] == now:
                speak(f"[REMINDER] {r['text']}", priority=True)
                reminders.remove(r)
        time.sleep(20)


def on_incoming_call(caller_name):
    """Called by notification_watcher when Phone Link detects a call."""
    msg = f"Sir, {caller_name} is calling you. Should I pick up or decline?"
    speak(msg, show_fullscreen=True)
    ui.update_status(f"Incoming call: {caller_name}")

# ────────────────────────────────────────────────────────────────────────────
#  MAIN
# ────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Start background threads
    threading.Thread(target=background_tasks, daemon=True).start()

    # Start Phone Link call watcher
    notification_watcher.set_call_callback(on_incoming_call)
    notification_watcher.start_watching()

    # Voice authentication
    ui.update_status("Say your passphrase to activate Friday")
    speak("Please say your passphrase to continue.")

    while not verify_voice():
        speak("Access denied. Please try again.")
        ui.update_status("Access denied")
        time.sleep(1)

    speak("Welcome back sir. All systems online.", show_fullscreen=False)
    ui.update_status("Authenticated. All systems online.")

    def voice_loop():
        greet()
        while assistant_running:
            command = listen()
            if command:
                handle_command(command)

    threading.Thread(target=voice_loop, daemon=True).start()
    sys.exit(app.exec())
