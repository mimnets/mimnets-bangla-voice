# Voice clone results (Phase 1)

Same three test scripts (`test_scripts/`) for every engine. Listen with headphones.
Scores 1 (bad) to 5 (great). "Accent" = how Bangladeshi it sounds (5 = clearly Bangladeshi, 1 = clearly Kolkata).

## Scores

| Date | Engine | Reference clip | Settings | Sounds like me | Accent (BD) | Natural | Wrong words | Speed (x real time) | Cost |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-26 | BanglaBox (Colab T4) | `reference.wav`, first recording, built-in greeting | default (cfg 0.5, exaggeration 0.5, temp 0.5), seed 0 | Yes | Slightly Kolkata | | | | Free (Colab) |
| | BanglaBox accent test (step 11) | | | | | | | | |
| | Sarvam (skipped for now) | | | | | | | | |
| | IndicF5 (optional) | | | | | | | | |

## Notes

- 2026-11-26, BanglaBox first run: the owner says it **sounds like me, but with a bit of a Kolkata accent**. The voice (timbre) transfers well; the accent and intonation lean West Bengal. Likely causes:
  1. The model's 520 h Bangla training data probably includes a lot of West Bengal (Indian) speech, so its default way of speaking leans that way.
  2. A 10 to 15 s clip mostly transfers *voice colour*; accent and intonation come more from the model than from the clip.
  3. Generation settings: `cfg_weight` controls how strongly the output follows the reference speaker's style.
- Next experiment: notebook step 11 compares `cfg_weight` and `exaggeration` settings on Bangladeshi-flavoured sentences, plus a reference clip read in a strongly Bangladeshi, conversational style.

## Recommendation

_To be filled in when testing is done._
