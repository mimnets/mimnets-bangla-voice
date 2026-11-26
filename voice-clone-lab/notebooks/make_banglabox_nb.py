"""Builds banglabox_colab.ipynb. Edit this file, then run:
    python notebooks/make_banglabox_nb.py notebooks/banglabox_colab.ipynb
"""
import json, sys

cells = []
def md(s): cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip("\n")})
def code(s): cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip("\n")})

md("""
# BanglaBox voice clone (mimnets-bangla-voice, Phase 1)

Clones **your** voice from a 10 to 15 s reference clip with **BanglaBox** (a Bangla fine-tune of Chatterbox TTS) and reads the project's test scripts or your own text.

### How to run (every time)
1. Menu **Runtime → Change runtime type → T4 GPU → Save**.
2. Menu **Runtime → Run all**.
3. The first time in a new session, step 2 installs libraries and then **restarts the session on purpose** (Colab says the session crashed or restarted). That's expected.
4. Do **Runtime → Run all** a second time. Step 2 now says "already installed" and everything runs through.
5. When step 5 asks, choose your reference clip. At the end, step 10 downloads a zip of the results.

Full guide: `voice-clone-lab/GUIDE_BANGLABOX.md` in the project.

Credits: model by the BanglaBox authors (https://huggingface.co/Banglabox/chatterbox-bangla-tts, arXiv 2610.09211), built on Chatterbox by Resemble AI (MIT). Output carries Resemble AI's inaudible Perth watermark marking it as AI audio. Only clone voices you have permission to use.
""")

md("## 1. Check the GPU\nYou should see `Tesla T4`. If you see `NO GPU`, change the runtime type (see above) and run again.")
code("""
!nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || echo "NO GPU: Runtime > Change runtime type > T4 GPU"
import sys; print("Python", sys.version.split()[0])
""")

md("""
## 2. Install the libraries (3 to 5 minutes, once per session)
Exact versions from BanglaBox's `inference/requirements.txt`, plus three fixes we found on 2026-11-26:
- `huggingface_hub==0.25.2`, because `diffusers 0.29` needs an older one.
- `resemble-perth`, which Chatterbox imports but BanglaBox's list leaves out (error was `No module named 'perth'`).
- Colab's `torchvision` is removed, because it's built for a newer torch.

Then the cell **restarts the session on purpose**: Colab had already loaded a newer numpy, and without a restart you get `numpy has no attribute '_no_nep50_warning'`.

Red *"pip's dependency resolver..."* lines (about gradio, torchvision) are normal. Ignore them.
If it's already installed, this cell skips everything.
""")
code("""
import importlib.metadata as _md, os

def _ver(pkg):
    try:
        return _md.version(pkg)
    except _md.PackageNotFoundError:
        return None

_ready = ((_ver("torch") or "").startswith("2.6.0") and _ver("numpy") == "2.1.2"
          and _ver("transformers") == "4.46.3" and _ver("resemble-perth") and _ver("torchvision") is None)
if _ready:
    print("Libraries already installed. Skipping install.")
else:
    get_ipython().system(
        "pip install -q torch==2.6.0 torchaudio==2.6.0 accelerate==1.14.0 conformer==0.3.2 diffusers==0.29.0 "
        "einops==0.8.2 librosa==0.11.0 numpy==2.1.2 omegaconf==2.3.1 peft==0.17.1 s3tokenizer==0.3.0 "
        "safetensors==0.5.3 soundfile==0.13.1 tokenizers==0.20.3 transformers==4.46.3 "
        "huggingface_hub==0.25.2 bnnumerizer bnunicodenormalizer")
    get_ipython().system("pip install -q --no-deps resemble-perth")
    get_ipython().system("pip uninstall -y -q torchvision")
    print("Install finished. Restarting the session now (this is on purpose).")
    print("When it has restarted, do Runtime > Run all again.")
    os.kill(os.getpid(), 9)
""")

