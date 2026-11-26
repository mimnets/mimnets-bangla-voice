# Voice clone lab (Phase 1)

Experiments to find which voice clone option makes the owner's voice sound right in Bangladeshi Bangla.

## One-time setup (PowerShell, from the repo root)

```powershell
cd voice-clone-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1`, run this once and try again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Each new terminal: `cd voice-clone-lab` then `.\.venv\Scripts\Activate.ps1`.

Keys are read from the `.env` file in the repo root (see `.env.example`).

## Scripts

| Step | File | What it does |
|---|---|---|
| 1 | `record_reference.py` | Record a 10 to 15 s reference clip plus its transcript into `reference/` |
| 2 | `bangla_text.py` | Normalise Bangla text (numbers, money, dates, English words) and split it into sentences. Tests: `python -m unittest test_bangla_text -v` |
| 3 | `sarvam_clone.py` | Clone with Sarvam's API (**skipped for now**, owner chose BanglaBox first) |
| 4 | `notebooks/banglabox_colab.ipynb` | Clone with BanglaBox on Google Colab's free GPU |
| 5 | `notebooks/indicf5_colab.ipynb` | Clone with IndicF5 on Colab (optional, later) |
| 6 | `test_scripts/` | Three ~30 s Bangla TikTok-style scripts every engine reads |
| 7 | `RESULTS.md` | Listening scores and the final pick |

`reference/` and `out/` are git-ignored: your voice never goes into the repo.

## Guide: test BanglaBox on Google Colab

Colab is Google's free notebook service. It lends you a GPU (an NVIDIA T4) for a few hours, which BanglaBox needs. Nothing gets installed on your PC.

1. **Record your reference clip** (step 1 above) so you have `voice-clone-lab\reference\reference.wav`.
2. **Open the notebook in Colab**, either way:
   - If the GitHub repo is public, open this link:
     https://colab.research.google.com/github/mimnets/mimnets-bangla-voice/blob/main/voice-clone-lab/notebooks/banglabox_colab.ipynb
   - Otherwise go to https://colab.research.google.com, sign in with your Google account, choose **File → Upload notebook**, and pick `voice-clone-lab\notebooks\banglabox_colab.ipynb`.
3. **Turn on the GPU:** menu **Runtime → Change runtime type → T4 GPU → Save**.
4. **Run the cells one at a time, top to bottom** (click ▶ on each and wait until it finishes):
   1. GPU check: should print `Tesla T4`.
   2. Install: 3 to 5 minutes. Red "dependency resolver" lines are normal. It then restarts the session on purpose ("session crashed" is expected); continue at step 3. If you ever see `numpy has no attribute _no_nep50_warning`, do **Runtime → Restart session** and run from step 3 again.
   3. Download BanglaBox: about 3.5 GB. All four lines should say `OK`.
   4. Get project code: clones this repo for `bangla_text.py` and the test scripts. If the repo is private it says "Clone failed"; then run the upload cell below it and upload `bangla_text.py` plus the three `test_scripts\*.txt` files.
   5. Upload `reference.wav`, then listen to the player.
   6. Load model: should say `on GPU`.
   7. Quick test: one sentence in your voice.
   8. All three test scripts: each one shows a player and its speed.
   9. Optional: type your own text.
   10. Download `banglabox_out.zip` and unzip it into `voice-clone-lab\out\`.
5. **Write down what you hear** in `RESULTS.md`: does it sound like you, does it sound Bangladeshi, which words it got wrong, and the speed it printed.

Notes:
- Colab's free GPU switches off after you're idle for a while, or after a few hours. If that happens, run everything from the top again.
- Change `SEED` in step 8 and re-run it to hear a different "take" of the same script.
- Colab is only for **testing**. If BanglaBox wins, Phase 2 decides where it runs for real: your own PC if it has an NVIDIA GPU, or a pay-per-use cloud GPU the app calls.

## Credits

See the Credits section in the root `README.md`.
