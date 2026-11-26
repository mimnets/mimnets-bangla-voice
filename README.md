# mimnets-bangla-voice

Bangla and English dictation that types where your cursor is, plus a Bangla voice clone tool for TikTok voiceovers.

- `prototype/dictate-python/`: working Windows dictation prototype (Groq Whisper, free). Reference only.
- `voice-clone-lab/`: voice cloning experiments (Phase 1, Python).
- `app/`: the cross-platform Flutter app (Phase 3 onward).

Project context for AI coding tools is in `CLAUDE.md`. The plan is in `docs/ROADMAP.md`.

## API keys

Copy `.env.example` to `.env` in the repo root and paste your keys there. `.env` is git-ignored.

```powershell
copy .env.example .env
notepad .env
```
