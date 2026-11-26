"""Record a 10 to 15 second reference clip for voice cloning.

Usage (from voice-clone-lab, with the venv active):
    python record_reference.py                 # record 12 s with the default mic
    python record_reference.py --seconds 15
    python record_reference.py --list-devices
    python record_reference.py --device 3

What it does:
  1. Opens the text to read in Notepad (Bangla renders better there than in a terminal).
  2. Counts down 3-2-1, records with a live level bar.
  3. Checks the level (too quiet, clipping, noisy room) and trims long silence.
  4. Plays the clip back and asks: keep, redo, or quit.
  5. Saves reference/<name>_<time>.wav + .txt and also reference/reference.wav + .txt
     (the "current" clip the clone scripts use). reference/ is git-ignored.
"""

import argparse
import os
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd

HERE = Path(__file__).resolve().parent
REF_DIR = HERE / "reference"
TARGET_RATE = 24000  # Hz, mono int16. IndicF5 outputs 24 kHz; others accept it.

SUGGESTED_TEXT = (
    "আসসালামু আলাইকুম, সবাইকে স্বাগতম। "
    "আজকে আমি তোমাদের সাথে একটা দারুণ জিনিস শেয়ার করবো, "
    "যেটা দেখলে তোমরা সত্যিই অবাক হয়ে যাবে। "
    "তাহলে চলো, শুরু করা যাক!"
)

# Level thresholds for int16 audio.
QUIET_PEAK = 4000        # loudest point under this -> speak up / move closer
CLIP_LEVEL = 32000       # samples at or above this count as clipped
CLIP_RATIO = 0.001       # more than 0.1 % clipped samples -> too loud
NOISE_FLOOR_DB = -50.0   # quietest parts louder than this -> noisy room
SILENCE_DB = -45.0       # 20 ms windows below this count as silence when trimming


def list_input_devices():
    """Microphones on the default host API (same filter as the prototype)."""
    try:
        host = sd.default.hostapi
    except Exception:
        host = None
    out = []
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) < 1:
            continue
        if host is not None and d.get("hostapi") != host:
            continue
        out.append((i, d["name"]))
    return out


def db(x):
    return 20 * np.log10(max(float(x), 1.0) / 32768.0)


def window_rms_db(audio, rate, ms=20):
    n = max(1, int(rate * ms / 1000))
    usable = len(audio) // n * n
    if usable == 0:
        return np.array([db(0)])
    frames = audio[:usable].astype(np.float32).reshape(-1, n)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    return 20 * np.log10(np.maximum(rms, 1.0) / 32768.0)


