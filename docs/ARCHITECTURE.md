# Architecture (Phase 2)

Written 2026-11-26. API facts were checked against official docs that day (sources at the end). Re-check anything marked **verify** when building.

## In plain words

- **The app** (Flutter, Windows first) does dictation exactly like the Python prototype: hotkey, record, Groq Whisper, optional Groq cleanup, paste at the cursor.
- **The voice clone** runs BanglaBox with `cfg_weight` 0.8 (the Phase 1 winner) in one of two places:
  1. **Colab by hand** (free, available today): the existing notebook. You paste your script, download the WAV, and the app can import it into its library.
  2. **Your own cloud GPU server on Modal** (pay per second, likely covered by Modal's $30/month free credit): the app sends one sentence at a time and gets audio back in seconds. Nobody else can use it: it needs your secret token.
- Both use **the same Python code** for BanglaBox (`voice-server/`), so a fix in one place fixes both.
- All keys live in the computer's secure storage, never in files or the repo.

```
                    ┌───────────────────────── Flutter app ─────────────────────────┐
 hotkey ──► Recorder ──► SilenceFilter ──► SpeechToText ──► HallucinationFilter ──┐  │
                                             (Groq)                               │  │
                                                     raw mode ◄───────────────────┤  │
                                                     clean mode ──► TextCleanup ──┤  │
                                                                    (Groq chat)   ▼  │
                                                                    PasteService ──► app at cursor
 Voice tab: script ──► BanglaText (normalise + split) ──► VoiceCloneTts ──► join + pauses ──► WAV/MP3
                                                            │
                                     ┌──────────────────────┴───────────────────────┐
                              BanglaBoxCloud (HTTP)                        ManualColab (import WAV)
                                     │                                              │
                     Modal endpoint: voice-server/modal_app.py      notebooks/banglabox_colab.ipynb
                                     └──────── shared: voice-server/banglabox_core.py ──┘
```

## 1. Code layout

```
app/                        Flutter app (Phase 3+)
  lib/core/                 pure Dart, no Flutter imports; unit-tested
    providers/              interfaces + implementations (section 2)
    text/bangla_text.dart   Dart port of voice-clone-lab/bangla_text.py
    filters.dart            silence + hallucination filters (section 6)
    settings.dart           settings model (section 3)
    errors.dart             ProviderError + mapping (section 5)
  lib/platform/             hotkeys, recorder, paste, tray, single instance
  lib/ui/                   screens
  test/
voice-server/               Python, BanglaBox serving (Phase 3, voice tab)
  banglabox_core.py         load model once, synthesise one sentence (shared by Modal and Colab)
  modal_app.py              Modal deployment (HTTP endpoint)
  README.md                 one-command deploy guide
shared/
  bangla_text_cases.json    input → expected pairs, run by BOTH the Python and Dart tests
```

**The normaliser lives in two languages** (Python for Colab and the lab, Dart for the app). To stop them drifting apart, the test cases move into `shared/bangla_text_cases.json`, and both test suites read that file. A change that passes one suite but not the other fails CI.

## 2. Provider interfaces (Dart)

Everything that talks to a cloud service sits behind an interface, so Groq, OpenRouter, Sarvam, Modal or a future offline model can be swapped in from Settings.

```dart
/// Speech to text. Groq Whisper today; OpenRouter, Sarvam or local later.
abstract class SpeechToText {
  String get id;                      // "groq", "openrouter"
  Future<Transcript> transcribe(Uint8List wav16kMono, SttOptions o);
}
class SttOptions { String model; String? language; /* "bn" | "en" | null = auto */ String? prompt; }
class Transcript { String text; Duration audioLength; String model; }

/// Turns raw dictation into a clear English instruction.
abstract class TextCleanup {
  String get id;
  Future<String> clean(String text, CleanupOptions o);   // o.promptTemplate contains ${output}
}

/// A cloned voice: the reference clip plus what was said in it.
class VoiceProfile {
  String id;            // sha256 of the WAV bytes: same clip = same id everywhere
  String name;          // "calm", "dhaka"
  String wavPath;       // local file (app data folder, never the repo)
  String transcript;
}

/// Speak text in a cloned voice. One sentence per call; the app joins them.
abstract class VoiceCloneTts {
  String get id;                      // "banglabox-modal", "manual-colab"
  Future<void> warmUp();              // starts a cold server early (call when the tab opens)
  Future<SpeechAudio> speakSentence(String sentence, VoiceProfile v, CloneSettings s);
}
class CloneSettings { double cfgWeight = 0.8; double exaggeration = 0.5; double temperature = 0.5; int seed = 0; }
class SpeechAudio { Float32List samples; int sampleRate; }

/// Plain (non-cloned) TTS voices, e.g. Sarvam stock voices. Not needed yet.
abstract class TextToSpeech { Future<SpeechAudio> speak(String text, String voiceId); }
```

Implementations for Phase 3: `GroqSpeechToText`, `GroqCleanup`, `OpenRouterCleanup` (`:free` models), `BanglaBoxCloud`. `ManualColab` isn't an HTTP provider. It's a screen that copies the prepared script for the notebook and imports the WAV you download.

**Why sentence by sentence:** you get a real progress bar ("4 of 7"), a failed sentence can be retried without redoing the rest, and no single HTTP request runs long enough to hit a timeout. The app normalises and splits the text, which also lets you preview exactly what will be spoken.

## 3. Settings model

Non-secret settings go in one JSON object (`shared_preferences`, which on Windows sits in the roaming AppData folder). Secrets go in secure storage (section 4). Defaults are copied from the prototype.

| Key | Default | Notes |
|---|---|---|
| `schemaVersion` | 1 | bump + migrate when fields change |
| `stt.provider` / `stt.model` | `groq` / `whisper-large-v3` | turbo is the other option |
| `stt.language` | `""` (auto) | `bn` forces Bangla script |
| `stt.prompt` | prototype's vocabulary hint | Groq limit: **224 tokens** |
| `cleanup.provider` / `cleanup.model` | `groq` / `openai/gpt-oss-120b` | `reasoning_effort: low` |
| `cleanup.prompt` | prototype's prompt with `${output}` | |
| `hotkeys.raw` / `hotkeys.clean` | `ctrl+alt+d` / `ctrl+alt+e` | configurable (Avro clash) |
| `audio.inputDevice` | system default | |
| `audio.beep` | true | high beep start, low beep stop |
| `paste.method` | `clipboard` | or `type` (section 7) |
| `window.onTop`, `app.startWithWindows` | false, false | |
| `clone.backend` | `manual-colab` | `banglabox-modal` once the server is deployed |
| `clone.serverUrl` | `""` | the Modal endpoint URL |
| `clone.cfgWeight`, `clone.exaggeration`, `clone.temperature`, `clone.seed` | 0.8, 0.5, 0.5, 0 | Phase 1 winner |
| `clone.pauseSeconds` | 0.25 | silence between sentences |
| `clone.voices` | `[]` | list of `VoiceProfile` (minus the audio) |

## 4. Key storage

- `flutter_secure_storage` 11.x keys: `groq_api_key`, `openrouter_api_key`, `sarvam_api_key`, `modal_token_id`, `modal_token_secret`.
- Windows build needs the **C++ ATL** component from Visual Studio Build Tools (package README). **Verify** which Windows store it uses (Credential Manager or DPAPI) in Phase 3.
- Android: turn off auto-backup for secure storage, or restores fail with "Failed to unwrap key" (package README).
- Keys are never written to the log. The logger redacts anything that looks like `gsk_…`, `sk-…` or a Modal token.
- Bring your own key: the user pastes keys in Settings, with "Get free key" links like the prototype.

## 5. Error handling

All providers throw one `ProviderError { kind, httpStatus, message, retryAfter }`, and the UI shows a plain-language message plus what to do.

| Situation | Kind | What the app does / says |
|---|---|---|
| Groq/OpenRouter **400** mentioning `reasoning` | — | retry once without `reasoning_effort` (prototype behaviour) |
| Other **400** | badRequest | "The service rejected the request" + first 300 chars, logged |
| **401** | badKey | "API key is wrong or expired. Check Settings." (Modal: "Voice server token is wrong.") |
| **402** (OpenRouter) | needsCredit | "OpenRouter needs credit. Switch back to Groq (free)." |
| **413** | tooLarge | can't happen in normal use: recordings are capped at 10 min (16 kHz mono int16 ≈ 19 MB, under Groq's 25 MB free limit) |
| **429** | rateLimited | read the `retry-after` header: "Free limit reached, try again in N s." No automatic retry for dictation (stale text pasted later is worse). Voice clone: wait and retry the sentence once. |
| **498 / 500 / 502 / 503** | serverBusy | retry once after 2 s, then "Service is busy, try again." |
| No network / DNS / TLS | offline | "No internet connection." The recording is kept so you can retry it. |
| Timeout (STT 60 s, cleanup 30 s, clone sentence 180 s) | timeout | "Took too long." First clone sentence after a cold start gets the long timeout. |
| Modal cold start | — | not an error: show "Starting your voice server (first time takes about 1 to 2 min)…" |

