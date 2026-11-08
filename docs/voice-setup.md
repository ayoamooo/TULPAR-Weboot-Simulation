# Local voice interaction

Voice is the primary interaction path and runs locally once configured. No audio is sent to a hosted service. Raw microphone audio, recognized words, generated replies, and conversation history are not written to the simulation event log. The event log stores event types, timestamps, outcomes, target IDs, and response emotion.

## Components

- Vosk transcribes English microphone audio. It needs a local model directory; the model files are not part of this repository.
- A spoken `stop` is checked against Vosk partial results and bypasses model inference. It cancels queued requests and invalidates any in-flight response so an old result cannot trigger new speech or movement after Stop. `Emergency stop` latches the stop state; `clear emergency stop` releases it.
- Voice commands can request floor or tabletop mode, a greeting wave, or a supported facial emotion. Keyboard inputs remain development controls and are also available for the repeatable test harness.
- The local dialogue model receives a short system instruction, the current utterance, and up to four recent exchanges held temporarily in memory.
- The model returns structured JSON for ordinary conversation and a supported emotion. Clear movement commands to a named target are parsed deterministically before model inference, so target selection does not depend on the language model. The controller requires current camera recognition, floor mode, and a cleared emergency stop before starting an approach. The model cannot return coordinates, wheel speeds, or actuator commands.
- The target registry contains `target-A` (gold/orange/yellow), `target-B` (purple/violet), the bench, and the potted plant. Voice navigation requires a clear target name; an unspecified or ambiguous object does not start motion, and TULPAR asks for clarification. The simulated pointing controls are reserved for separate repeatable checks.
- The selected response is spoken by the Webots Speaker and the same validated emotion drives the face and arm pose.
- The default backend remains Ollama so the existing local setup continues to work. A llama.cpp server can be selected through the OpenAI-compatible chat-completions API.
- Webots Speaker reads the reply. No separate TTS API is used.

## Configuration

On Windows, run `SETUP-TULPAR-VOICE.ps1` from PowerShell to install the optional Python packages, download the compact English Vosk model, and create `START-TULPAR.local.cmd` if it does not already exist. The archive is downloaded from the Vosk project and extracted into the Git-ignored `voice-models/` directory; it is not committed to the repository. The model catalogue lists this model as approximately 40 MB and Apache 2.0 licensed ([Vosk model catalogue](https://alphacephei.com/vosk/models)). Confirm that the Python environment used by Webots is the same one printed by the setup script; otherwise install the optional packages in Webots' configured Python environment.

`START-TULPAR.cmd` reads `START-TULPAR.local.cmd` before opening the interactive
`tulpar_demo.wbt` world. The setup script creates it from the example on first run and
preserves it on later runs. If you configure voice manually, copy
`START-TULPAR.local.example.cmd`, set the extracted model path and selected dialogue
backend, and keep the local file out of Git. Use `START-TULPAR-SHOWCASE.cmd` for the
separate automatic visual presentation.

Install the optional Python packages if the Python interpreter used by Webots does not already have them:

```powershell
python -m pip install -e ".[voice]"
```

If launching from PowerShell rather than the batch file, configure the path to an extracted English Vosk model and the local Ollama model name in that session:

```powershell
$env:TULPAR_VOSK_MODEL = "C:\path\to\vosk-model-small-en-us"
$env:TULPAR_LLM_BACKEND = "ollama"
$env:TULPAR_OLLAMA_MODEL = "qwen3:4b"
```

Ollama must be running locally at `http://127.0.0.1:11434`. Set `TULPAR_OLLAMA_URL` only if the local server uses another address. No model is downloaded by the controller.

For llama.cpp, start a compatible local `llama-server` with the selected GGUF model and its chat-completion endpoint bound to loopback. Then set:

```powershell
$env:TULPAR_LLM_BACKEND = "llama.cpp"
$env:TULPAR_LLAMACPP_URL = "http://127.0.0.1:8080"
$env:TULPAR_LLAMACPP_MODEL = "qwen3.5-2b-q4"
```

The server must support `/v1/chat/completions` and JSON-schema constrained output. Model binaries are not stored in Git. The Qwen3.5-2B Q4 choice is a provisional candidate; the final model selection depends on measured intent accuracy, response quality, RAM/VRAM use, and latency on the target computer. The llama.cpp path has not yet been runtime-validated in this project.

If `TULPAR_VOSK_MODEL` is unset or points to a missing directory, the microphone is disabled and keyboard controls remain available. Startup waits until the audio stream has opened; if the stream fails later, TULPAR marks voice input unavailable and announces that the simulation should be restarted after checking the microphone. If the selected local model server is unavailable, TULPAR reports that conversational inference is unavailable; immediate Stop and keyboard controls remain independent of it. Camera image capture is not part of the conversational turn in the current implementation. Live audio is held only in the microphone pipeline and is not written to persistent storage by this controller.

## Evidence limits

The separate, single-run local smoke check in [local-model-smoke-check.md](local-model-smoke-check.md) documents earlier Ollama measurements; it is not a comparative benchmark or a measurement of the new interaction path. Microphone recognition accuracy, target-intent accuracy, spoken response latency, audio output, and speech/face/arm synchronisation still require measured Webots runs. These results must be added only after the runs are performed.
