from vosk import Model, KaldiRecognizer
import pyaudio
import json

def verify_voice():
    model = Model("vosk-model-small-en-in-0.4/vosk-model-small-en-in-0.4")  # Ensure the 'model' folder exists in the same directory
    rec = KaldiRecognizer(model, 16000)
    mic = pyaudio.PyAudio()

    stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
    stream.start_stream()

    print("🎙️ Say your password (example: 'hello friday')...")

    attempts = 0
    while attempts < 5:
        data = stream.read(4096, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            spoken_text = result.get("text", "")
            print(f"🗣️ You said: {spoken_text}")

            if "hello friday" in spoken_text.lower():
                print("✅ Voice recognized")
                stream.stop_stream()
                stream.close()
                mic.terminate()
                return True
            else:
                print("❌ Incorrect passphrase. Try again...")
                attempts += 1

    stream.stop_stream()
    stream.close()
    mic.terminate()
    return False
