# Bangla Dictate

Speak, and your words get typed wherever your cursor is: VS Code, Claude, ChatGPT, a browser, anything. The speech is transcribed by OpenRouter.

## Start it

Double-click `start.bat`. The first time, it installs the libraries it needs, then the window opens.

## First time

1. Click **Get free key** next to the Groq box, sign up at Groq (free, no card), create a key, paste it in the **Groq API key** box and click **Save keys**. Your OpenRouter key goes in the second box; it's only used for the clean-up hotkey.
2. Click **Test mic**, say something, and listen to the playback. If it's silent, choose another microphone in the **Settings** tab and click Save.
3. Click **Record**, speak, then click **Stop**. The text appears in the Result box. If it does, dictation works.

Speech runs on Groq's free Whisper Large v3, which allows several hours of audio per day. The clean-up step also runs on Groq for free, using the same key. The OpenRouter key is optional. If you ever add OpenRouter credit, you can switch **Speech provider** in Settings to try its other models.

## Typing into other apps

Click where you want the text to go, then:

- **Ctrl + Alt + D**: press, speak, press again. Types exactly what you said.
- **Ctrl + Alt + E**: same, but an AI cleans it up into a clear English prompt first.

You'll hear a high beep when recording starts and a lower one when it stops. The window shows what happened. Tick **Keep window on top** to watch it while you work.

## Pick the best model for your voice

In **Settings**, click **Compare speech models**. It counts down, records 10 seconds of you talking, and runs that clip through six models. Pick the one that got your Bangla right, choose it under **Speech model**, and click Save.

## Settings

- **Language**: Auto detect, or force Bangla or English if it keeps guessing wrong.
- **Words you use often**: names and tech words, so the model spells them right.
- **Hotkeys**: change them if they clash with another app (e.g. `ctrl+shift+space`).
- **Cleanup model / prompt**: what Ctrl + Alt + E does. `${output}` is where your words go.

## If something goes wrong

Check the Log box at the bottom of the window.

- **401 error**: the API key is wrong.
- **402 error**: OpenRouter needs credit. Switch Speech provider back to Groq (free).
- **429 error**: you hit the free limit for now. Wait a minute.
- **Mic seems silent**: pick another microphone in Settings.
- **Hotkey text doesn't appear in an app run as administrator**: run `start.bat` as administrator too.