**Groq billing note:** each transcription is counted as at least **10 s** of audio toward the hourly (7,200 s) and daily (28,800 s) audio limits. That still allows about 720 short dictations an hour.

## 6. Silence and hallucination filters (port exactly from the prototype)

1. **Silence:** after recording, compute the peak absolute sample of the int16 PCM. If `peak < 400` (about −38 dBFS), don't send it: "No voice heard (mic level N)". The app computes the peak from the raw PCM stream itself, rather than relying on the recorder's amplitude callback.
2. **Hallucination:** normalise the text (lowercase, keep letters/digits/spaces/dots, collapse spaces):
   - if it has ≤ 10 words and contains any of: `thank you for watching`, `thanks for watching`, `please subscribe`, `like and subscribe`, `subscribe to`, `subtitles by`, `amara.org`, `see you in the next video`, `see you next time`, drop it;
   - if the recording is < 3 s and the text is one of `thank you`, `thanks`, `you`, `bye`, `okay`, `ধন্যবাদ`, `.`, drop it.
3. Strip `<think>…</think>` and surrounding quotes from cleanup replies.

The lists live in `filters.dart` with unit tests copied from real cases.

## 7. Recording, hotkeys, clipboard and paste (Windows)

**Recording:** `record` 7.x, PCM16 stream, mono, **16 kHz**. The package says Windows supports PCM16 streaming and WAV, but doesn't list sample rates. **Verify** 16 kHz on the owner's Realtek mic in Phase 3; if it refuses, record at the device rate and resample (same fallback as the prototype). The stream is fully closed after every recording (the Windows mic indicator must go away). Beeps are two short bundled WAVs played with `audioplayers`.

