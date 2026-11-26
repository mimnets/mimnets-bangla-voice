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

## Credits

This project builds on other people's work. Thank you to:

| What | By | Used for | License |
|---|---|---|---|
| [BanglaBox TTS](https://huggingface.co/Banglabox/chatterbox-bangla-tts) ([paper, arXiv 2610.09211](https://arxiv.org/abs/2610.09211)) | BanglaBox authors (anonymous for peer review) | Bangla voice cloning test (Colab notebook) | MIT per the model card |
| [BanglaBox corpus](https://huggingface.co/datasets/Banglabox/bangla-corpus) | BanglaBox authors | Training data behind the model (we don't use it directly) | CC BY 4.0 |
| [Chatterbox TTS](https://github.com/resemble-ai/chatterbox) | Resemble AI | The base model BanglaBox fine-tunes | MIT |
| [bnnumerizer](https://pypi.org/project/bnnumerizer/), [bnunicodenormalizer](https://pypi.org/project/bnunicodenormalizer/) | their authors (bnunicodenormalizer by Bengali.AI) | BanglaBox's own text normaliser | see their PyPI pages |
| [Whisper large-v3](https://github.com/openai/whisper) | OpenAI, served by [Groq](https://groq.com) | Speech to text in the dictation prototype | MIT (model), Groq terms (API) |
| [IndicF5](https://huggingface.co/ai4bharat/IndicF5) | AI4Bharat | Planned optional voice clone test | MIT |
| [Handy](https://handy.computer) | Handy contributors | Inspiration for the dictation app design | MIT |
| [sounddevice](https://python-sounddevice.readthedocs.io), [NumPy](https://numpy.org), [requests](https://requests.readthedocs.io), [keyboard](https://github.com/boppreh/keyboard), [pyperclip](https://github.com/asweigart/pyperclip) | their maintainers | Recording, audio maths, HTTP, hotkeys, clipboard | MIT, BSD-3, Apache-2.0, MIT, BSD-3 |
| [Google Colab](https://colab.research.google.com) | Google | Free GPU for testing models | Google terms |

If you publish audio made with BanglaBox or Chatterbox, please credit them. Only clone voices you have permission to use.
