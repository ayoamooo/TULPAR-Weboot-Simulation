@echo off
rem Copy this file to START-TULPAR.local.cmd and edit the local paths/model name.
rem The local copy is ignored by Git and is read by START-TULPAR.cmd.
set "TULPAR_VOSK_MODEL=%~dp0voice-models\vosk-model-small-en-us-0.15"
set "TULPAR_LLM_BACKEND=ollama"
set "TULPAR_OLLAMA_MODEL=qwen3:4b"
rem For llama.cpp, use these instead and keep the local llama-server running:
rem set "TULPAR_LLM_BACKEND=llama.cpp"
rem set "TULPAR_LLAMACPP_URL=http://127.0.0.1:8080"
rem set "TULPAR_LLAMACPP_MODEL=qwen3.5-2b-q4"
