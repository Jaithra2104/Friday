import sys
import os

# Force UTF-8 output so emojis don't crash on Windows terminals
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from vosk import Model, KaldiRecognizer
import pyaudio
import json

def verify_voice():
    model_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "vosk-model-small-en-in-0.4",
        "vosk-model-small-en-in-0.4"
    )
    model = Model(model_path)
    rec = KaldiRecognizer(model, 16000)
    mic = pyaudio.PyAudio()

    stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
    stream.start_stream()

    print("[MIC] Say your passphrase (example: 'hello friday')...")

    attempts = 0
    while attempts < 5:
        data = stream.read(4096, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            spoken_text = result.get("text", "")
            print(f"[VOICE] You said: {spoken_text}")

            if "hello friday" in spoken_text.lower():
                print("[OK] Voice recognized")
                stream.stop_stream()
                stream.close()
                mic.terminate()
                return True
            else:
                print(f"[DENIED] Incorrect passphrase. Attempt {attempts + 1}/5")
                attempts += 1

    stream.stop_stream()
    stream.close()
    mic.terminate()
    return False
