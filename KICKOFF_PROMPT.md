Paste everything below the line into Claude Code as your first message.

---

Hi. This repo is a Bangla voice project: a dictation app that types Bangla or English at my cursor, and a voice clone tool so I can make TikTok voiceovers in my own voice. Before you do anything, read `CLAUDE.md` and `docs/ROADMAP.md` fully. They contain the background, the APIs that already work, the mistakes to avoid, the chosen tech stack, and the plan.

There's a working Python prototype in `prototype/dictate-python/`. It's for reference only. Don't change it.

Please do Phase 0 now, then start Phase 1 (the voice clone lab). I want to test voice cloning before we build any app.

How I'd like you to work:
- I'm on Windows 11 with VS Code. Give me exact commands to run and tell me what I should see.
- Use a Python virtual environment in `voice-clone-lab/`, and read API keys from a `.env` file. Never put keys in code or commits.
- Before using any API or model, check its current docs, because things change fast. If something in CLAUDE.md is out of date, tell me and update it.
- Build one step at a time. After each script, tell me how to test it, then wait for my result before moving on.
- At the end of Phase 1, help me fill in `voice-clone-lab/RESULTS.md` and recommend which voice clone option to use. Then stop and wait for me before Phase 2.
- Make small git commits with clear messages as you go.

What I have ready: a free Groq API key. I can create a Sarvam account for free credits, and I have a Google account for Colab. I'll record my reference clip when your script is ready.

Start by confirming you've read CLAUDE.md, summarising the plan back to me in a few lines, then begin Phase 0.
