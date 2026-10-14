"""Optional offline microphone transcription through a local Vosk model."""

from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Thread
import json


class VoskMicrophone:
    """Capture 16 kHz mono audio and deliver completed English utterances."""

    def __init__(self, model_path, on_transcript, on_error):
        self.model_path = Path(model_path)
        self.on_transcript = on_transcript
        self.on_error = on_error
        self._stop = Event()
        self._audio = Queue(maxsize=32)
        self._thread = None

    def start(self):
        if not self.model_path.is_dir():
            raise FileNotFoundError(f"Vosk model directory not found: {self.model_path}")
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._listen, name="tulpar-microphone", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _audio_callback(self, indata, frames, timing, status):
        if status:
            self.on_error(f"Audio input status: {status}")
        block = bytes(indata)
        try:
            self._audio.put_nowait(block)
        except Full:
            try:
                self._audio.get_nowait()
                self._audio.put_nowait(block)
            except (Empty, Full):
                pass

    def _listen(self):
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model, SetLogLevel

            SetLogLevel(-1)
            model = Model(str(self.model_path))
            recognizer = KaldiRecognizer(model, 16000)
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=self._audio_callback,
            ):
                while not self._stop.is_set():
                    try:
                        block = self._audio.get(timeout=0.2)
                    except Empty:
                        continue
                    if recognizer.AcceptWaveform(block):
                        transcript = json.loads(recognizer.Result()).get("text", "").strip()
                        if transcript:
                            self.on_transcript(transcript)
        except Exception as error:
            if not self._stop.is_set():
                self.on_error(f"Microphone input stopped: {error}")
