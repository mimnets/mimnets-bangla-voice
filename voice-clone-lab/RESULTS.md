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
| | Sarvam (skipped for now) | | | | | | | | |
| | IndicF5 (optional) | | | | | | | | |

## Notes

- 2026-11-26, BanglaBox first run: the owner says it **sounds like me, but with a bit of a Kolkata accent**. The voice (timbre) transfers well; the accent and intonation lean West Bengal. Likely causes:
  1. The model's 520 h Bangla training data probably includes a lot of West Bengal (Indian) speech, so its default way of speaking leans that way.
  2. A 10 to 15 s clip mostly transfers *voice colour*; accent and intonation come more from the model than from the clip.
  3. Generation settings: `cfg_weight` controls how strongly the output follows the reference speaker's style.
- 2026-11-26, accent test round 1 (step 11, one Bangladeshi-flavoured sentence, seed 0): **B (cfg_weight 0.8) won with 5/5** and was the only one with natural timing and pauses. Raising cfg_weight from 0.5 to 0.8 makes the output copy more of the owner's own speaking style, which fixed most of the Kolkata lean. Going further (1.0) or lower (0.3) made it worse, and so did calming it down (exaggeration 0.35).
- The notebook now uses cfg_weight 0.8 by default (step 6, `MY_SETTINGS`). Step 11 round 2 tests 0.7, 0.9, more energy and lower temperature around it.
- Still to check: the three full test scripts with cfg 0.8 (scores per script, wrong words, speed).

## Recommendation

_To be filled in when testing is done._
