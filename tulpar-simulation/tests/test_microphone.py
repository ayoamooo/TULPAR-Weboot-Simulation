from pathlib import Path
import unittest

from core.microphone import VoskMicrophone


class MicrophoneSetupTests(unittest.TestCase):
    def test_missing_model_is_reported_before_audio_capture(self):
        missing_model = Path(__file__).parent / "not-installed-vosk-model-fixture"
        self.assertFalse(missing_model.exists())
        listener = VoskMicrophone(missing_model, lambda text: None, lambda error: None)
        with self.assertRaises(FileNotFoundError):
            listener.start()


if __name__ == "__main__":
    unittest.main()
