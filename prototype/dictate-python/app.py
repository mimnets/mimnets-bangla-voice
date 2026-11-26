"""
Bangla Dictate (window version)

Click Record (or use a hotkey), speak, stop. The text shows in the window,
and with a hotkey it is also typed wherever your cursor is.
Speech is transcribed by OpenRouter.

Run:  python app.py
"""

import base64
import io
import json
import os
import queue
import re
import threading
import time
import tkinter as tk
import wave
import webbrowser
from tkinter import ttk

import keyboard
import numpy as np
import pyperclip
import requests
import sounddevice as sd

try:
    import winsound
except ImportError:
    winsound = None

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
STT_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

# Things Whisper "hears" in silence or noise (it learned them from video subtitles)
HALLUCINATIONS = [
    "thank you for watching", "thanks for watching", "please subscribe",
    "like and subscribe", "subscribe to", "subtitles by", "amara.org",
    "see you in the next video", "see you next time",
]
SHORT_FILLERS = {"thank you", "thanks", "you", "bye", "okay", "ধন্যবাদ", "."}
PROVIDERS = {"Groq (free)": "groq", "OpenRouter (paid)": "openrouter"}
GROQ_MODELS = ["whisper-large-v3", "whisper-large-v3-turbo"]

STT_MODELS = [
    "openai/whisper-large-v3",
    "openai/whisper-large-v3-turbo",
    "openai/gpt-4o-transcribe",
    "openai/gpt-4o-mini-transcribe",
    "google/gemini-3.5-transcribe",
    "elevenlabs/scribe-v2",
]
LANGUAGES = {"Auto detect": "", "Bangla (bn)": "bn", "English (en)": "en"}

DEFAULTS = {
    "api_key": "",
    "groq_api_key": "",
    "stt_provider": "groq",
    "groq_model": "whisper-large-v3",
    "stt_model": "openai/whisper-large-v3",
    "language": "",
    "stt_prompt": "Mixed Bangla and English speech about programming and AI tools. "
                  "Words like VS Code, Python, JavaScript, React, function, API, file, "
                  "folder, Claude, ChatGPT.",
    "hotkey_raw": "ctrl+alt+d",
    "hotkey_clean": "ctrl+alt+e",
    "cleanup_provider": "groq",
    "groq_cleanup_model": "openai/gpt-oss-120b",
    "cleanup_model": "openrouter/free",
    "cleanup_prompt": "You are cleaning up voice dictation. The speaker talks in Bangla, "
                      "English, or a mix.\nFix transcription mistakes, then rewrite it as a "
                      "clear English instruction.\nKeep code terms, file names, and technical "
                      "words exactly as spoken.\nOutput only the final text, nothing else.\n\n"
                      "${output}",
    "input_device": None,
    "sample_rate": 16000,
    "beep": True,
    "on_top": False,
}


# ---------------- config ----------------

def load_config():
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    if "PASTE_YOUR" in (cfg.get("api_key") or ""):
        cfg["api_key"] = ""
    # old version used F8/F9, which need Fn on most laptops
    if cfg.get("hotkey_raw") == "f8":
        cfg["hotkey_raw"] = DEFAULTS["hotkey_raw"]
    if cfg.get("hotkey_clean") == "f9":
        cfg["hotkey_clean"] = DEFAULTS["hotkey_clean"]
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ---------------- helpers ----------------

def to_wav_bytes(audio, rate):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(rate))
        w.writeframes(audio.astype(np.int16).tobytes())
    return buf.getvalue()


def strip_thinking(s):
    s = re.sub(r"<think>.*?</think>", "", s or "", flags=re.S | re.I)
    return s.strip().strip('"').strip()


def is_hallucination(text, seconds):
    t = re.sub(r"[^\w\s.]", " ", text.lower()).strip()
    t = re.sub(r"\s+", " ", t)
    words = len(t.split())
    if words <= 10 and any(h in t for h in HALLUCINATIONS):
        return True
    if seconds < 3 and t.strip(" .") in SHORT_FILLERS:
        return True
    return False


