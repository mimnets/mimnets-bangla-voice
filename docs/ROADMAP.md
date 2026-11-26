# Roadmap

Each phase ends with something the owner can run and judge. Stop and check in after each one.

## Phase 0: Repo setup
- Confirm the folder layout below and the `.gitignore`.
- Create `.env.example` with `GROQ_API_KEY=`, `SARVAM_API_KEY=`, `OPENROUTER_API_KEY=`.
- Add a short root `README.md`.

```
mimnets-bangla-voice/
  CLAUDE.md
  docs/ROADMAP.md
  prototype/dictate-python/   working Windows dictation prototype (reference only)
  voice-clone-lab/            Phase 1, Python
  app/                        Phase 3 onward, Flutter
```

## Phase 1: Voice clone lab (do this first)
Goal: find out which option makes the owner's voice sound right in Bangladeshi Bangla, before building any app.

1. `voice-clone-lab/record_reference.py`: records a 10 to 15 s reference clip (16 or 24 kHz mono WAV) with a countdown and a level check, plays it back, and saves it with a transcript file the owner types in.
2. `voice-clone-lab/bangla_text.py`: Bangla text normaliser (digits, numbers to words, ৳ and টাকা, dates, common English abbreviations) and a sentence splitter on । ? ! newline. Include tests.
3. `voice-clone-lab/sarvam_clone.py`: Sarvam Instant Voice Cloning. Reads the key from `.env`, clones from the reference, synthesises a test script sentence by sentence, joins with short pauses, and saves `out/sarvam_<timestamp>.wav`. Check the current API docs first (docs.sarvam.ai, voice-cloning section).
4. `voice-clone-lab/notebooks/banglabox_colab.ipynb`: Colab notebook (free T4 GPU). Installs BanglaBox from huggingface.co/Banglabox, uploads the reference clip, runs the same test script, downloads the WAV. Read the model card for the exact inference code and check the weights' license.
5. `voice-clone-lab/notebooks/indicf5_colab.ipynb`: same thing for `ai4bharat/IndicF5` (needs reference audio plus its exact transcript).
6. `voice-clone-lab/test_scripts/`: three short Bangla TikTok-style scripts (about 30 s each) with numbers, an English brand name, and a question, so every engine gets the same input.
7. `voice-clone-lab/RESULTS.md`: a table the owner fills in (naturalness, sounds like me, Bangladeshi accent, pronunciation errors, speed, cost) and a recommendation.

Done when the owner has listened to all three and picked a winner (or decided none is good enough yet).

## Phase 2: Shared design
- Write `docs/ARCHITECTURE.md`: provider interfaces (`SpeechToText`, `TextCleanup`, `TextToSpeech`, `VoiceClone`), settings model, key storage, error handling (401, 402, 429, network), hallucination and silence filters, clipboard and paste flow.
- Decide the voice clone backend from Phase 1. If it needs a GPU (BanglaBox or IndicF5), design a small serverless endpoint (e.g. Modal) that the app calls; otherwise call Sarvam directly.

## Phase 3: Windows app (Flutter)
- Tray app with a small window: key setup, Record button, mic level, test mic, result, log, settings. Same behaviour as the prototype.
- Global hotkeys (configurable), recording, Groq STT, Groq cleanup, paste at cursor with clipboard restore, beeps, silence and hallucination filters.
- Voice clone tab: record reference, type script, generate, play, save WAV or MP3.
- Start with Windows option, single instance, remembers settings.
- Packaging: Inno Setup installer and a portable zip. GitHub Actions workflow that builds both on each tagged release.

## Phase 4: Android
- Same Flutter app for settings and the voice clone studio.
- Kotlin `InputMethodService` keyboard with a big mic button (tap to start and stop) plus a "clean to English" toggle. It commits text into any app's text field. Shares API code through a platform channel or a small Kotlin client.
- Build a signed APK for sideloading first; Play Store later.

## Phase 5: Other platforms
- macOS and Linux desktop (hotkeys, paste and permissions differ, especially macOS Accessibility permission).
- iOS custom keyboard (stricter rules: keyboards can't use the mic directly, so this needs a different design).
