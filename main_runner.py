import subprocess
import time
import speech_recognition as sr

def listen_for_wake_word():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    print("🎤 Waiting for 'hello friday'...")

    while True:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                command = recognizer.recognize_google(audio).lower()
                print(f"You said: {command}")
                if "hello friday" in command:
                    print("✅ Wake word detected. Starting Friday...")

                    # 🛑 Stop listening while Friday runs
                    run_friday()

                    print("🌀 Friday closed. Listening again...\n")
                    print("🎤 Waiting for 'hello friday'...")

            except sr.UnknownValueError:
                pass
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print("Error:", e)

def run_friday():
    try:
        subprocess.run(["C:\Users\jaith\OneDrive\Desktop\friday"], check=True)
    except Exception as e:
        print("❌ Failed to run Friday:", e)

if __name__ == "__main__":
    listen_for_wake_word()
