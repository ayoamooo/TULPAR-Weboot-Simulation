import json
from io import BytesIO
import base64
import os
import unittest
from unittest.mock import patch

from core.dialogue import (
    DialogueError,
    INTERACTION_SCHEMA,
    DialogueResponse,
    InteractionResponse,
    enforce_spoken_navigation_intent,
    explicit_navigation_interaction,
    generate_local_dialogue,
    generate_local_interaction,
    generate_local_vision_summary,
    parse_dialogue_response,
    scene_navigation_interaction,
)
from core.scene_targets import SCENE_TARGETS


class DialogueValidationTests(unittest.TestCase):
    def test_accepts_only_a_reply_and_supported_emotion(self):
        self.assertEqual(
            parse_dialogue_response('{"response":"Hello there.","emotion":"happy"}'),
            DialogueResponse("Hello there.", "happy"),
        )

    def test_removes_emoji_before_sending_reply_to_speaker(self):
        self.assertEqual(
            parse_dialogue_response('{"response":"Hello 😊!","emotion":"happy"}'),
            DialogueResponse("Hello!", "happy"),
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

    def test_model_cannot_move_without_an_explicit_spoken_target(self):
        result = enforce_spoken_navigation_intent(
            "Tell me what you can do.",
            InteractionResponse("Moving to target-A.", "neutral", "move_to_object", "target-A"),
        )
        self.assertEqual(result.action, "conversation")
        self.assertIsNone(result.target_id)
        self.assertIn("bench", result.response)

    def test_model_target_must_match_the_explicit_spoken_target(self):
        result = enforce_spoken_navigation_intent(
            "Move to the yellow marker.",
            InteractionResponse("Moving to target-B.", "neutral", "move_to_object", "target-B"),
        )
        self.assertEqual(result.action, "move_to_object")
        self.assertEqual(result.target_id, "target-A")
        self.assertEqual(result.response, "Okay, I will move to the yellow marker now.")

    def test_explicit_matching_target_keeps_the_navigation_proposal(self):
        proposal = InteractionResponse(
            "I am moving to the purple marker.", "thinking", "move_to_object", "target-B"
        )
        result = enforce_spoken_navigation_intent("Drive to the purple marker.", proposal)
        self.assertEqual(result.action, "move_to_object")
        self.assertEqual(result.target_id, "target-B")
        self.assertEqual(result.response, "Okay, I will move to the purple marker now.")

    def test_registered_scene_objects_are_valid_navigation_targets(self):
        self.assertIn("scene-bench", INTERACTION_SCHEMA["properties"]["target_id"]["enum"])
        proposal = InteractionResponse(
            "What is the target id? (scene-bench)", "thinking", "move_to_object", "scene-bench"
        )
        result = enforce_spoken_navigation_intent("Please drive to the bench.", proposal)
        self.assertEqual(result.action, "move_to_object")
        self.assertEqual(result.target_id, "scene-bench")
        self.assertEqual(result.response, "Okay, I will move to the bench now.")
        self.assertIn("scene-plant", SCENE_TARGETS)

    def test_registered_target_must_match_the_spoken_object_name(self):
        result = enforce_spoken_navigation_intent(
            "Approach the potted plant.",
            InteractionResponse("Moving to bench.", "neutral", "move_to_object", "scene-bench"),
        )
        self.assertEqual(result.action, "move_to_object")
        self.assertEqual(result.target_id, "scene-plant")
        self.assertEqual(result.response, "Okay, I will move to the potted plant now.")

    def test_model_cannot_ignore_an_explicit_navigation_request(self):
        result = enforce_spoken_navigation_intent(
            "Go to the yellow marker.",
            InteractionResponse("Hello there.", "happy", "conversation", None),
        )
        self.assertEqual(result.action, "move_to_object")
        self.assertEqual(result.target_id, "target-A")

    def test_explicit_navigation_is_resolved_without_an_llm_proposal(self):
        result = explicit_navigation_interaction("Go to the potted plant.")
        self.assertEqual(result.action, "move_to_object")
        self.assertEqual(result.target_id, "scene-plant")
        self.assertIsNone(explicit_navigation_interaction("Tell me about the plant."))

    def test_ambiguous_navigation_gets_local_clarification_without_model(self):
        result = scene_navigation_interaction("Go to that object.")
        self.assertEqual(result.action, "conversation")
        self.assertIn("Which object", result.response)
        self.assertIsNone(scene_navigation_interaction("Tell me about the plant."))

    @patch("core.dialogue.urlopen", side_effect=AssertionError("LLM should not be called"))
    def test_explicit_navigation_does_not_call_local_model(self, mock_urlopen):
        result = generate_local_interaction("Please drive to the bench.")
        self.assertEqual(result.action, "move_to_object")
        self.assertEqual(result.target_id, "scene-bench")
        mock_urlopen.assert_not_called()

    @patch.dict(os.environ, {"TULPAR_LLM_BACKEND": "ollama"})
    @patch("core.dialogue.urlopen")
    def test_open_conversation_uses_reply_schema_without_navigation_fields(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value = BytesIO(
            json.dumps({"message": {"content": json.dumps({
                "response": "I can explore the simulated room with you.",
                "emotion": "happy",
            })}}).encode()
        )
        result = generate_local_interaction("What can you do?")
        self.assertEqual(result.action, "conversation")
        self.assertIsNone(result.target_id)
        self.assertIn("explore", result.response)
        payload = json.loads(mock_urlopen.call_args.args[0].data)
        self.assertEqual(payload["format"]["required"], ["response", "emotion"])
        self.assertNotIn("target_id", payload["format"]["properties"])

    @patch.dict(os.environ, {"TULPAR_OLLAMA_URL": "http://127.0.0.1:11434", "TULPAR_OLLAMA_MODEL": "qwen3:4b"})
    @patch("core.dialogue.urlopen")
    def test_local_request_uses_schema_and_never_receives_motor_tools(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value = BytesIO(
            json.dumps({"message": {"content": '{"response":"Nice to meet you.","emotion":"happy"}'}}).encode()
        )
        result = generate_local_dialogue("Hello TULPAR")
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(result.response, "Nice to meet you.")
        self.assertEqual(payload["model"], "qwen3:4b")
        self.assertEqual(payload["format"]["required"], ["response", "emotion"])
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["content"], "Hello TULPAR")
        self.assertFalse(payload["think"])
        self.assertTrue(request.full_url.endswith("/api/chat"))
        self.assertEqual(mock_urlopen.call_args.kwargs["timeout"], 90)
        self.assertNotIn("tools", payload)

    @patch.dict(os.environ, {"TULPAR_OLLAMA_URL": "http://127.0.0.1:11434", "TULPAR_VISION_MODEL": "qwen2.5vl:3b"})
    @patch("core.dialogue.urlopen")
    def test_vision_request_sends_frame_only_to_local_model_and_unloads_it(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value = BytesIO(
            json.dumps({"message": {"content": "A robot and two markers are visible."}}).encode()
        )
        result = generate_local_vision_summary(b"fake-jpeg-frame")
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(result, "A robot and two markers are visible.")
        self.assertTrue(request.full_url.startswith("http://127.0.0.1:11434/api/chat"))
        self.assertEqual(payload["model"], "qwen2.5vl:3b")
        self.assertEqual(base64.b64decode(payload["messages"][0]["images"][0]), b"fake-jpeg-frame")
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertEqual(payload["keep_alive"], "0s")


if __name__ == "__main__":
    unittest.main()
