import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import os
import requests
import time
import threading
import random
import wikipedia
import re


from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from hologram_ui import HologramUI
import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from voice_auth import verify_voice
import time as t
# ---------------- AI AGENT CONFIG ----------------
N8N_WEBHOOK_URL = "https://jaithra.app.n8n.cloud/webhook/2d18b019-ffb8-42c2-98bb-7260caeaf204"
SESSION_ID = "jaithra_main"

def ask_ai_agent(message):
    try:
        payload = {
            "message": message,
            "sessionId": SESSION_ID
        }

        print("Sending to:", N8N_WEBHOOK_URL)
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)

        print("Status Code:", response.status_code)
        print("RAW RESPONSE:", response.text)

        data = response.json()
        return data.get("reply", "Sorry, I couldn't process that.")

    except Exception as e:
        print("AI Agent Error:", e)
        return "I am having trouble connecting to my brain."
# Initialize voice engine
friday = pyttsx3.init()
friday.setProperty('rate', 165)

try:
    voices = friday.getProperty('voices')
    female_voices = [v for v in voices if 'female' in v.name.lower()]
    friday.setProperty('voice', female_voices[0].id if female_voices else voices[0].id)
except Exception as e:
    print(f"Voice selection error: {e}")

WEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"
NEWS_API_KEY = "YOUR_NEWSAPI_KEY"
MUSIC_DIR = "C:/Music"
conversation_context = {}
reminders = []

ui = HologramUI()
ui.show()

assistant_running = True

def speak(text, priority=False):
    print(f"Friday: {text}")
    ui.update_status(text)
    ui.set_state("speaking")

    friday.say(text)
    friday.runAndWait()

    ui.set_state("idle")

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            r.adjust_for_ambient_noise(source, duration=0.5)
            ui.set_state("listening")  # 🔥 listening glow
            print("Listening...")
            audio = r.listen(source, timeout=5, phrase_time_limit=7)
        except sr.WaitTimeoutError:
            ui.set_state("idle")
            return ""

    try:
        command = r.recognize_google(audio).lower()
        ui.set_state("idle")  # 🔥 stop listening glow
        ui.update_status("💬 Responding...")
        print(f"You: {command}")
        conversation_context["last_command"] = command
        return command
    except:
        ui.set_state("idle")
        return ""

def greet():
    speak("Hello sir, I am Friday. How can I help you?")
    ui.update_status("👋 Ready for commands")

def search_web(query):
    search_url = f"https://www.google.com/search?q={quote_plus(query)}"
    webbrowser.open(search_url)
    return f"Searching Google for {query}"

def evaluate_math(expression):
    try:
        expression = expression.replace("x", "*").replace("divided by", "/")
        expression = expression.replace("to the power of", "**")
        expression = re.sub(r'[^0-9\+\-\*/\(\)\.\s\^]', '', expression)
        result = eval(expression)
        return f"The answer is {result}"
    except ZeroDivisionError:
        return "You can't divide by zero."
    except:
        return None

def get_summary_from_wikipedia(query):
    try:
        summary = wikipedia.summary(query, sentences=2)
        return summary
    except:
        return "Sorry, I couldn't find anything relevant."

def handle_command(cmd):
    global assistant_running
    if any(op in cmd for op in ["+", "-", "x", "times", "to the power of", "divided by"]):
        result = evaluate_math(cmd)
        if result:
            speak(result)
            return

    if "time" in cmd:
        speak("It's " + datetime.datetime.now().strftime("%I:%M %p"))
    elif "date" in cmd:
        speak("Today is " + datetime.datetime.now().strftime("%A, %B %d, %Y"))
    elif "play" in cmd and "youtube" in cmd:
        query = cmd.split("play")[-1].replace("on youtube", "").replace("youtube", "").strip()
        play_youtube_video(query)
    elif "open youtube" in cmd or ("youtube" in cmd and "open" in cmd):
        webbrowser.open("https://youtube.com")
        speak("Opening YouTube")
    elif "search for" in cmd:
        query = cmd.split("search for")[-1].strip()
        speak(search_web(query))
    elif "weather" in cmd:
        city = cmd.split("in")[-1].strip() if "in" in cmd else "New York"
        speak(get_weather(city))
    elif "news" in cmd:
        topic = "sports" if "sports" in cmd else "technology" if "tech" in cmd else "general"
        speak(get_news(topic))
    elif "remind me to" in cmd:
        try:
            parts = cmd.split("remind me to")[1].split("in")
            task = parts[0].strip()
            mins = int(''.join(filter(str.isdigit, parts[1])))
            speak(set_reminder(task, mins))
        except:
            speak("Try saying: remind me to take medicine in 30 minutes")
    elif "list reminders" in cmd:
        if reminders:
            for r in reminders:
                speak(f"At {r['time']}: {r['text']}")
        else:
            speak("No reminders set.")
    elif "shutdown" in cmd:
        speak("Shutting down.")
        os.system("shutdown /s /t 1")
    elif "restart" in cmd:
        speak("Restarting.")
        os.system("shutdown /r /t 1")
    elif "bye" in cmd or "exit" in cmd or "goodbye" in cmd:
        speak("Goodbye sir, I’ll be listening in the background.")
        ui.update_status("💤 Sleeping...")
        time.sleep(2)
        os._exit(0)  # Only exits this layer, not the background

    else:
    # Send unknown queries to AI Agent (n8n brain)
        ai_reply = ask_ai_agent(cmd)
        speak(ai_reply)

def get_weather(city="New York"):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()
        if data["cod"] != "404":
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            return f"In {city}, it's {temp}°C with {desc}."
    except:
        return f"Couldn't fetch weather for {city}"

def get_news(topic="general"):
    try:
        url = f"https://newsapi.org/v2/top-headlines?q={topic}&apiKey={NEWS_API_KEY}&pageSize=3"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "ok":
            return ". ".join([article["title"] for article in data["articles"]])
    except:
        return "Couldn't fetch news"

def set_reminder(text, delay_min):
    time_str = (datetime.datetime.now() + datetime.timedelta(minutes=delay_min)).strftime("%I:%M %p")
    reminders.append({"text": text, "time": time_str})
    threading.Timer(delay_min * 60, lambda: speak(f"⏰ Reminder: {text}", priority=True)).start()
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
        speak("Something went wrong trying to play the video.")
        print(e)

def background_tasks():
    while True:
        now = datetime.datetime.now().strftime("%I:%M %p")
        for r in reminders[:]:
            if r["time"] == now:
                speak(f"⏰ Reminder: {r['text']}", priority=True)
                reminders.remove(r)
        time.sleep(20)
if __name__ == "__main__":
    threading.Thread(target=background_tasks, daemon=True).start()
    ui.update_status("🎤 Say your passphrase to activate Friday")
    speak("Please say your passphrase to continue")

    while not verify_voice():
        speak("Access denied. Please try again.")
        ui.update_status("❌ Access denied")
        time.sleep(1)

    speak("Welcome back sir")
    ui.update_status("✅ Authenticated. Welcome back!")

    def voice_loop():
        greet()
        while assistant_running:
            command = listen()
            if command:
                handle_command(command)

    threading.Thread(target=voice_loop, daemon=True).start()
    sys.exit(app.exec())
