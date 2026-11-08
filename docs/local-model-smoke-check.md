# Local model smoke check

Date: 20 October 2026. These are single local integration checks, not a comparative benchmark, a statistically reliable performance study, or results from the planned 40 robot trials.

## Environment

- Windows PC with an NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM), an Intel Core i7-12700H, and 16 GB system RAM.
- Ollama 0.32.5; local HTTP endpoint at `127.0.0.1:11434`.
- Dialogue model: `qwen3:4b`, 4.0B parameters, Q4_K_M.
- Vision model: `qwen2.5vl:3b`, 3.8B parameters, Q4_K_M.
- The test image was a 640 × 480 Webots robot-camera capture. No hosted inference API was used.

## Observations

| Check | Result | Limitation |
|---|---|---|
| Qwen3 cold dialogue request with a short transcript and vision summary | Valid response and supported emotion; the first request took about 55.5 s end to end. | One request only; the first cold response included a non-spoken emoji, so the text should be checked before TTS. |
| Qwen3 warm dialogue request with the same context | Valid response and emotion; 1.63 s. | One warm sample; no latency distribution or answer-quality scoring. |
| Qwen2.5-VL cold image description | Returned a relevant natural-language description of the Webots image; 74.44 s end to end, including about 31.9 s to load the model. | One image only. The model is unloaded after each image request to manage VRAM, so cold-start latency is a serious limitation for repeated live use. |
| Sequential dialogue → vision → follow-up dialogue | The three calls returned usable outputs in 55.95 s, 75.80 s, and 56.49 s respectively (188.24 s total). The vision answer identified a green object on a yellow cylinder; the follow-up answer referred to it correctly. | One sequential cycle only. Ollama logs showed Qwen3 being evicted to make room for Qwen2.5-VL, then reloaded for the final dialogue call. This is a functional integration check, not a benchmark or evidence of acceptable conversational latency. |
| GPU memory after Qwen3 was warm | 2,793 MiB of 4,096 MiB reported in use; Ollama reported 23% CPU / 77% GPU processing. | This is a point-in-time reading, not a peak-memory profile. No simultaneous two-model load was tested. |

## Interpretation

These checks show that both local model endpoints can return usable outputs on this computer. They do not establish real-time vision performance. The one-image-per-second capture limit controls sampling frequency; it does not mean that the model can process one frame per second. At the measured cold-start time, the current separate-model configuration is too slow for immediate, repeated vision responses. The report should describe this as a feasibility result and an unresolved performance constraint, not as a successful real-time benchmark.

The sequential integration check confirms that a vision description can be passed into a follow-up dialogue request. It also exposes a severe delay on this 4 GB GPU: the measured cycle took 188.24 s, and the dialogue model had to be reloaded after vision inference. The current configuration is therefore suitable only for a staged demonstration with clear pauses, not fluid live multimodal conversation. Any future latency improvement must be measured again on the same hardware before it is described as a result.

The Webots pointing and target-navigation demonstration still uses simulator recognition and world coordinates. The local vision model only produced a textual scene summary; it did not choose a navigation target or prove human pointing recognition. Movement, spoken microphone recognition, model dialogue, and measured audio/face/arm synchronisation have not yet been validated together in a physical prototype.

## Reproduction

From the simulation repository root, start Ollama and run the Python functions `generate_local_vision_summary` and `generate_local_dialogue` in `core/dialogue.py`. For timing comparisons, repeat each request after both a cold model load and a warm request, keep the prompt and image constant, and log each result separately. Do not combine these smoke checks with the 40 planned technical trials.