md("""
## 3. Download BanglaBox (about 3.5 GB, 2 to 4 minutes; seconds if already downloaded)
The model repo keeps the base model in `pretrained_models/` and the Bangla adapter in `checkpoint/adapter/`, but its `infer.py` looks for both next to itself, so this cell adds links. It also checks the session was restarted after the install.
""")
code("""
import os, numpy
if numpy.__version__ != "2.1.2":
    raise SystemExit(f"numpy {numpy.__version__} is loaded, expected 2.1.2. "
                     "Do Runtime > Restart session, then Runtime > Run all.")

from huggingface_hub import snapshot_download
ROOT = snapshot_download("Banglabox/chatterbox-bangla-tts", local_dir="/content/banglabox",
                         allow_patterns=["pretrained_models/*", "checkpoint/*", "inference/*", "voices/*"])
KIT = os.path.join(ROOT, "inference")
for name, target in [("pretrained_models", "../pretrained_models"), ("adapter", "../checkpoint/adapter")]:
    link = os.path.join(KIT, name)
    if not os.path.exists(link):
        os.symlink(target, link)
missing = [f for f in ["infer.py", "NEW_VOCAB_SIZE.txt", "pretrained_models/t3_cfg.safetensors",
                       "adapter/adapter_config.json"] if not os.path.exists(os.path.join(KIT, f))]
print("Model files OK" if not missing else f"MISSING: {missing}")
""")

md("""
## 4. Get our project code (text normaliser + test scripts)
Clones https://github.com/mimnets/mimnets-bangla-voice. If the repo is private the clone fails, and the cell asks you to upload `bangla_text.py` and the `test_scripts/*.txt` files instead.
""")
code("""
import os, shutil, subprocess
LAB = "/content/project/voice-clone-lab"
shutil.rmtree("/content/project", ignore_errors=True)
ok = subprocess.run(["git", "clone", "-q", "--depth", "1",
                     "https://github.com/mimnets/mimnets-bangla-voice.git", "/content/project"]).returncode == 0
if ok:
    print("Cloned OK")
else:
    from google.colab import files
    print("Clone failed (private repo?). Upload bangla_text.py and the test_scripts .txt files:")
    os.makedirs(f"{LAB}/test_scripts", exist_ok=True)
    for name in files.upload():
        shutil.move(name, f"{LAB}/{name}" if name.endswith(".py") else f"{LAB}/test_scripts/{name}")
print("Test scripts:", sorted(os.listdir(f"{LAB}/test_scripts")))
""")

md("""
## 5. Your reference clip
Click **Choose files** and pick your clip, usually `voice-clone-lab\\reference\\reference.wav` on your PC. WAV is best; MP3, M4A, FLAC or OGG from a phone also work.

If you already uploaded one in this session, it's reused. Set `NEW_CLIP = True` to upload a different one. Listen to the player to check it.
""")
code("""
import glob, librosa, soundfile as sf
from IPython.display import Audio, display

NEW_CLIP = False

REF_DIR = "/content/ref"
os.makedirs(REF_DIR, exist_ok=True)
existing = sorted(glob.glob(f"{REF_DIR}/*.wav"), key=os.path.getmtime)
if existing and not NEW_CLIP:
    REF = existing[-1]
    print("Reusing", REF)
else:
    from google.colab import files
    up = [n for n in files.upload() if n.lower().endswith((".wav", ".mp3", ".m4a", ".flac", ".ogg"))]
    if not up:
        raise SystemExit("No audio file chosen. Run this cell again.")
    y, sr0 = librosa.load(up[0], sr=24000, mono=True)       # any format -> 24 kHz mono
    base = os.path.splitext(os.path.basename(up[0]))[0].replace(" ", "_")
    REF = f"{REF_DIR}/{base}.wav"
    sf.write(REF, y, 24000)
    os.remove(up[0])
REF_NAME = os.path.splitext(os.path.basename(REF))[0]
dur = librosa.get_duration(path=REF)
print(f"Reference: {REF_NAME} ({dur:.1f} s)")
if dur < 8:
    print("Warning: under 8 s. 10 to 15 s gives a closer match.")
elif dur > 20:
    print("Warning: over 20 s. Trim it to 10 to 15 s of your best speech.")
display(Audio(REF))
""")

