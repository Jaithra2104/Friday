"""
main_runner.py — Wake-word listener for Friday.
Runs silently in background, listens for "hello friday",
then launches friday.pyw.
"""
import sys
import os
import subprocess
import speech_recognition as sr

# Force UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FRIDAY_DIR    = os.path.dirname(os.path.abspath(__file__))
FRIDAY_SCRIPT = os.path.join(FRIDAY_DIR, "friday.pyw")

_friday_proc = None


def run_friday():
    global _friday_proc
    try:
        _friday_proc = subprocess.run(
            [sys.executable, FRIDAY_SCRIPT],
            cwd=FRIDAY_DIR,
            check=True
        )
    except Exception as e:
        print(f"[ERROR] Failed to run Friday: {e}")


def listen_for_wake_word():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    print("[MIC] Waiting for 'hello friday'...")

    while True:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                command = recognizer.recognize_google(audio).lower()
                print(f"Heard: {command}")

                if "hello friday" in command or "hey friday" in command:
                    print("[OK] Wake word detected. Starting Friday...")
                    run_friday()
                    print("Friday closed. Listening again...")
                    print("[MIC] Waiting for 'hello friday'...")

            except sr.UnknownValueError:
                pass
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print(f"[ERROR] {e}")


if __name__ == "__main__":
    listen_for_wake_word()