def list_input_devices():
    """Return [(index, name)] of microphones, de-duplicated to the default host API."""
    devices = sd.query_devices()
    try:
        host = sd.default.hostapi
    except Exception:
        host = None
    out = []
    for i, d in enumerate(devices):
        if d.get("max_input_channels", 0) < 1:
            continue
        if host is not None and d.get("hostapi") != host:
            continue
        out.append((i, d["name"]))
    return out


def wait_for_modifiers_release(timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if not any(keyboard.is_pressed(k) for k in ("ctrl", "alt", "shift")):
                return
        except Exception:
            return
        time.sleep(0.05)


def paste_text(text):
    try:
        old = pyperclip.paste()
    except Exception:
        old = None
    pyperclip.copy(text)
    wait_for_modifiers_release()
    time.sleep(0.05)
    keyboard.send("ctrl+v")
    if old is not None:
        time.sleep(0.4)
        try:
            pyperclip.copy(old)
        except Exception:
            pass


# ---------------- app ----------------

class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.q = queue.Queue()

        self.recording = False
        self.mode = "raw"
        self.target = "ui"
        self.frames = []
        self.level = 0.0
        self.stream = None
        self.rate = self.cfg.get("sample_rate", 16000)
        self.busy = False
        self.hotkey_handles = []

        root.title("Bangla Dictate")
        root.geometry("620x640")
        root.minsize(520, 560)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_ui()
        self.register_hotkeys()
        self.root.attributes("-topmost", bool(self.cfg.get("on_top")))
        self.root.after(50, self.poll)

        if not self.speech_key():
            self.log("Paste your free Groq API key at the top (click 'Get free key'), "
                     "then click Save keys.")
            self.set_status("Add your Groq API key first", "#b36b00")
        else:
            self.log("Ready. Click Record, or use the hotkeys in any app.")

    # ----- UI -----

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Status.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Big.TButton", font=("Segoe UI", 12, "bold"), padding=10)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # --- Dictate tab ---
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="  Dictate  ")

        self.key_var = tk.StringVar(value=self.cfg.get("api_key", ""))
        self.groq_key_var = tk.StringVar(value=self.cfg.get("groq_api_key", ""))
        keys = ttk.Frame(tab)
        keys.pack(fill="x", pady=(0, 10))
        keys.columnconfigure(1, weight=1)
        ttk.Label(keys, text="Groq API key (free, for speech)").grid(row=0, column=0, sticky="w")
        self.groq_entry = ttk.Entry(keys, textvariable=self.groq_key_var, show="•")
        self.groq_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=2)
        link = ttk.Label(keys, text="Get free key", foreground="#0a58ca", cursor="hand2")
        link.grid(row=0, column=2, sticky="w")
        link.bind("<Button-1>", lambda e: webbrowser.open("https://console.groq.com/keys"))
        ttk.Label(keys, text="OpenRouter API key (optional)").grid(row=1, column=0, sticky="w")
        self.key_entry = ttk.Entry(keys, textvariable=self.key_var, show="•")
        self.key_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=2)
        self.show_key = tk.BooleanVar(value=False)
        ttk.Checkbutton(keys, text="Show", variable=self.show_key,
                        command=self.toggle_show_keys).grid(row=1, column=2, sticky="w")
        ttk.Button(keys, text="Save keys", command=self.save_key).grid(
            row=0, column=3, rowspan=2, sticky="ns", padx=(8, 0))

        self.status_var = tk.StringVar(value="Ready")
        self.status_lbl = ttk.Label(tab, textvariable=self.status_var, style="Status.TLabel")
        self.status_lbl.pack(anchor="w")

        meter_row = ttk.Frame(tab)
        meter_row.pack(fill="x", pady=(6, 10))
        ttk.Label(meter_row, text="Mic level").pack(side="left")
        self.meter = ttk.Progressbar(meter_row, maximum=100, length=300)
        self.meter.pack(side="left", fill="x", expand=True, padx=8)

        mode_row = ttk.Frame(tab)
        mode_row.pack(fill="x")
        self.mode_var = tk.StringVar(value="raw")
        ttk.Radiobutton(mode_row, text="Type what I said", value="raw",
                        variable=self.mode_var).pack(side="left")
        ttk.Radiobutton(mode_row, text="Clean up into English prompt", value="clean",
                        variable=self.mode_var).pack(side="left", padx=16)

        btn_row = ttk.Frame(tab)
        btn_row.pack(fill="x", pady=10)
        self.rec_btn = ttk.Button(btn_row, text="●  Record", style="Big.TButton",
                                  command=self.on_record_button)
        self.rec_btn.pack(side="left")
        ttk.Button(btn_row, text="Test mic (3 sec + playback)",
                   command=self.test_mic).pack(side="left", padx=10)

        ttk.Label(tab, text="Result").pack(anchor="w")
        self.result = tk.Text(tab, height=6, wrap="word", font=("Segoe UI", 12))
        self.result.pack(fill="both", expand=True)
        res_row = ttk.Frame(tab)
        res_row.pack(fill="x", pady=(4, 8))
        ttk.Button(res_row, text="Copy", command=self.copy_result).pack(side="left")
        ttk.Button(res_row, text="Clear", command=lambda: self.result.delete("1.0", "end")
                   ).pack(side="left", padx=6)
        self.top_var = tk.BooleanVar(value=bool(self.cfg.get("on_top")))
        ttk.Checkbutton(res_row, text="Keep window on top", variable=self.top_var,
                        command=self.toggle_on_top).pack(side="right")

        self.hint_var = tk.StringVar()
        ttk.Label(tab, textvariable=self.hint_var, foreground="#555",
                  wraplength=560, justify="left").pack(anchor="w", pady=(0, 6))
        self.update_hint()

        ttk.Label(tab, text="Log").pack(anchor="w")
        self.logbox = tk.Text(tab, height=7, wrap="word", font=("Consolas", 9),
                              background="#f6f6f6")
        self.logbox.pack(fill="both", expand=True)

        # --- Settings tab ---
        st = ttk.Frame(self.notebook, padding=12)
        self.settings_tab = st
        self.notebook.add(st, text="  Settings  ")
        st.columnconfigure(1, weight=1)
        r = 0

        def row(label):
            nonlocal r
            ttk.Label(st, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 8))
            r += 1
            return r - 1

        prov_name = next((k for k, v in PROVIDERS.items() if v == self.cfg.get("stt_provider")),
                         "Groq (free)")
        self.provider_var = tk.StringVar(value=prov_name)
        prov_box = ttk.Combobox(st, textvariable=self.provider_var, values=list(PROVIDERS),
                                state="readonly")
        prov_box.grid(row=row("Speech provider"), column=1, sticky="ew")
        prov_box.bind("<<ComboboxSelected>>", lambda e: self.on_provider_change())

        self.mic_choices = [("Default microphone", None)]
        try:
            self.mic_choices += [(f"{i}: {n}", i) for i, n in list_input_devices()]
        except Exception as e:
            self.log(f"Could not list microphones: {e}")
        mic_names = [n for n, _ in self.mic_choices]
        current = next((n for n, i in self.mic_choices if i == self.cfg.get("input_device")),
                       "Default microphone")
        self.mic_var = tk.StringVar(value=current)
        ttk.Combobox(st, textvariable=self.mic_var, values=mic_names, state="readonly").grid(
            row=row("Microphone"), column=1, sticky="ew")

        self.model_var = tk.StringVar(value=self.current_model())
        self.model_box = ttk.Combobox(st, textvariable=self.model_var,
                                      values=self.models_for(self.cfg.get("stt_provider")))
        self.model_box.grid(row=row("Speech model"), column=1, sticky="ew")

        lang_name = next((k for k, v in LANGUAGES.items() if v == self.cfg.get("language")),
                         "Auto detect")
        self.lang_var = tk.StringVar(value=lang_name)
        ttk.Combobox(st, textvariable=self.lang_var, values=list(LANGUAGES),
                     state="readonly").grid(row=row("Language"), column=1, sticky="ew")

        self.words_var = tk.StringVar(value=self.cfg.get("stt_prompt", ""))
        ttk.Entry(st, textvariable=self.words_var).grid(
            row=row("Words you use often"), column=1, sticky="ew")

        self.hk_raw_var = tk.StringVar(value=self.cfg.get("hotkey_raw"))
        ttk.Entry(st, textvariable=self.hk_raw_var).grid(
            row=row("Hotkey: type what I said"), column=1, sticky="ew")
        self.hk_clean_var = tk.StringVar(value=self.cfg.get("hotkey_clean"))
        ttk.Entry(st, textvariable=self.hk_clean_var).grid(
            row=row("Hotkey: clean up"), column=1, sticky="ew")

        cprov = next((k for k, v in PROVIDERS.items() if v == self.cfg.get("cleanup_provider")),
                     "Groq (free)")
        self.clean_provider_var = tk.StringVar(value=cprov.replace(" (paid)", ""))
        cbox = ttk.Combobox(st, textvariable=self.clean_provider_var,
                            values=["Groq (free)", "OpenRouter"], state="readonly")
        cbox.grid(row=row("Cleanup provider"), column=1, sticky="ew")
        cbox.bind("<<ComboboxSelected>>", lambda e: self.clean_model_var.set(
            self.cfg.get("groq_cleanup_model") if self.clean_provider_var.get().startswith("Groq")
            else self.cfg.get("cleanup_model")))
        self.clean_model_var = tk.StringVar(value=self.cfg.get("groq_cleanup_model")
                                            if self.cfg.get("cleanup_provider") == "groq"
                                            else self.cfg.get("cleanup_model"))
        ttk.Entry(st, textvariable=self.clean_model_var).grid(
            row=row("Cleanup model"), column=1, sticky="ew")

        ttk.Label(st, text="Cleanup prompt  (${output} = your words)").grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(8, 2))
        r += 1
        self.prompt_box = tk.Text(st, height=7, wrap="word", font=("Segoe UI", 10))
        self.prompt_box.grid(row=r, column=0, columnspan=2, sticky="nsew")
        self.prompt_box.insert("1.0", self.cfg.get("cleanup_prompt", ""))
        st.rowconfigure(r, weight=1)
        r += 1

        b = ttk.Frame(st)
        b.grid(row=r, column=0, columnspan=2, sticky="ew", pady=10)
        ttk.Button(b, text="Save", command=self.save_settings).pack(side="left")
        ttk.Button(b, text="Compare speech models (10 sec)",
                   command=self.compare_models).pack(side="left", padx=10)

    def update_hint(self):
        self.hint_var.set(
            f"Hotkeys work in any app (VS Code, browser, chat):  "
            f"{self.cfg['hotkey_raw'].upper()} = type what I said,  "
            f"{self.cfg['hotkey_clean'].upper()} = clean up.  "
            f"Press once to start, again to stop. The text is typed where your cursor is.")

    def toggle_on_top(self):
        self.cfg["on_top"] = bool(self.top_var.get())
        self.root.attributes("-topmost", self.cfg["on_top"])
        save_config(self.cfg)

    def copy_result(self):
        pyperclip.copy(self.result.get("1.0", "end").strip())
        self.log("Copied to clipboard.")

    def log(self, msg):
        stamp = time.strftime("%H:%M:%S")
        self.logbox.insert("end", f"[{stamp}] {msg}\n")
        self.logbox.see("end")

    def set_status(self, text, color="black"):
        self.status_var.set(text)
        self.status_lbl.configure(foreground=color)

    def beep(self, freq, ms=90):
        if self.cfg.get("beep", True) and winsound:
            threading.Thread(target=lambda: winsound.Beep(freq, ms), daemon=True).start()

    # ----- settings -----

    # ----- provider helpers -----

    def models_for(self, provider):
        return GROQ_MODELS if provider == "groq" else STT_MODELS

    def current_model(self):
        if self.cfg.get("stt_provider") == "groq":
            return self.cfg.get("groq_model") or DEFAULTS["groq_model"]
        return self.cfg.get("stt_model") or DEFAULTS["stt_model"]

    def on_provider_change(self):
        provider = PROVIDERS.get(self.provider_var.get(), "groq")
        self.model_box.configure(values=self.models_for(provider))
        self.model_var.set(self.cfg.get("groq_model") if provider == "groq"
                           else self.cfg.get("stt_model"))

    def toggle_show_keys(self):
        show = "" if self.show_key.get() else "•"
        self.key_entry.configure(show=show)
        self.groq_entry.configure(show=show)

    def speech_key(self):
        if self.cfg.get("stt_provider") == "groq":
            return self.cfg.get("groq_api_key", "")
        return self.cfg.get("api_key", "")

    def save_settings(self):
        mic = dict(self.mic_choices).get(self.mic_var.get())
        provider = PROVIDERS.get(self.provider_var.get(), "groq")
        model = self.model_var.get().strip()
        if provider == "groq":
            self.cfg["groq_model"] = model if model in GROQ_MODELS else DEFAULTS["groq_model"]
        else:
            self.cfg["stt_model"] = model or DEFAULTS["stt_model"]
        cmodel = self.clean_model_var.get().strip()
        if self.clean_provider_var.get().startswith("Groq"):
            self.cfg["groq_cleanup_model"] = cmodel or DEFAULTS["groq_cleanup_model"]
        else:
            self.cfg["cleanup_model"] = cmodel or DEFAULTS["cleanup_model"]
        self.cfg.update({
            "api_key": self.key_var.get().strip(),
            "groq_api_key": self.groq_key_var.get().strip(),
            "stt_provider": provider,
            "input_device": mic,
            "language": LANGUAGES.get(self.lang_var.get(), ""),
            "stt_prompt": self.words_var.get().strip(),
            "hotkey_raw": self.hk_raw_var.get().strip().lower() or DEFAULTS["hotkey_raw"],
            "hotkey_clean": self.hk_clean_var.get().strip().lower() or DEFAULTS["hotkey_clean"],
            "cleanup_provider": "groq" if self.clean_provider_var.get().startswith("Groq")
                                else "openrouter",
            "cleanup_prompt": self.prompt_box.get("1.0", "end").strip(),
        })
        save_config(self.cfg)
        self.register_hotkeys()
        self.update_hint()
        self.log("Settings saved.")
        self.notebook.select(0)

    def save_key(self):
        self.cfg["api_key"] = self.key_var.get().strip()
        self.cfg["groq_api_key"] = self.groq_key_var.get().strip()
        save_config(self.cfg)
        if not self.speech_key():
            name = "Groq" if self.cfg.get("stt_provider") == "groq" else "OpenRouter"
            self.log(f"Saved, but the {name} key is empty. Speech needs it.")
            self.set_status(f"Add your {name} API key", "#b36b00")
            return
        self.log("Keys saved. Now click Record and speak.")
        self.set_status("Ready", "black")

    def register_hotkeys(self):
        for h in self.hotkey_handles:
            try:
                keyboard.remove_hotkey(h)
            except Exception:
                pass
        self.hotkey_handles = []
        for key, mode in ((self.cfg["hotkey_raw"], "raw"), (self.cfg["hotkey_clean"], "clean")):
            try:
                h = keyboard.add_hotkey(key, lambda m=mode: self.q.put(("hotkey", m)),
                                        suppress=True)
                self.hotkey_handles.append(h)
            except Exception as e:
                self.log(f"Could not set hotkey '{key}': {e}")

    # ----- recording -----

    def open_stream(self):
        device = self.cfg.get("input_device")

        def cb(indata, frames, t, status):
            self.frames.append(indata.copy())
            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
            self.level = min(1.0, rms / 3000.0)

        for rate in (self.cfg.get("sample_rate", 16000), None):
            try:
                if rate is None:
                    info = sd.query_devices(device, "input")
                    rate = int(info["default_samplerate"])
                stream = sd.InputStream(samplerate=rate, channels=1, dtype="int16",
                                        device=device, callback=cb)
                stream.start()
                self.rate = rate
                return stream
            except Exception as e:
                last = e
        raise last

    def on_record_button(self):
        self.toggle(self.mode_var.get(), "ui")

    def toggle(self, mode, target):
        if not self.recording:
            if self.busy:
                self.log("Still working on the last one, wait a second.")
                return
            if not self.speech_key():
                self.save_key()
                if not self.speech_key():
                    return
            self.frames = []
            try:
                self.stream = self.open_stream()
            except Exception as e:
                self.log(f"Could not open microphone: {e}")
                self.set_status("Microphone error", "red")
                return
            self.recording = True
            self.mode, self.target = mode, target
            self.beep(880)
            self.rec_btn.configure(text="■  Stop")
            where = "here" if target == "ui" else "at your cursor"
            label = "type what I said" if mode == "raw" else "clean up"
            self.set_status(f"● Recording...  ({label}, result {where})", "red")
        else:
            self.recording = False
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
            self.beep(500)
            self.rec_btn.configure(text="●  Record")
            self.level = 0.0
            if not self.frames:
                self.set_status("Nothing recorded", "red")
                return
            audio = np.concatenate(self.frames, axis=0)
            seconds = len(audio) / self.rate
            if seconds < 0.4:
                self.set_status("Too short, try again", "red")
                return
            peak = int(np.abs(audio).max())
            if peak < 400:
                self.log(f"No voice heard (mic level {peak}), nothing sent. Speak a bit "
                         "louder or check the microphone in Settings.")
                self.set_status("No voice heard, try again", "red")
                return
            self.busy = True
            self.set_status("Transcribing...", "#b36b00")
            threading.Thread(target=self.process,
                             args=(audio, self.rate, self.mode, self.target),
                             daemon=True).start()

    # ----- OpenRouter -----

    def headers(self):
        return {"Authorization": f"Bearer {self.cfg['api_key']}",
                "Content-Type": "application/json",
                "X-Title": "Bangla Dictate"}

    def transcribe(self, wav, model=None):
        if self.cfg.get("stt_provider") == "groq":
            return self.transcribe_groq(wav, model)
        return self.transcribe_openrouter(wav, model)

    def transcribe_groq(self, wav, model=None):
        data = {"model": model or self.cfg.get("groq_model") or DEFAULTS["groq_model"],
                "temperature": "0", "response_format": "json"}
        if self.cfg.get("language"):
            data["language"] = self.cfg["language"]
        if self.cfg.get("stt_prompt"):
            data["prompt"] = self.cfg["stt_prompt"]
        r = requests.post(GROQ_STT_URL,
                          headers={"Authorization": f"Bearer {self.cfg['groq_api_key']}"},
                          files={"file": ("audio.wav", wav, "audio/wav")},
                          data=data, timeout=90)
        if r.status_code != 200:
            raise RuntimeError(f"Groq transcription failed ({r.status_code}): {r.text[:300]}")
        return (r.json().get("text") or "").strip(), None

    def transcribe_openrouter(self, wav, model=None):
        payload = {
            "model": model or self.cfg["stt_model"],
            "input_audio": {"data": base64.b64encode(wav).decode("ascii"), "format": "wav"},
            "temperature": 0,
        }
        if self.cfg.get("language"):
            payload["language"] = self.cfg["language"]
        if self.cfg.get("stt_prompt"):
            payload["prompt"] = self.cfg["stt_prompt"]
        r = requests.post(STT_URL, headers=self.headers(), json=payload, timeout=90)
        if r.status_code != 200:
            raise RuntimeError(f"Transcription failed ({r.status_code}): {r.text[:300]}")
        data = r.json()
        return (data.get("text") or "").strip(), (data.get("usage") or {}).get("cost")

    def cleanup_key(self):
        if self.cfg.get("cleanup_provider", "groq") == "groq":
            return self.cfg.get("groq_api_key", "")
        return self.cfg.get("api_key", "")

    def cleanup(self, text):
        tpl = self.cfg.get("cleanup_prompt") or "${output}"
        prompt = tpl.replace("${output}", text) if "${output}" in tpl else f"{tpl}\n\n{text}"
        messages = [{"role": "user", "content": prompt}]
        if self.cfg.get("cleanup_provider", "groq") == "groq":
            payload = {"model": self.cfg.get("groq_cleanup_model") or DEFAULTS["groq_cleanup_model"],
                       "messages": messages, "temperature": 0.2, "reasoning_effort": "low"}
            hdr = {"Authorization": f"Bearer {self.cfg['groq_api_key']}",
                   "Content-Type": "application/json"}
            r = requests.post(GROQ_CHAT_URL, headers=hdr, json=payload, timeout=45)
            if r.status_code == 400 and "reasoning" in r.text:
                payload.pop("reasoning_effort", None)
                r = requests.post(GROQ_CHAT_URL, headers=hdr, json=payload, timeout=45)
        else:
            payload = {"model": self.cfg.get("cleanup_model", "openrouter/free"),
                       "messages": messages, "temperature": 0.2}
            r = requests.post(CHAT_URL, headers=self.headers(), json=payload, timeout=45)
        if r.status_code != 200:
            raise RuntimeError(f"Cleanup failed ({r.status_code}): {r.text[:300]}")
        content = r.json()["choices"][0]["message"].get("content") or ""
        return strip_thinking(content) or text

    def process(self, audio, rate, mode, target):
        put = self.q.put
        try:
            put(("log", f"Sending {len(audio) / rate:.1f}s of audio to "
                        f"{self.cfg.get('stt_provider')} / {self.current_model()}"))
            text, cost = self.transcribe(to_wav_bytes(audio, rate))
            put(("log", f"Heard: {text or '(nothing)'}"
                        + (f"   cost ${cost:.6f}" if cost is not None else "")))
            if not text:
                put(("status", ("Nothing recognised, try again", "red")))
                return
            if is_hallucination(text, len(audio) / rate):
                put(("log", f"Ignored \"{text}\": Whisper invents this when it hears "
                            "silence or noise."))
                put(("status", ("No clear speech, try again", "red")))
                return
            if mode == "clean":
                if not self.cleanup_key():
                    put(("log", "Cleanup skipped: no key for the cleanup provider. "
                                "Typing the raw text instead."))
                else:
                    put(("status", ("Cleaning up...", "#b36b00")))
                    try:
                        text = self.cleanup(text)
                        put(("log", f"Cleaned: {text}"))
                    except Exception as e:
                        put(("log", f"Cleanup failed, typing raw text instead. ({e})"))
            put(("result", text))
            if target == "paste":
                paste_text(text)
                put(("status", ("✓ Typed at your cursor", "green")))
            else:
                put(("status", ("✓ Done. Dictation works!", "green")))
        except requests.exceptions.ConnectionError:
            put(("log", "ERROR: no internet connection, or OpenRouter is unreachable."))
            put(("status", ("Network error", "red")))
        except Exception as e:
            put(("log", f"ERROR: {e}"))
            msg = str(e)
            if "(401)" in msg:
                put(("log", "That API key looks wrong. Check it at the top."))
            if "(402)" in msg:
                put(("log", "OpenRouter needs credit for speech. Switch Settings > "
                            "Speech provider to Groq (free)."))
            if "(429)" in msg:
                put(("log", "Free limit reached for now. Wait a minute and try again."))
            put(("status", ("Error, see log below", "red")))
        finally:
            put(("busy", False))

    # ----- tests -----

    def test_mic(self):
        if self.recording or self.busy:
            return
        self.busy = True
        self.set_status("Testing mic: say something for 3 seconds...", "red")

        def run():
            device = self.cfg.get("input_device")
            try:
                try:
                    rate = 16000
                    audio = sd.rec(3 * rate, samplerate=rate, channels=1, dtype="int16",
                                   device=device)
                    sd.wait()
                except Exception:
                    rate = int(sd.query_devices(device, "input")["default_samplerate"])
                    audio = sd.rec(3 * rate, samplerate=rate, channels=1, dtype="int16",
                                   device=device)
                    sd.wait()
                peak = int(np.abs(audio).max())
                self.q.put(("status", ("Playing it back...", "#b36b00")))
                sd.play(audio, rate)
                sd.wait()
                if peak < 300:
                    self.q.put(("log", f"Mic test: almost silent (peak {peak}). "
                                       "Pick another microphone in Settings."))
                    self.q.put(("status", ("Mic seems silent", "red")))
                else:
                    self.q.put(("log", f"Mic test OK (peak level {peak})."))
                    self.q.put(("status", ("✓ Mic works", "green")))
            except Exception as e:
                self.q.put(("log", f"Mic test failed: {e}"))
                self.q.put(("status", ("Microphone error", "red")))
            finally:
                self.q.put(("busy", False))

        threading.Thread(target=run, daemon=True).start()

    def compare_models(self):
        if self.recording or self.busy:
            return
        self.save_settings()
        if not self.speech_key():
            self.log("Add your speech API key at the top and click Save keys first.")
            return
        self.busy = True

        def run():
            put = self.q.put
            device = self.cfg.get("input_device")
            try:
                for n in (3, 2, 1):
                    put(("status", (f"Comparing models: start speaking in {n}...", "#b36b00")))
                    time.sleep(1)
                put(("status", ("● Speak now (10 seconds)", "red")))
                rate = 16000
                audio = sd.rec(10 * rate, samplerate=rate, channels=1, dtype="int16",
                               device=device)
                sd.wait()
                wav = to_wav_bytes(audio, rate)
                put(("status", ("Sending to models...", "#b36b00")))
                lines = []
                for m in self.models_for(self.cfg.get("stt_provider")):
                    t0 = time.time()
                    try:
                        text, cost = self.transcribe(wav, model=m)
                        c = f"${cost:.6f}" if cost is not None else ""
                        lines.append(f"[{m}]  {time.time() - t0:.1f}s {c}\n{text}\n")
                    except Exception as e:
                        lines.append(f"[{m}]  FAILED: {e}\n")
                    put(("result_replace", "\n".join(lines)))
                put(("log", "Compare done. Put the best model in Settings > Speech model."))
                put(("status", ("✓ Compare done, see Result", "green")))
            except Exception as e:
                put(("log", f"Compare failed: {e}"))
                put(("status", ("Error, see log", "red")))
            finally:
                put(("busy", False))

        threading.Thread(target=run, daemon=True).start()

    # ----- loop -----

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "hotkey":
                    self.toggle(val, "paste")
                elif kind == "log":
                    self.log(val)
                elif kind == "status":
                    self.set_status(*val)
                elif kind == "result":
                    self.result.delete("1.0", "end")
                    self.result.insert("1.0", val)
                elif kind == "result_replace":
                    self.notebook.select(0)
                    self.result.delete("1.0", "end")
                    self.result.insert("1.0", val)
                elif kind == "busy":
                    self.busy = val
        except queue.Empty:
            pass
        self.meter["value"] = int(self.level * 100) if self.recording else 0
        self.root.after(50, self.poll)

    def on_close(self):
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        if self.stream:
            try:
                self.stream.close()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