def resample(audio, src_rate, dst_rate):
    """Simple resampler, good enough for speech. Averages first when downsampling by an integer factor."""
    if src_rate == dst_rate:
        return audio
    x = audio.astype(np.float32)
    if src_rate % dst_rate == 0:
        k = src_rate // dst_rate
        x = x[: len(x) // k * k].reshape(-1, k).mean(axis=1)
    else:
        n_out = int(round(len(x) * dst_rate / src_rate))
        x = np.interp(np.linspace(0, len(x) - 1, n_out), np.arange(len(x)), x)
    return np.clip(np.round(x), -32768, 32767).astype(np.int16)


def record(seconds, device):
    """Record mono int16. Tries 24 kHz directly, then the device's own rate (resampled after)."""
    frames = []
    level = [0.0]

    def cb(indata, n, t, status):
        frames.append(indata.copy())
        level[0] = float(np.abs(indata).max())

    last_err = None
    for rate in (TARGET_RATE, None):
        try:
            if rate is None:
                rate = int(sd.query_devices(device, "input")["default_samplerate"])
            stream = sd.InputStream(samplerate=rate, channels=1, dtype="int16",
                                    device=device, callback=cb)
            break
        except Exception as e:
            last_err = e
    else:
        raise SystemExit(f"Could not open the microphone: {last_err}")

    with stream:  # the stream is fully closed when this block ends
        start = time.time()
        while (elapsed := time.time() - start) < seconds:
            bars = int(min(1.0, level[0] / 32768.0) * 30)
            meter = "#" * bars + "-" * (30 - bars)
            warn = "  TOO LOUD" if level[0] >= CLIP_LEVEL else ""
            print(f"\r  REC {elapsed:4.1f}/{seconds}s  [{meter}]{warn}   ", end="", flush=True)
            time.sleep(0.05)
    print()
    audio = np.concatenate(frames)[:, 0] if frames else np.zeros(0, np.int16)
    return resample(audio, rate, TARGET_RATE)


def trim_silence(audio, rate, keep_ms=300):
    """Cut silence at the start and end, leaving keep_ms of padding."""
    win = int(rate * 0.02)
    levels = window_rms_db(audio, rate)
    voiced = np.where(levels > SILENCE_DB)[0]
    if len(voiced) == 0:
        return audio
    pad = int(rate * keep_ms / 1000)
    start = max(0, voiced[0] * win - pad)
    end = min(len(audio), (voiced[-1] + 1) * win + pad)
    return audio[start:end]


def check_level(audio, rate, raw=None):
    """Return (problems, info_lines). problems is a list of strings; empty means OK.

    raw is the untrimmed recording; its quietest parts (before you start talking,
    pauses between words) give the background noise level.
    """
    problems = []
    if len(audio) == 0:
        return ["Nothing was recorded."], []
    peak = int(np.abs(audio.astype(np.int32)).max())
    clipped = float(np.mean(np.abs(audio.astype(np.int32)) >= CLIP_LEVEL))
    levels = window_rms_db(audio, rate)
    noise_floor = float(np.percentile(window_rms_db(raw if raw is not None else audio, rate), 5))
    speech_level = float(np.percentile(levels, 90))
    duration = len(audio) / rate

    info = [
        f"Length after trimming: {duration:.1f} s",
        f"Peak: {peak} ({db(peak):.1f} dBFS)",
        f"Speech level: {speech_level:.1f} dBFS, background: {noise_floor:.1f} dBFS",
        f"Clipped samples: {clipped * 100:.2f} %",
    ]
    if peak < QUIET_PEAK:
        problems.append("Too quiet. Move closer to the mic or raise the mic volume in Windows sound settings.")
    if clipped > CLIP_RATIO:
        problems.append("Too loud (clipping). Move back a little or lower the mic volume.")
    if noise_floor > NOISE_FLOOR_DB:
        problems.append("Background is noisy. Turn off fans/TV, close the window, try a quieter room.")
    if duration < 8:
        problems.append(f"Only {duration:.1f} s of speech. Aim for 10 to 15 s; read a bit slower or add a sentence.")
    return problems, info


def save_wav(path, audio, rate):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(audio.astype("<i2").tobytes())


def open_in_notepad(path):
    try:
        os.startfile(str(path))  # Windows: opens .txt in the default editor
    except Exception:
        pass


def ask(prompt, choices):
    while True:
        ans = input(prompt).strip().lower()
        default = next((c for c in choices if c.isupper()), None)
        if ans == "" and default:
            return default.lower()
        if len(ans) == 1 and ans in choices.lower():
            return ans
        print(f"  Please type one of: {', '.join(choices.lower())}")


def main():
    p = argparse.ArgumentParser(description="Record a voice clone reference clip.")
    p.add_argument("--seconds", type=float, default=12, help="recording length, 10 to 15 recommended (default 12)")
    p.add_argument("--device", type=int, default=None, help="microphone index from --list-devices")
    p.add_argument("--name", default="me", help="label for the saved files (default: me)")
    p.add_argument("--list-devices", action="store_true", help="show microphones and exit")
    p.add_argument("--no-open", action="store_true", help="don't open the text in Notepad")
    args = p.parse_args()

    if args.list_devices:
        default_in = sd.default.device[0]
        for i, name in list_input_devices():
            mark = "  (default)" if i == default_in else ""
            print(f"{i:3}: {name}{mark}")
        return

    REF_DIR.mkdir(exist_ok=True)
    read_file = REF_DIR / "read_this.txt"
    read_file.write_text(SUGGESTED_TEXT + "\n", encoding="utf-8")

    mic = sd.query_devices(args.device, "input")["name"]
    print(f"Microphone: {mic}")
    print("Tips: quiet room, no music, mic about one hand-width from your mouth,")
    print("      speak in your normal TikTok tone.\n")
    print("Read this text (also opened in Notepad):\n")
    print("  " + SUGGESTED_TEXT + "\n")
    if not args.no_open:
        open_in_notepad(read_file)

    while True:
        input("Press Enter when you're ready...")
        for n in (3, 2, 1):
            print(f"  {n}...", flush=True)
            time.sleep(1)
        print("  Speak now!")
        raw = record(args.seconds, args.device)
        audio = trim_silence(raw, TARGET_RATE)

        problems, info = check_level(audio, TARGET_RATE, raw)
        print()
        for line in info:
            print("  " + line)
        if problems:
            print("\n  Problems found:")
            for prob in problems:
                print("   - " + prob)
        else:
            print("\n  Level check: OK")

        if len(audio):
            print("\nPlaying it back...")
            sd.play(audio, TARGET_RATE)
            sd.wait()

        prompt = "\nKeep it, redo, or quit? " + ("[k/R/q] " if problems else "[K/r/q] ")
        choice = ask(prompt, "kRq" if problems else "Krq")
        if choice == "q":
            print("Nothing saved.")
            return
        if choice == "k" and len(audio):
            break
        print()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    wav_path = REF_DIR / f"{args.name}_{stamp}.wav"
    txt_path = wav_path.with_suffix(".txt")
    save_wav(wav_path, audio, TARGET_RATE)
    save_wav(REF_DIR / "reference.wav", audio, TARGET_RATE)

    same = ask("\nDid you read the text exactly as written? [Y/n] ", "Yn")
    transcript = SUGGESTED_TEXT
    txt_path.write_text(transcript + "\n", encoding="utf-8")
    if same == "n":
        print("Notepad will open the transcript. Change it to exactly what you said, save (Ctrl+S), close it.")
        os.system(f'notepad "{txt_path}"')  # waits until Notepad is closed
        transcript = txt_path.read_text(encoding="utf-8").strip()
    (REF_DIR / "reference.txt").write_text(transcript + "\n", encoding="utf-8")

    print("\nSaved:")
    print(f"  {wav_path}")
    print(f"  {txt_path}")
    print(f"  {REF_DIR / 'reference.wav'}  (current reference used by the clone scripts)")
    print(f"  {REF_DIR / 'reference.txt'}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(1)
