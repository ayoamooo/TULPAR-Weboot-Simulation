# Local voice interaction

The voice path is local and optional. No audio is sent to a hosted service. Raw microphone audio, recognized words, generated replies, and conversation history are not written to the simulation event log. The event log stores event types, timestamps, outcomes, target IDs, and response emotion.

## Components

- Vosk transcribes English microphone audio. It needs a local model directory; the model files are not part of this repository.
- A spoken `stop` is checked against Vosk partial results and bypasses model inference. It cancels queued requests and invalidates any in-flight response so an old result cannot trigger new speech or movement after Stop. `Emergency stop` latches the stop state; `clear emergency stop` releases it.
- Voice commands can request floor or tabletop mode, a greeting wave, or a supported facial emotion. Keyboard inputs remain development controls and are also available for the repeatable test harness.
- The local dialogue model receives a short system instruction, the current utterance, and up to four recent exchanges held temporarily in memory.
- The model returns structured JSON containing a short reply, a supported emotion, and either ordinary conversation or a proposed move to one of the scene's two named targets. The controller checks the proposal against explicit movement words and target names in the transcript, camera recognition freshness, floor mode, and emergency-stop state. The model cannot return coordinates, wheel speeds, or actuator commands.
- The target registry currently contains `target-A` (gold/orange) and `target-B` (purple). Requests to other objects or ambiguous references are not allowed to start motion; TULPAR asks the operator to clarify or select a known target.
- The selected response is spoken by the Webots Speaker and the same validated emotion drives the face and arm pose.
- The default backend remains Ollama so the existing local setup continues to work. A llama.cpp server can be selected through the OpenAI-compatible chat-completions API.
- Webots Speaker reads the reply. No separate TTS API is used.

## Configuration

Install the optional Python packages if the Python interpreter used by Webots does not already have them:

```powershell
python -m pip install -e ".[voice]"
```

Before launching Webots, configure the path to an extracted English Vosk model and the local Ollama model name in the same PowerShell session:

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

If `TULPAR_VOSK_MODEL` is unset or points to a missing directory, the microphone is disabled and keyboard controls remain available. If the selected local model server is unavailable, TULPAR reports that conversational inference is unavailable; immediate Stop and keyboard controls remain independent of it. Camera image capture is not part of the conversational turn in the current implementation. Live audio is held only in the microphone pipeline and is not written to persistent storage by this controller.

## Evidence limits

The separate, single-run local smoke check in [local-model-smoke-check.md](local-model-smoke-check.md) documents earlier Ollama measurements; it is not a comparative benchmark or a measurement of the new interaction path. Microphone recognition accuracy, target-intent accuracy, spoken response latency, audio output, and speech/face/arm synchronisation still require measured Webots runs. These results must be added only after the runs are performed.
