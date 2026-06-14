# F.R.I.D.A.Y — AI Desktop Assistant

> *"Good morning. I am Friday, your personal AI assistant."*

A fully-featured Iron Man–inspired voice assistant for Windows, powered by **Gemini 2.0 Flash** and **Groq (LLaMA 3)** with real-time web search, full PC control, document automation, and mobile integration.

---

## Features

| Category | Capabilities |
|---|---|
| **Voice Auth** | Offline passphrase gate via Vosk (Indian English model) |
| **AI Brain** | Gemini 2.0 Flash (primary) → Groq LLaMA 3 (fallback) → Wikipedia |
| **Real-time Info** | DuckDuckGo search injected into prompts for live answers |
| **PC Control** | Open apps, recent docs, volume, screenshot, lock/sleep |
| **Document AI** | Creates styled Word docs from AI-generated content |
| **File Analysis** | Analyzes PDF, DOCX, Excel, TXT, images with AI |
| **Mobile Send** | Sends files & messages via Telegram Bot + Gmail |
| **Smart Reminders** | Persistent reminders → sent to phone even if PC is off |
| **Phone Calls** | Detects Phone Link incoming calls, announces caller |
| **Hologram UI** | PySide6 animated arc-reactor overlay with fullscreen mode |
| **System Tray** | Runs silently in background, wakes on "hello friday" |

---

## Project Structure

```
friday/
├── friday.pyw              # Main assistant brain
├── main_runner.py          # Wake-word listener (background)
├── system_tray.py          # Windows system tray app
├── hologram_ui.py          # Animated PySide6 hologram widget
├── fullscreen_ui.py        # Full-screen answer overlay
├── floating_ui.py          # Legacy Tkinter UI (kept for reference)
├── voice_auth.py           # Vosk offline passphrase auth
├── pc_control.py           # PC automation (apps, volume, etc.)
├── doc_handler.py          # Word document creation
├── file_analyzer.py        # File reading + AI analysis
├── mobile_sender.py        # Telegram + Email sender
├── reminder_store.py       # Persistent reminder storage
├── notification_watcher.py # Phone Link call detector
├── chira_preferences.json  # User config (fill in your keys)
└── vosk-model-small-en-in-0.4/  # Offline speech model
```

---

## Setup

### 1. Install dependencies
```bash
pip install speechrecognition pyttsx3 wikipedia requests selenium PySide6 vosk pyaudio pillow pystray pyautogui python-docx pycaw comtypes pywin32 pdfplumber openpyxl
```

### 2. Configure `chira_preferences.json`
```json
{
  "city": "Your City",
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "email_sender": "your@gmail.com",
  "email_password": "YOUR_APP_PASSWORD",
  "email_receiver": "your_phone@gmail.com",
  "docs_folder": "C:/Users/YourName/Documents"
}
```

### 3. Set API keys in `friday.pyw`
```python
GEMINI_API_KEY = "your_gemini_key"   # https://aistudio.google.com/app/apikey
GROQ_API_KEY   = "your_groq_key"     # https://console.groq.com/keys
```

### 4. Download Vosk model
Download [vosk-model-small-en-in-0.4](https://alphacephei.com/vosk/models) and place in project root.

### 5. Download ChromeDriver
For YouTube playback, download [ChromeDriver](https://chromedriver.chromium.org/) matching your Chrome version.

---

## Running

**Option A — Wake word (recommended):**
```bash
python main_runner.py
```
Say `"hello friday"` → passphrase prompt → Friday activates.

**Option B — Direct launch:**
```bash
python friday.pyw
```

**Option C — System tray (silent background):**
```bash
python system_tray.py
```
Right-click the cyan tray icon → Show Friday.

---

## Voice Commands

| Say this | Action |
|---|---|
| `"open recent documents"` | Opens your most recently accessed file |
| `"open Chrome / Word / VS Code"` | Launches the app |
| `"take a screenshot"` | Saved to Desktop, can be sent to mobile |
| `"make a doc about [topic]"` | AI writes a Word document and opens it |
| `"analyze this file"` | Opens file picker → AI analyzes content |
| `"send this to my mobile"` | Sends last doc/screenshot via Telegram + Email |
| `"show me on big screen"` | Full-screen overlay with last AI answer |
| `"remind me to X in 30 minutes"` | Persistent reminder, sent to phone when it fires |
| `"list my reminders"` | Reads all pending reminders |
| `"volume up / down / mute"` | System volume control |
| `"lock my PC"` | Locks the workstation |
| `"pick up"` / `"reject"` | Answer/decline Phone Link calls |
| `"is RCB in the IPL finals?"` | Live web search via DuckDuckGo + AI answer |

---

## Telegram Bot Setup (5 minutes)

1. Open Telegram → message `@BotFather` → `/newbot` → follow steps → copy token
2. Message `@userinfobot` → copy your chat ID
3. Paste both into `chira_preferences.json`

## Gmail App Password

1. Google Account → Security → 2-Step Verification (enable)
2. App Passwords → Generate for "Mail" → copy the 16-char password
3. Paste as `email_password` in `chira_preferences.json`

---

## Architecture

```
Windows Boot
    └── system_tray.py / main_runner.py (background, silent)
            │ "hello friday"
            ▼
        voice_auth.py (Vosk passphrase)
            │ authenticated
            ▼
        friday.pyw (AI brain)
        ├── pc_control.py       — PC automation
        ├── doc_handler.py      — Document creation
        ├── file_analyzer.py    — File analysis
        ├── mobile_sender.py    — Telegram + Email
        ├── reminder_store.py   — Persistent reminders
        ├── notification_watcher.py — Phone calls
        ├── ask_ai()            — Gemini → Groq → Wikipedia
        └── fetch_web_context() — DuckDuckGo real-time search

        hologram_ui.py  — Animated arc-reactor widget
        fullscreen_ui.py — Full-screen answer overlay
```

---

## License

MIT — Built with love by Jaithra.
