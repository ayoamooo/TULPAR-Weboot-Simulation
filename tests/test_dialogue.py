import json
from io import BytesIO
import base64
import os
import unittest
from unittest.mock import patch

from core.dialogue import (
    DialogueError,
    DialogueResponse,
    generate_local_dialogue,
    generate_local_vision_summary,
    parse_dialogue_response,
)


class DialogueValidationTests(unittest.TestCase):
    def test_accepts_only_a_reply_and_supported_emotion(self):
        self.assertEqual(
            parse_dialogue_response('{"response":"Hello there.","emotion":"happy"}'),
            DialogueResponse("Hello there.", "happy"),
        )

    def test_rejects_actuator_fields(self):
        with self.assertRaises(DialogueError):
            parse_dialogue_response(
                '{"response":"Move forward.","emotion":"neutral","action":"drive"}'
            )

    def test_rejects_unknown_emotions_and_invalid_output(self):
        with self.assertRaises(DialogueError):
            parse_dialogue_response('{"response":"Hi.","emotion":"drive"}')
        with self.assertRaises(DialogueError):
            parse_dialogue_response("not json")

    def test_rejects_empty_and_overlong_replies(self):
        with self.assertRaises(DialogueError):
            parse_dialogue_response('{"response":" ","emotion":"neutral"}')
        with self.assertRaises(DialogueError):
            parse_dialogue_response('{"response":"' + ('x' * 361) + '","emotion":"neutral"}')

    @patch.dict(os.environ, {"TULPAR_OLLAMA_URL": "http://127.0.0.1:11434", "TULPAR_OLLAMA_MODEL": "qwen3:4b"})
    @patch("core.dialogue.urlopen")
    def test_local_request_uses_schema_and_never_receives_motor_tools(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value = BytesIO(
            json.dumps({"response": '{"response":"Nice to meet you.","emotion":"happy"}'}).encode()
        )
        result = generate_local_dialogue("Hello TULPAR")
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(result.response, "Nice to meet you.")
        self.assertEqual(payload["model"], "qwen3:4b")
        self.assertEqual(payload["format"]["required"], ["response", "emotion"])
        self.assertNotIn("tools", payload)

    @patch.dict(os.environ, {"TULPAR_OLLAMA_URL": "http://127.0.0.1:11434", "TULPAR_VISION_MODEL": "qwen2.5vl:3b"})
    @patch("core.dialogue.urlopen")
    def test_vision_request_sends_frame_only_to_local_model_and_unloads_it(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value = BytesIO(
            json.dumps({"response": "A robot and two markers are visible."}).encode()
        )
        result = generate_local_vision_summary(b"fake-jpeg-frame")
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(result, "A robot and two markers are visible.")
        self.assertTrue(request.full_url.startswith("http://127.0.0.1:11434/"))
        self.assertEqual(payload["model"], "qwen2.5vl:3b")
        self.assertEqual(base64.b64decode(payload["images"][0]), b"fake-jpeg-frame")
        self.assertEqual(payload["keep_alive"], "0s")


if __name__ == "__main__":
    unittest.main()
