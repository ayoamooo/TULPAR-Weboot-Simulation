# Local voice path

The voice path is local and optional. No audio is sent to a hosted service. Raw microphone audio and recognized words are not written to the simulation event log; the log stores event types, timestamps, outcome, and response emotion.

## Components

- Vosk transcribes English microphone audio. It needs a local model directory; the model files are not part of this repository.
- `core/command_policy.py` checks the transcript before movement or gesture commands are dispatched.
- For each ordinary conversation turn, the controller captures one JPEG frame (at most once per second) and sends it to the local Ollama vision model `qwen2.5vl:3b` by default. The model is asked only for a brief visual summary, and its response is treated as uncertain context.
- The transcript and visual summary are then sent to the local Ollama dialogue model asynchronously on a background thread. `qwen3:4b` is the default model name and can be changed with `TULPAR_OLLAMA_MODEL`.
- Ollama receives a JSON response schema containing only `response` and `emotion`. The controller validates both fields before speaking or updating the face.
- Webots Speaker reads the reply. No separate TTS API is used.
- The vision model is unloaded after each frame request to reduce simultaneous GPU memory use. This may increase response latency; performance on the 4 GB GPU still needs a real run.

## Configuration

Install the optional Python packages if the Python interpreter used by Webots does not already have them:

```powershell
python -m pip install -e ".[voice]"
```

Before launching Webots, configure the path to an extracted English Vosk model and the local Ollama model name in the same PowerShell session:

```powershell
$env:TULPAR_VOSK_MODEL = "C:\path\to\vosk-model-small-en-us"
$env:TULPAR_OLLAMA_MODEL = "qwen3:4b"
$env:TULPAR_VISION_MODEL = "qwen2.5vl:3b"
```

Ollama must be running locally at `http://127.0.0.1:11434`. Set `TULPAR_OLLAMA_URL` only if the local server uses another address. No model is downloaded by the controller.

If `TULPAR_VOSK_MODEL` is unset or points to a missing directory, the microphone is disabled and the keyboard controls remain available. If the vision model request fails, the text model still receives the spoken question without visual context. If Ollama is unavailable, free-form dialogue receives a spoken error response; the allow-listed movement commands remain independent of Ollama. The model cannot command the tracks or arms directly. Captured image bytes are not stored in the event log; the temporary JPEG is removed after it is read.

## Evidence limits

The Python unit tests verify transcript-policy separation, local image request construction, and model-response validation. They do not measure microphone recognition accuracy, visual-description quality, model answer quality, spoken response latency, or Webots audio output. Those require a working audio device, configured Vosk model, local Ollama service, and an installed Webots runtime. Record such results only after running those components together.