md("## 6. Load the model (1 to 2 minutes)")
code("""
import sys, time, importlib.util, torch
if importlib.util.find_spec("perth") is None:      # safety net for the missing-package error
    get_ipython().system("pip install -q --no-deps resemble-perth")
for p in (KIT, LAB):
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(KIT)
from infer import BanglaTTS
from bangla_text import prepare

if "tts" not in globals():
    t = time.time()
    tts = BanglaTTS(KIT)
    print(f"Loaded in {time.time() - t:.0f} s on", "GPU" if torch.cuda.is_available() else "CPU (very slow!)",
          "| sample rate:", tts.sr)
else:
    print("Model already loaded.")
""")

md("## 7. Quick test: one sentence")
code("""
import numpy as np

def to_np(wav):
    if hasattr(wav, "detach"):
        wav = wav.detach().cpu().numpy()
    return np.asarray(wav, dtype=np.float32).squeeze()

torch.manual_seed(0)
t = time.time()
wav, sr = tts.tts("আসসালামু আলাইকুম, আমি এখন আমার নিজের কণ্ঠে বাংলা বলছি।", REF)
wav = to_np(wav)
print(f"{len(wav) / sr:.1f} s of audio in {time.time() - t:.1f} s")
display(Audio(wav, rate=sr))
""")

md("""
## 8. Read the test scripts
Each script goes through our `bangla_text.prepare()` (numbers → Bangladeshi words, split into sentences). Each sentence is synthesised, then they're joined with a short pause.

File names include the reference clip and the seed, so takes from different clips don't overwrite each other: `banglabox_<clip>_<script>_seed<N>.wav`.
- `SEED`: change it (1, 2, 3...) to get a different "take" of the same text.
- `PAUSE_S`: the silence between sentences.
""")
code("""
import datetime

SEED = 0
PAUSE_S = 0.25
OUT = "/content/out"
os.makedirs(OUT, exist_ok=True)

def speak(text, label):
    torch.manual_seed(SEED)
    sentences = prepare(text, max_chars=200)
    pieces, t0 = [], time.time()
    for i, s in enumerate(sentences, 1):
        print(f"  {i}/{len(sentences)}  {s}")
        wav, sr = tts.tts(s, REF)
        pieces += [to_np(wav), np.zeros(int(sr * PAUSE_S), np.float32)]
    audio = np.concatenate(pieces)
    took = time.time() - t0
    path = f"{OUT}/banglabox_{REF_NAME}_{label}_seed{SEED}.wav"
    sf.write(path, audio, sr)
    print(f"Saved {os.path.basename(path)}: {len(audio) / sr:.1f} s audio in {took:.0f} s "
          f"({len(audio) / sr / took:.2f}x real time)\\n")
    display(Audio(audio, rate=sr))

for script in sorted(glob.glob(f"{LAB}/test_scripts/*.txt")):
    label = os.path.basename(script)[:-4]
    print("==", label)
    speak(open(script, encoding="utf-8").read(), label)
""")

md("## 9. Your own text (optional)\nEdit `TEXT` and run the cell. Leave it empty to skip.")
code("""
TEXT = "বন্ধুরা, আজকের ভিডিওটা শেষ পর্যন্ত দেখো। দাম মাত্র ৳৯৯৯!"
if TEXT.strip():
    speak(TEXT, "custom_" + datetime.datetime.now().strftime("%H%M%S"))
""")

md("## 10. Download all results\nDownloads `banglabox_out.zip`. Unzip the WAVs into `voice-clone-lab\\out\\` on your PC (git-ignored).")
code("""
import shutil
from google.colab import files
shutil.make_archive("/content/banglabox_out", "zip", OUT)
files.download("/content/banglabox_out.zip")
""")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
      "kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("wrote", sys.argv[1])
