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
| 2 | `bangla_text.py` | Normalise Bangla text and split it into sentences |
| 3 | `sarvam_clone.py` | Clone with Sarvam's API |
| 4 | `notebooks/banglabox_colab.ipynb` | Clone with BanglaBox on Colab |
| 5 | `notebooks/indicf5_colab.ipynb` | Clone with IndicF5 on Colab |
| 6 | `test_scripts/` | Same three Bangla scripts for every engine |
| 7 | `RESULTS.md` | Listening scores and the final pick |

`reference/` and `out/` are git-ignored: your voice never goes into the repo.
