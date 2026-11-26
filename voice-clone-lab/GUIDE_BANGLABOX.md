# Guide: make a BanglaBox voice clone (step by step)

Use this every time you want to try again, for example with a cleaner recording of your voice.
It takes about 15 minutes. Nothing is installed on your PC except the small recorder.

**The idea in one line:** you record 10 to 15 seconds of your voice on your PC, then Google Colab (a free computer with a GPU) uses BanglaBox to read any Bangla text in that voice.

---

## Part A: Record a better reference clip (on your PC)

The clone copies **everything** in your clip: your voice, but also echo, fan noise, a tired tone or a laptop-mic hiss. A better clip gives a better clone. That matters more than anything else in this guide.

### A1. Get the room ready
- **Quiet:** fan off, AC off if you can, window closed, phone on silent, no TV or music.
- **Less echo:** a small room with curtains, a bed or clothes is better than an empty room with bare walls. Sitting near a wardrobe or under a blanket fort sounds silly, but it works.
- **Mic:** a headset or earphones with a mic, or a USB mic, usually sounds cleaner than the laptop's built-in mic. Keep it about one hand-width from your mouth, slightly to the side so your breath doesn't hit it.

### A2. Decide how you'll sound
- Speak exactly the way you want the TikTok voice to sound: same energy, same speed, same smile.
- Want two styles, say calm and energetic? Record two clips and test both (see A4).
- Don't whisper or shout. Normal, clear, confident talking.

### A3. Record
In PowerShell:

```powershell
cd C:\Users\Monir\Dev\mimnets-voice\voice-clone-lab
.\.venv\Scripts\Activate.ps1
python record_reference.py --name calm
```

1. Notepad opens with the text to read. Read it once or twice silently first.
2. Press Enter, wait for 3-2-1, then read it.
3. Look at the check it prints:
   - `Level check: OK` is good.
   - "Too quiet": move closer, or raise the mic volume in Windows Settings → System → Sound → your mic → Input volume.
   - "Too loud (clipping)": move back a little, or lower the input volume.
   - "Background is noisy": find a quieter spot.
4. Listen to the playback. Type `r` to redo it if you stumbled, laughed or a noise happened. Type `k` to keep it.

To read your own text instead of the built-in greeting: save it as a UTF-8 `.txt` file (Notepad saves UTF-8 by default), then run
`python record_reference.py --name energetic --text-file my_text.txt`.
Pick text that sounds like your real videos and has a question and an exclamation in it.

### A4. What you get
Files in `voice-clone-lab\reference\` (git-ignored, never uploaded to GitHub):
- `calm_20261127_103000.wav`: this clip, named with your `--name`.
- `reference.wav`: always the **latest** clip.

Use different `--name` values (`calm`, `energetic`, `headset`, `laptopmic`) so you can compare later. The name appears in the output file names.

**Phone option:** you can also record on your phone (a voice recorder app, quiet room, 10 to 15 s) and upload that file in Part B. MP3, M4A and WAV all work.

---

## Part B: Make the clone in Google Colab

### B1. Open the notebook
- Go to https://colab.research.google.com and sign in with your Google account.
- **File → Upload notebook** → pick `voice-clone-lab\notebooks\banglabox_colab.ipynb`.
  (If your GitHub repo is public you can use **File → Open notebook → GitHub** and paste `mimnets/mimnets-bangla-voice` instead, so you always get the latest version.)

### B2. Turn on the free GPU
**Runtime → Change runtime type → T4 GPU → Save.**

### B3. Run all (twice)
1. **Runtime → Run all.**
2. Step 2 installs the libraries (3 to 5 minutes), then **restarts the session on purpose**. Colab may say "Your session crashed". That's expected and fine.
3. **Runtime → Run all again.** Step 2 now says "already installed" and the rest runs.
4. At **step 5**, click **Choose files** and pick your clip, e.g. `reference\calm_....wav`. Listen to the player.
5. Wait. Steps 7 and 8 show audio players as each piece finishes. All three test scripts take a few minutes on the T4.
6. Step 10 downloads `banglabox_out.zip`. Unzip it into `voice-clone-lab\out\`.

### B4. Try more in the same session (no reinstall needed)
- **Different take of the same text:** in step 8 set `SEED = 1` (then 2, 3...) and run step 8 again. Each seed sounds slightly different; keep the best.
- **Different clip:** in step 5 set `NEW_CLIP = True`, run step 5 and pick the other file, then run steps 7, 8 and 10.
- **Your own script:** edit `TEXT` in step 9 and run it.

Output names look like `banglabox_calm_script1_product_seed0.wav`, so nothing gets overwritten and you can tell clips and seeds apart.

**Colab limits:** the free GPU disconnects after you're idle for a while, or after a few hours. If that happens, start again at B2. Everything is re-created automatically; you only re-upload your clip.

---

## Part C: Judge and record the result

Listen with headphones and write in `RESULTS.md`:
1. **Sounds like me?** (1 to 5)
2. **Sounds Bangladeshi?** (1 to 5, or "Kolkata-ish")
3. **Natural?** (1 to 5: robotic, flat, rushed, odd pauses?)
4. **Wrong words:** write the word and how it came out.
5. **Speed:** the "x real time" number step 8 printed.
6. Which clip and seed was best.

---

## Part D: If something goes wrong

These are the problems we hit on the first run (2026-11-26). The notebook now prevents or handles all of them, but here's what each one means.

| You see | What it means | Fix |
|---|---|---|
| `NO GPU` in step 1, or "CPU (very slow!)" in step 6 | GPU not turned on | Runtime → Change runtime type → T4 GPU, then Run all |
| Red `ERROR: pip's dependency resolver...` about gradio or torchvision | Colab's own extras want other versions; we don't use them | Ignore |
| "Your session crashed" right after step 2 | On purpose: new library versions load only after a restart | Runtime → Run all again |
| `module 'numpy' has no attribute '_no_nep50_warning'`, or step 3 says "numpy ... is loaded, expected 2.1.2" | The session wasn't restarted after installing | Runtime → Restart session, then Run all |
| `No module named 'perth'` | A package BanglaBox forgot to list | Step 2 and step 6 now install it; if you still see it, run `!pip install -q --no-deps resemble-perth` in a new cell |
| "Clone failed" in step 4 | Your GitHub repo is private | Upload `bangla_text.py` and the `test_scripts` `.txt` files when it asks |
| `MISSING: [...]` in step 3 | Download was interrupted or the model repo changed | Run step 3 again; if it persists, tell Claude Code which file is missing |
| Gets cut off / "You cannot currently connect to a GPU" | Free GPU quota used up for now | Try again in a few hours, or use Kaggle's free GPU |
| Some words keep coming out wrong | Pronunciation/normalisation | Note them in RESULTS.md; we can fix spellings in `bangla_text.py` |

---

## Credits

BanglaBox model by the BanglaBox authors (https://huggingface.co/Banglabox/chatterbox-bangla-tts, arXiv 2610.09211, MIT per model card), built on Chatterbox TTS by Resemble AI (MIT). Every output carries Resemble AI's inaudible Perth watermark marking it as AI-generated. Only clone voices you have permission to use. Full credits are in the root `README.md`.
