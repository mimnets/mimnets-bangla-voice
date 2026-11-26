# Bangla Voice: project context for Claude Code

Read this whole file before doing anything. It holds the background, decisions, and lessons from the research and prototyping done before this repo existed.

## Who this is for

- Owner: Monir, based in Bangladesh (timezone Asia/Dhaka). Speaks Bangladeshi Bangla and mixes in English, especially tech words ("ei file e ekta login function banao").
- Main machine: Windows 11 laptop. Python is installed. Works in VS Code with AI coding tools.
- Budget: as close to free as possible. ElevenLabs was ruled out as too expensive. Prefer free tiers and pay-per-use APIs with free credit over subscriptions.
- Not a full-time developer. Explain choices in plain language, keep setup steps short, and give exact commands.

## What we are building

Two features, one product:

1. **Dictation (speech to text) that types where the cursor is.** Press a hotkey, speak Bangla, English, or a mix, press again, and the text is pasted into whatever app has focus (VS Code, browser, ChatGPT, Claude). There are two modes:
   - Raw: type exactly what was said.
   - Clean: an LLM fixes transcription errors and rewrites it as a clear English instruction (for prompting AI tools).
2. **Voice clone text to speech for TikTok videos.** The owner records about 10 seconds of his own voice, types a Bangla script, and gets an audio file in his voice. It must sound Bangladeshi, not Kolkata.

Target platforms, in order: Windows (installer plus portable), then Android, then macOS, Linux, iOS if it succeeds.

## What already works (the prototype)

`prototype/dictate-python/app.py` is a working Windows dictation app (Python and Tkinter). It's the reference implementation. Port its behaviour, don't reinvent it.

- Global hotkeys: `Ctrl+Alt+D` raw, `Ctrl+Alt+E` clean. Toggle mode: press to start, press again to stop. High beep on start, low beep on stop.
- Records 16 kHz mono int16 WAV, sends it to Groq Whisper, then for clean mode sends the text to a Groq chat model.
- Pastes at the cursor: saves the clipboard, copies the text, waits for Ctrl/Alt/Shift to be released, sends Ctrl+V, then restores the old clipboard after about 0.4 s.
- Window has API key boxes, Record button, mic level meter, "Test mic" (3 s record plus playback), result box, log box, settings tab, and "Compare speech models" (records 10 s and runs every model).
- The owner tested it on 2026-11-26 and Bangla dictation works well.

## Proven API details (verified November 2026)

### Groq (free tier, no card): the default for everything
- STT: `POST https://api.groq.com/openai/v1/audio/transcriptions`, multipart form: `file` (wav), `model`, `language` (optional ISO-639-1: `bn` or `en`; omit for auto), `prompt` (vocabulary hint), `temperature=0`, `response_format=json`. Response: `{"text": ...}`.
- STT models: `whisper-large-v3` (default, best for Bangla), `whisper-large-v3-turbo`.
- Free STT limits: 20 req/min, 2,000 req/day, 7,200 audio seconds/hour, 28,800 audio seconds/day.
- Chat (cleanup): `POST https://api.groq.com/openai/v1/chat/completions` (OpenAI-compatible). Default model `openai/gpt-oss-120b` with `"reasoning_effort": "low"`. If a 400 mentions reasoning, retry without that field. Other free chat models seen: `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`. Model lists change, so check https://console.groq.com/docs/rate-limits before hardcoding.

### OpenRouter (optional, paid for speech)
- STT endpoint `POST https://openrouter.ai/api/v1/audio/transcriptions`, JSON body with `input_audio: {data: <base64>, format: "wav"}`. Audio models need at least $0.50 account balance or the API returns 402. That's why Groq became the default.
- Chat models ending in `:free` and `openrouter/free` work without credit. Strip `<think>...</think>` from replies.

### Sarvam AI (Indian company, Indic speech)
- TTS Bulbul v3: ₹30 per 10K chars. Bulbul V4 Flash: ₹20 per 10K chars. Instant Voice Cloning (beta): about ₹2 per 1,000 chars, 10 to 15 s reference clip, cross-lingual. New accounts get free credits.
- STT Saaras v3 handles Bengali code-mixing, ₹30 per hour, and can transcribe and translate to English in one call.
- Caveat: trained mainly on Indian speech, so the Bengali may sound West Bengal rather than Bangladesh. Must be judged by ear.

## Lessons learned (don't repeat these mistakes)