**Hotkeys:** `hotkey_manager` 0.4.x, system-wide scope. On Windows it reports key-down only, which suits the toggle design (press to start, press again to stop). Registration can fail if another app owns the combo: show "Ctrl+Alt+E is taken by another app, pick another in Settings". It needs Flutter 3.50 / Dart 3.14.

**Paste flow** (`paste.method = clipboard`, the prototype's behaviour):
1. Save the current clipboard text.
2. Put the result text on the clipboard.
3. Wait until Ctrl, Alt and Shift are physically released (poll `GetAsyncKeyState`, max 2 s), then 50 ms.
4. Send Ctrl+V with Win32 `SendInput` (through the `win32` FFI package: `keypress_simulator` is discontinued).
5. After 400 ms, put the saved text back.

Known limitation: Flutter's clipboard API is text-only, so if the clipboard held an image or file, it isn't restored (the prototype has the same limit). Phase 3 can save and restore all formats with Win32 calls if this bothers the owner.

**Alternative (`paste.method = type`):** type the text with `SendInput` + `KEYEVENTF_UNICODE` and don't touch the clipboard at all. Useful for apps that block paste. It may be slow for long text, and a few apps (some terminals and games) ignore it. Offered as a setting, not the default.

**Elevated apps:** Windows blocks a normal app from sending keys into an app running as administrator. The fix is to run our app as admin too (same as the prototype README says).

**Desktop shell:** `tray_manager` (tray icon + menu; keep a reference to the icon), `window_manager`, `windows_single_instance` (a second launch brings the first window forward), `launch_at_startup` (setting).

## 8. Voice clone backend

### 8.1 Shared core: `voice-server/banglabox_core.py`
- Downloads `Banglabox/chatterbox-bangla-tts` and arranges the folders (the same symlink fix as the notebook).
- Pins exactly the versions the notebook proved: torch 2.6.0, torchaudio 2.6.0, transformers 4.46.3, diffusers 0.29.0, huggingface_hub 0.25.2, numpy 2.1.2, plus `resemble-perth` (no-deps) and no torchvision.
- `load()` once per process; `speak(sentence, ref_wav_path, settings) -> (float32 samples, sr)` sets `infer.GEN` from the settings (`cfg_weight` 0.8 by default) and the seed.
- The notebook will import this file later, so Colab and Modal can't drift apart.

### 8.2 Modal deployment: `voice-server/modal_app.py`
- **Image:** `modal.Image.debian_slim(python_version="3.11")` (Chatterbox was tested on 3.11; torch 2.6 has wheels for it) with the pins above.
- **Weights on a Modal Volume** (`banglabox-weights`), downloaded once by a setup function, so a cold start reads 3.5 GB from Modal's fast storage instead of Hugging Face.
- **GPU:** start with **T4** (cheapest). Measure, then try L4 if T4 is too slow.
- A class with `@modal.enter()` loads the model once per container. `scaledown_window=120` s keeps it warm between sentences and between scripts made a minute apart. Billed while warm, so don't set it higher without a reason.
- **Endpoints** (`@modal.fastapi_endpoint`, `requires_proxy_auth=True`, so callers must send `Modal-Key` + `Modal-Secret` headers; anything else gets 401):

| Method | Body | Returns |
|---|---|---|
| `GET /health` | — | `{status, model_loaded, gpu}`; used by `warmUp()` |
| `PUT /voices/{id}` | WAV bytes (≤ 2 MB) | stores the clip on the Volume as `voices/{id}.wav`; id must equal sha256(bytes) |
| `POST /speak` | `{text, voice_id, cfg_weight, exaggeration, temperature, seed}` | `audio/wav` (24 kHz mono); **404** if the voice isn't uploaded yet |

- The app sends `/speak`. On a 404 it uploads the voice with `PUT` and retries, so clips are uploaded once and identified by their hash.
- Function `timeout=600` s, so a cold start plus a sentence always fits.

### 8.3 Cost estimate (to confirm with a real measurement)
- Modal T4: **$0.000164 per second**, about $0.59 an hour, only while a container runs. Starter plan includes **$30/month free credit** (pricing page, 2026-11-26). Whether signup needs a card: **verify**.
- One 30 s voiceover, guessing about 1× real time on a T4: ~90 s cold start + ~45 s generation + 120 s warm idle ≈ 255 s ≈ **$0.04 (about ৳5)**. Back-to-back scripts skip the cold start.
- So the free credit covers several hundred voiceovers a month. The real speed number from Phase 3 replaces this guess.
- For comparison, RunPod serverless 16 GB GPUs are $0.58/hr with no free credit listed. Modal is simpler and has the free credit.

### 8.4 Colab path (manual, free)
Stays as it is (`GUIDE_BANGLABOX.md`). The app's "Manual (Colab)" screen shows the normalised sentences with a Copy button for notebook step 9, then lets you import the downloaded WAV into the voice library.

We deliberately **don't** expose Colab to the app with a tunnel. Colab's FAQ lists web services unrelated to interactive use as not allowed on its managed runtimes (**verify** the current wording), and a free session dies after a few hours anyway.

### 8.5 Safety and privacy
- The voice clip is stored only on the owner's PC and in the owner's own Modal Volume.
- The server only accepts the owner's token. The app has no shared server.
- Every output carries Resemble AI's Perth watermark (inaudible AI-audio marker).
- The app shows a one-time consent notice: only clone your own voice or a voice you have permission to use.

## 9. Android and later platforms (for reference)

- `hotkey_manager` has no system-wide hotkeys on Android (expected). Dictation there is the Kotlin `InputMethodService` keyboard (Phase 4), calling the same Groq API with a small Kotlin client.
- `tray_manager`, `window_manager`, `windows_single_instance` and `launch_at_startup` are desktop-only and sit behind `lib/platform/`, so Android builds simply don't use them.
- `record`, `flutter_secure_storage`, `audioplayers`, `dio`/`http` and `shared_preferences` all support Android.

## 10. Phase 3 build order (proposal)

1. Flutter project in `app/`, Windows target, core package with filters, settings, Groq STT/cleanup, and tests.
2. Recorder + mic level + test mic. **Verify 16 kHz.**
3. Hotkeys + paste flow + beeps. Test in VS Code, browser, ChatGPT and Claude.
4. Tray, single instance, start with Windows, settings screen, log panel.
5. `voice-server/` + Modal deploy; **measure T4 speed and real cost**.
6. Voice tab: record reference, script editor with preview, generate via Modal or Colab import, play, save WAV (MP3 later).
7. Packaging: Inno Setup installer + portable zip, GitHub Actions on tags.

## Sources checked (2026-11-26)

- Groq: rate limits, speech-to-text, reasoning, errors, deprecations (console.groq.com/docs/…). The rate-limit table may show Developer-plan numbers (the page has Free and Developer tabs); they match CLAUDE.md's free-tier figures.
- Modal: pricing, web endpoints, proxy auth, volumes, cold start, memory snapshots, timeouts, images (modal.com/docs/guide/…).
- RunPod pricing (updated 2026-11-12).
- pub.dev: hotkey_manager 0.4.1, record 7.2.0, keypress_simulator 0.2.0 (discontinued), flutter_secure_storage 11.2.0, tray_manager 0.9.1, window_manager 0.7.1, launch_at_startup 0.5.1, windows_single_instance 1.2.0, audioplayers 6.8.1, just_audio 0.10.6, super_clipboard 0.9.1, dio 5.11.1, http 1.6.0, shared_preferences 2.5.6. Flutter stable 3.50 (Dart 3.14).
