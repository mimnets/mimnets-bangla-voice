# Voice clone results (Phase 1)

Same three test scripts (`test_scripts/`) for every engine. Listen with headphones.
Scores 1 (bad) to 5 (great). "Accent" = how Bangladeshi it sounds (5 = clearly Bangladeshi, 1 = clearly Kolkata).

## Scores

| Date | Engine | Reference clip | Settings | Sounds like me | Accent (BD) | Natural | Wrong words | Speed (x real time) | Cost |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-26 | BanglaBox (Colab T4) | `reference.wav`, first recording, built-in greeting | default (cfg 0.5, exaggeration 0.5, temp 0.5), seed 0 | Yes | Slightly Kolkata | | | | Free (Colab) |
| 2026-11-26 | BanglaBox accent test, A | same | cfg 0.5 (default) | | 3 | odd timing and stops | | | Free |
| 2026-11-26 | **BanglaBox accent test, B** | same | **cfg 0.8** | | **5** | **natural timing and pauses** | | | Free |
| 2026-11-26 | BanglaBox accent test, C | same | cfg 1.0 | | 2.5 | odd timing and stops | | | Free |
| 2026-11-26 | BanglaBox accent test, D | same | cfg 0.3 | | 2.5 | odd timing and stops | | | Free |
| 2026-11-26 | BanglaBox accent test, E | same | cfg 0.8, exaggeration 0.35 | | 2 | odd timing and stops | | | Free |
| 2026-11-26 | **BanglaBox, 3 test scripts** | same | **cfg 0.8**, seed 0 | Yes | Good | Good | none reported | not recorded | Free (Colab) |
| | Sarvam | not tested: BanglaBox was good enough | | | | | | | |
| | IndicF5 | not tested: BanglaBox was good enough | | | | | | | |

## Notes

- 2026-11-26, BanglaBox first run: the owner says it **sounds like me, but with a bit of a Kolkata accent**. The voice (timbre) transfers well; the accent and intonation lean West Bengal. Likely causes:
  1. The model's 520 h Bangla training data probably includes a lot of West Bengal (Indian) speech, so its default way of speaking leans that way.
  2. A 10 to 15 s clip mostly transfers *voice colour*; accent and intonation come more from the model than from the clip.
  3. Generation settings: `cfg_weight` controls how strongly the output follows the reference speaker's style.
- 2026-11-26, accent test round 1 (step 11, one Bangladeshi-flavoured sentence, seed 0): **B (cfg_weight 0.8) won with 5/5** and was the only one with natural timing and pauses. Raising cfg_weight from 0.5 to 0.8 makes the output copy more of the owner's own speaking style, which fixed most of the Kolkata lean. Going further (1.0) or lower (0.3) made it worse, and so did calming it down (exaggeration 0.35).
- The notebook now uses cfg_weight 0.8 by default (step 6, `MY_SETTINGS`). Step 11 round 2 tests 0.7, 0.9, more energy and lower temperature around it.
- 2026-11-26, three full test scripts with cfg 0.8: owner says **all scripts sound good**.

## Recommendation (Phase 1 result, 2026-11-26)

**Use BanglaBox with `cfg_weight` 0.8** for the voice clone feature. Keep BanglaBox's other defaults (temperature 0.5, exaggeration 0.5, repetition_penalty 1.5, min_p 0.05).

Why:
- It sounds like the owner, with a Bangladeshi accent and natural timing once cfg_weight is 0.8.
- The model is free and MIT-licensed (per the model card), with no per-character cost.
- Our `bangla_text.py` normaliser (Bangladeshi number words, dates, money, English brand names) plus sentence-by-sentence synthesis works well with it.

Not tested, and not needed for now: Sarvam (paid, trained mainly on Indian speech) and IndicF5 (also Indian-trained). Keep them as fallbacks if BanglaBox ever stops working.

Things to carry into Phase 2:
- **It needs an NVIDIA GPU.** The owner's laptop has Intel UHD Graphics only (checked 2026-11-26), so running it locally would be very slow. Phase 2 must choose where it runs: Colab by hand (free, manual), or a pay-per-use cloud GPU endpoint the app calls.
- Upstream Chatterbox is retired (no updates). BanglaBox pins old library versions (torch 2.6, transformers 4.46). A server image should pin them exactly, the way the notebook does.
- Every output carries Resemble AI's inaudible Perth watermark.
- Reference clip: 10 to 15 s, quiet room, natural Bangladeshi conversational tone (`record_reference.py`).
- Weights licence is MIT per the model card, but the authors are anonymous. Re-check before any commercial use.
- Speed on a T4 wasn't recorded. Measure it in Phase 2, because it sets the cloud-GPU cost.

