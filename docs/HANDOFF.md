# Handoff (2026-11-27)

Where the project stands, what to do next, and the gotchas learned so far.
A new Claude Code session should read `CLAUDE.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md` and then this file.

## Status at a glance

| Phase | State |
|---|---|
| 0. Repo setup | Done. GitHub: https://github.com/mimnets/mimnets-bangla-voice (branch `main`) |
| 1. Voice clone lab | Done. **BanglaBox with `cfg_weight` 0.8** chosen (`voice-clone-lab/RESULTS.md`) |
| 2. Shared design | Done. `docs/ARCHITECTURE.md`. Voice backend = Colab by hand + owner's own Modal endpoint |
| 3. Windows app | **In progress.** Steps 1 and 2 done and owner-tested; step 3 built but **not yet tested by the owner** |
| 4. Android, 5. other platforms | Not started |

## Phase 3 progress (`app/`, Flutter 3.50.1 / Dart 3.14)

Build order from `docs/ARCHITECTURE.md` section 10:

1. **Core + tests**: done. `lib/core/` holds the WAV encoder, silence and hallucination filters, `ProviderError`, `AppSettings`, provider interfaces, Groq STT and cleanup clients, and `DictationPipeline`. The live Groq check `tool/groq_smoke.dart` passed with the owner's key.
2. **Recorder + window**: done and owner-tested. The owner confirmed Bangla dictation works in the app. `lib/platform/recorder.dart` (record 7.2, PCM16 stream at 16 kHz), `storage.dart` (secure key storage, settings JSON, log redaction), `lib/ui/home_page.dart`.
   - **Still unknown:** the "measured rate ~N Hz" line from **Test mic** on the owner's Realtek mic. Ask for it. If it isn't about 16000, add resampling.
3. **Hotkeys + paste + beeps**: built, committed, analyze clean, 32 tests pass. **Not yet tested by the owner.** Files: `lib/platform/hotkeys.dart`, `paste.dart` (Win32 `SendInput` via the `win32` package), `beeps.dart`.
   - Owner test checklist:
     - Ctrl+Alt+D in Notepad, VS Code, a browser, ChatGPT and Claude: beep, speak, Ctrl+Alt+D again, low beep, text appears at the cursor.
     - Ctrl+Alt+E gives an English instruction.
     - The old clipboard text is back afterwards.
     - If a hotkey is taken (Avro), the log says so.
4. **Next:** tray icon (`tray_manager`), single instance (`windows_single_instance`), start with Windows (`launch_at_startup`), window on top. Plus a **Settings screen**: model, vocabulary hint, cleanup prompt, hotkeys (re-register on save), paste method, beep. Plus "Compare speech models" from the prototype.
5. `voice-server/` (`banglabox_core.py` + `modal_app.py`). Deploy to the owner's Modal account; **measure T4 speed and real cost**. Owner needs a Modal account (whether a card is required is unverified).
6. Voice tab: Dart port of `voice-clone-lab/bangla_text.py`, with the test cases moved to `shared/bangla_text_cases.json` and read by both Python and Dart tests. Record reference, script editor and preview, generate (Modal, or Colab import), play, save WAV.
7. Packaging: Inno Setup installer + portable zip, GitHub Actions on tags.

## How to run things (owner's machine)

```powershell
# Flutter is at C:\Users\Monir\develop\flutter\bin (on the user PATH). Terminals opened before
# 2026-11-26 23:30 need:  $env:Path = "$env:USERPROFILE\develop\flutter\bin;$env:Path"
cd C:\Users\Monir\Dev\mimnets-voice\app
flutter run -d windows        # press R in this terminal for a hot restart after code changes
flutter test                  # 32 tests
flutter analyze               # must say "No issues found!"
dart run tool/groq_smoke.dart ..\voice-clone-lab\out\banglabox\<file>.wav   # live Groq check

# Voice clone lab (Python 3.15 venv)
cd C:\Users\Monir\Dev\mimnets-voice\voice-clone-lab
.\.venv\Scripts\Activate.ps1
python record_reference.py --name calm
python -m unittest test_bangla_text -v      # 18 tests
python notebooks/make_banglabox_nb.py notebooks/banglabox_colab.ipynb   # rebuild the notebook
```

Machine: Windows 11, 16 GB RAM, **Intel UHD only (no NVIDIA GPU)**, VS Build Tools 2026 with the C++ workload and ATL, **Developer Mode on** (needed for Flutter plugins), Python 3.15, Git 2.56. `.env` in the repo root holds `GROQ_API_KEY` (git-ignored). The app stores its own copy of the key in Windows secure storage.

## Decisions made after ARCHITECTURE.md was written

- App name shown to users: **Mimnets Bangla Voice** (window title, Runner.rc). The package name stays `mimnets_bangla_voice`.
- Default STT language is **Bangla (`bn`)**. Auto-detect misheard the owner's Bangla as Spanish. The main window has a Language dropdown.
- The default Whisper vocabulary hint now ends with a colloquial Bangla sentence (তুমি কি শুনতে পাচ্ছো? ...), because Whisper wrote তুনি and পার্ছো. Saved settings holding the old default are upgraded automatically.
- `package:flutter/material.dart` is deprecated since Flutter 3.47: import `package:material_ui/material_ui.dart`.
- `keypress_simulator` is discontinued: keys are sent with Win32 `SendInput` (`win32` 6.4 API: `INPUT.Anonymous.ki`, `VIRTUAL_KEY(...)`, `KEYBD_EVENT_FLAGS(...)`).
- The hallucination filter uses Unicode letter and mark classes, so Bangla fillers like ধন্যবাদ match. The prototype's Python `\w` version never matched them.
- Optional experiment added to the roadmap: local or Bangla fine-tuned Whisper vs Groq (the owner agreed). The laptop is CPU-only, so expect it to be slow.

## Open questions and loose ends

- **BanglaBox number pronunciation:** Whisper heard "এক হাজার দুইশো পঞ্চাশ টাকা" in the cloned `script1_product` as "১০০ পন্চাস", and "বিশ পার্সেন্ট" as "২ পার্সেন". Ask the owner to re-listen. If the clip really mumbles them, consider a short pause between number groups.
- The notebook's round-2 file names repeat the setting (`..._B_cfg0.8_cfg0.8_seed0.wav`), and some include `reference.wav` in the clip name. This is cosmetic only: fix it in `make_banglabox_nb.py` (label vs `REF_NAME`).
- BanglaBox speed (x real time on a T4) was never recorded. It's needed for the Modal cost estimate.
- Colab's terms on web services weren't re-checked. That's why the Colab path stays manual.
- Modal signup card requirement: unverified.

## Gotchas for the next Claude session (tooling on this machine)

- **Bash heredocs can lose backslashes** in this environment (`\\n` became `\n`, `\\r` became a CR, and Windows paths broke). For files with backslashes, use the Write or Edit tools, not heredocs.
- **PowerShell 5.1 `Set-Content -Encoding utf8` adds a BOM.** Strip it or avoid it.
- `tar` in PowerShell can resolve to Git's GNU tar, which fails on `C:` paths. Use `$env:SystemRoot\System32\tar.exe`.
- Colab: installing BanglaBox's pinned numpy/torch needs a session restart (the notebook kills the kernel on purpose; the owner then chooses Run all again). Colab's torchvision must be removed, and `resemble-perth` must be installed with `--no-deps`.
- The owner prefers exact commands, one at a time. Long multi-line pastes get joined into one line by mistake, so give single-line commands where possible.
- At the end of each phase, stop and check in with the owner (project rule).