- Windows built-in voice typing (Win+H) does not support Bangla.
- Laptop F-keys (F8, F9) are often media keys unless Fn is held. Use Ctrl+Alt combos for hotkeys. Ctrl+Alt+E can clash with some keyboard tools (Avro), so hotkeys must be configurable.
- Whisper hallucinates on silence or noise: "Thank you for watching", "Please subscribe", "Subtitles by amara.org". The prototype drops recordings with peak amplitude under 400 without sending them, and discards short outputs that match known hallucination phrases.
- With `language` on auto, Whisper sometimes writes Bangla in Latin letters ("ki Bungla e katho bolbo"). Setting `bn` forces Bangla script. Clean mode handles both.
- Windows shows "Python is using your microphone" while recording. That's normal. The mic stream must be fully closed after each recording.
- `pip install` must be `python -m pip install` so it targets the same Python that runs the app.
- Handy (open source, Tauri, MIT, handy.computer) only supports local Whisper. Its local Bangla accuracy is weak, which is why we use cloud STT.

## Voice clone research so far (not built or tested yet)

Candidates to test, in order of effort:

1. **Sarvam Instant Voice Cloning API.** Easiest, cheap, no GPU. Verify `bn-IN` is in its supported languages. Judge the accent.
2. **BanglaBox** (paper arXiv 2610.09211, weights and code at https://huggingface.co/Banglabox). Fine-tuned Chatterbox TTS (MIT base) on 520 h of Bangla. Zero-shot cloning from a 3 to 10 s clip; 10 s gave better similarity. The paper claims it beats Google, Azure, IndicF5 and XTTS on naturalness. Code is MIT, the corpus is CC BY 4.0, but the weights' license is not stated, so check before any commercial use. Needs a GPU: use Google Colab or Kaggle free GPU.
3. **IndicF5** (`ai4bharat/IndicF5` on Hugging Face, MIT, 11 Indic languages including Bengali). Clones from a reference clip plus its exact transcript. 24 kHz output. Needs a GPU for reasonable speed.

Practical rules for good clones:
- Clean 10 s reference: quiet room, no music, one speaker, normal TikTok tone, exact transcript saved alongside.
- Normalise text before synthesis: numbers, dates and currency to Bangla words (১২৫০ টাকা → এক হাজার দুইশো পঞ্চাশ টাকা).
- Split long scripts at । ? ! and synthesise sentence by sentence, then join.
- Only clone voices with consent. This is the owner's own voice.

## Chosen tech stack (and why)

- **Experiments and voice clone lab: Python.** Fast to try models, every TTS model ships Python code, and Colab runs it on free GPUs.
- **Apps: Flutter (Dart)** for one codebase across Windows, Android, macOS, Linux, iOS.
  - Windows: global hotkeys, mic recording, clipboard, and simulated Ctrl+V all have Flutter plugins (check current packages, e.g. `hotkey_manager`, `record`, `keypress_simulator` or a small win32 FFI call). Ships as an installer (Inno Setup or MSIX) and as a portable zip of the release folder.
  - Android: an app can't type into other apps the way desktop paste works. The standard approach is a custom keyboard (`InputMethodService`) with a mic button, written in Kotlin inside the Flutter project's Android folder. The rest (settings, voice clone screen) stays in Flutter. Note: Gboard already does Bangla voice typing for free, so our Android value is Groq accuracy, English cleanup, and the voice clone studio.
- **Cloud first.** The app calls Groq and Sarvam APIs directly, so it stays small and works on low-end PCs and phones. Local models can come later as an offline option.
- **Bring your own key.** The user pastes their own free Groq key. Store keys in secure storage (`flutter_secure_storage`), never in the repo. Behind a provider interface so Sarvam, OpenRouter or local models can be swapped in.

Alternative considered: Tauri (Rust plus web UI), which is what Handy uses. It's excellent for desktop, but its mobile support is less mature, and Rust is harder for a non-specialist owner. Kotlin Multiplatform is strong on Android but heavier on desktop. Pure Python can't produce a real Android app.

## Working rules for Claude Code in this repo

- Work phase by phase (see `docs/ROADMAP.md`). Finish and test one phase before starting the next, and stop to check with the owner at the end of each phase.
- Never commit secrets. Keys go in `.env` (git-ignored) for Python tools and in secure storage in apps.
- Give the owner exact commands to run on Windows (PowerShell or cmd) and explain what output to expect.
- When an API detail matters (endpoint, model name, price, limit), check current docs instead of trusting this file blindly. Update this file when something changes.
- Keep commits small, with clear messages.
