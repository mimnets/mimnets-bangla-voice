"""Bangla text normaliser and sentence splitter for TTS.

TTS models read words better than digits and symbols, so before synthesis we turn
    ৳১,২৫০       -> এক হাজার দুইশো পঞ্চাশ টাকা
    ২৬/১১/২০২৬   -> ছাব্বিশে নভেম্বর দুই হাজার ছাব্বিশ
    ৫০% ছাড়     -> পঞ্চাশ পার্সেন্ট ছাড়
    AI, TikTok   -> এআই, টিকটক
Spellings follow Bangladeshi usage (দুইশো, পহেলা).

Try it:
    python bangla_text.py "আজ ২৬/১১/২০২৬, দাম মাত্র ৳১২৫০! AI দিয়ে বানানো।"
    python bangla_text.py --file test_scripts/script1.txt
Tests:
    python -m unittest test_bangla_text -v
"""

import argparse
import re
import sys
import unicodedata


def N(s):
    """NFC-normalise (Bangla য় can be stored two ways; this makes them match)."""
    return unicodedata.normalize("NFC", s)


# ---------------------------------------------------------------- numbers

_UNITS = N(
    "শূন্য এক দুই তিন চার পাঁচ ছয় সাত আট নয় "
    "দশ এগারো বারো তেরো চৌদ্দ পনেরো ষোলো সতেরো আঠারো উনিশ "
    "বিশ একুশ বাইশ তেইশ চব্বিশ পঁচিশ ছাব্বিশ সাতাশ আটাশ ঊনত্রিশ "
    "ত্রিশ একত্রিশ বত্রিশ তেত্রিশ চৌত্রিশ পঁয়ত্রিশ ছত্রিশ সাঁইত্রিশ আটত্রিশ ঊনচল্লিশ "
    "চল্লিশ একচল্লিশ বিয়াল্লিশ তেতাল্লিশ চুয়াল্লিশ পঁয়তাল্লিশ ছেচল্লিশ সাতচল্লিশ আটচল্লিশ ঊনপঞ্চাশ "
    "পঞ্চাশ একান্ন বাহান্ন তিপ্পান্ন চুয়ান্ন পঞ্চান্ন ছাপ্পান্ন সাতান্ন আটান্ন ঊনষাট "
    "ষাট একষট্টি বাষট্টি তেষট্টি চৌষট্টি পঁয়ষট্টি ছেষট্টি সাতষট্টি আটষট্টি ঊনসত্তর "
    "সত্তর একাত্তর বাহাত্তর তিয়াত্তর চুয়াত্তর পঁচাত্তর ছিয়াত্তর সাতাত্তর আটাত্তর ঊনআশি "
    "আশি একাশি বিরাশি তিরাশি চুরাশি পঁচাশি ছিয়াশি সাতাশি আটাশি ঊননব্বই "
    "নব্বই একানব্বই বিরানব্বই তিরানব্বই চুরানব্বই পঁচানব্বই ছিয়ানব্বই সাতানব্বই আটানব্বই নিরানব্বই"
).split()
assert len(_UNITS) == 100

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def int_to_words(n):
    """Integer to Bangla words, Indian grouping (হাজার, লাখ, কোটি)."""
    if n < 0:
        return N("মাইনাস ") + int_to_words(-n)
    if n < 100:
        return _UNITS[n]
    parts = []
    for size, name in ((10**7, "কোটি"), (10**5, "লাখ"), (1000, "হাজার")):
        if n >= size:
            parts.append(f"{int_to_words(n // size)} {name}")
            n %= size
    if n >= 100:
        parts.append(_UNITS[n // 100] + "শো")
        n %= 100
    if n:
        parts.append(_UNITS[n])
    return N(" ".join(parts))


def digits_to_words(s):
    """Read a digit string one digit at a time (phone numbers, decimals)."""
    return N(" ".join(_UNITS[int(d)] for d in s))


def number_to_words(s):
    """'1250' -> words, '12.5' -> বারো দশমিক পাঁচ, '007' -> digit by digit."""
    if "." in s:
        whole, frac = s.split(".", 1)
        return N(f"{number_to_words(whole or '0')} দশমিক {digits_to_words(frac)}")
    if len(s) > 1 and s.startswith("0"):
        return digits_to_words(s)
    return int_to_words(int(s))


def year_to_words(y):
    """1971 -> উনিশশো একাত্তর, 2026 -> দুই হাজার ছাব্বিশ."""
    if 1100 <= y <= 1999:
        head = _UNITS[y // 100] + "শো"
        return N(head if y % 100 == 0 else f"{head} {_UNITS[y % 100]}")
    return int_to_words(y)


_SPECIAL_DAYS = {1: "পহেলা", 2: "দোসরা", 3: "তেসরা", 4: "চৌঠা"}


def day_to_words(d):
    """Day of month as spoken: পহেলা, দোসরা, পাঁচই, ছাব্বিশে."""
    if d in _SPECIAL_DAYS:
        return N(_SPECIAL_DAYS[d])
    return N(_UNITS[d] + ("ই" if d <= 18 else "ে"))


_ORDINALS = {1: "প্রথম", 2: "দ্বিতীয়", 3: "তৃতীয়", 4: "চতুর্থ", 5: "পঞ্চম",
             6: "ষষ্ঠ", 7: "সপ্তম", 8: "অষ্টম", 9: "নবম", 10: "দশম"}

# ---------------------------------------------------------------- dates

_MONTHS = N("জানুয়ারি ফেব্রুয়ারি মার্চ এপ্রিল মে জুন জুলাই আগস্ট সেপ্টেম্বর অক্টোবর নভেম্বর ডিসেম্বর").split()
_EN_MONTHS = ["january", "february", "march", "april", "may", "june", "july",
              "august", "september", "october", "november", "december"]
_BN_CAL_MONTHS = N("বৈশাখ জ্যৈষ্ঠ আষাঢ় শ্রাবণ ভাদ্র আশ্বিন কার্তিক অগ্রহায়ণ পৌষ মাঘ ফাল্গুন চৈত্র").split()
_MONTH_NAME_RE = "|".join(sorted(_MONTHS + _BN_CAL_MONTHS + _EN_MONTHS, key=len, reverse=True))

# ---------------------------------------------------------------- English words

ENGLISH_WORDS = {
    "ai": "এআই", "tiktok": "টিকটক", "youtube": "ইউটিউব", "facebook": "ফেসবুক",
    "instagram": "ইনস্টাগ্রাম", "whatsapp": "হোয়াটসঅ্যাপ", "google": "গুগল",
    "chatgpt": "চ্যাটজিপিটি", "iphone": "আইফোন", "android": "অ্যান্ড্রয়েড",
    "samsung": "স্যামসাং", "bkash": "বিকাশ", "nagad": "নগদ", "daraz": "দারাজ",
    "app": "অ্যাপ", "apps": "অ্যাপস", "online": "অনলাইন", "offline": "অফলাইন",
    "video": "ভিডিও", "link": "লিংক", "like": "লাইক", "share": "শেয়ার",
    "comment": "কমেন্ট", "follow": "ফলো", "subscribe": "সাবস্ক্রাইব", "ok": "ওকে",
    "vs": "ভার্সেস", "kg": "কেজি", "km": "কিলোমিটার", "cm": "সেন্টিমিটার",
    "mb": "এমবি", "gb": "জিবি", "tb": "টিবি",
}
_LETTERS = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    N("এ বি সি ডি ই এফ জি এইচ আই জে কে এল এম এন ও পি কিউ আর এস টি ইউ ভি ডাবলিউ এক্স ওয়াই জেড").split()))


def _english_word(m):
    w = m.group(0)
    if w.lower() in ENGLISH_WORDS:
        return N(ENGLISH_WORDS[w.lower()])
    if w.isupper() and 2 <= len(w) <= 6 and w.isalpha():  # acronyms: BRAC -> spelled out
        return "".join(_LETTERS[c] for c in w)
    return w  # unknown English word: leave it for the TTS engine


# ---------------------------------------------------------------- pipeline

_NUM = r"\d+(?:\.\d+)?"


def _money(amount, unit, sub_unit):
    if "." in amount:
        whole, frac = amount.split(".", 1)
        if len(frac) == 2 and sub_unit:
            words = f"{int_to_words(int(whole))} {unit}"
            return words if int(frac) == 0 else f"{words} {int_to_words(int(frac))} {sub_unit}"
    return f"{number_to_words(amount)} {unit}"


def normalize(text, english=True):
    """Turn digits, symbols, dates and (optionally) English words into speakable Bangla."""
    t = N(text).translate(_BN_DIGITS)
    t = re.sub(r"(?<=\d),(?=\d)", "", t)  # 1,250 / 1,00,000 -> plain digits

    # dates: 26/11/2026, 26-11-26
    def date(m):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if not (1 <= d <= 31 and 1 <= mo <= 12):
            return m.group(0)
        year = int(y) + 2000 if len(y) == 2 else int(y)
        return f"{day_to_words(d)} {_MONTHS[mo - 1]} {year_to_words(year)}"
    t = re.sub(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4}|\d{2})\b", date, t)

    # day + month name: ২৬ নভেম্বর, ২৬শে নভেম্বর, 1 বৈশাখ
    def day_month(m):
        d = int(m.group(1))
        if not 1 <= d <= 31:
            return m.group(0)
        month = m.group(2)
        if month.lower() in _EN_MONTHS:
            month = _MONTHS[_EN_MONTHS.index(month.lower())]
        return f"{day_to_words(d)} {month}"
    t = re.sub(N(r"(\d{1,2})\s*(?:শে|ই|লা|রা|ঠা|এ)?\s+(" + _MONTH_NAME_RE + r")"),
               day_month, t, flags=re.IGNORECASE)

    # years: ১৯৭১ সালে
    t = re.sub(N(r"(\d{4})(\s*সাল)"), lambda m: year_to_words(int(m.group(1))) + m.group(2), t)

    # time: 10:30
    t = re.sub(r"\b(\d{1,2}):(\d{2})\b",
               lambda m: N(f"{_UNITS[int(m.group(1))]}টা")
               + ("" if int(m.group(2)) == 0 else N(f" {int_to_words(int(m.group(2)))} মিনিট")), t)

    # money
    t = re.sub(N(r"৳\s*(" + _NUM + ")"), lambda m: _money(m.group(1), "টাকা", "পয়সা"), t)
    t = re.sub(N(r"(" + _NUM + r")\s*(?:টাকা|tk\b\.?|taka\b|bdt\b)"),
               lambda m: _money(m.group(1), "টাকা", "পয়সা"), t, flags=re.IGNORECASE)
    t = re.sub(r"\$\s*(" + _NUM + ")", lambda m: _money(m.group(1), "ডলার", "সেন্ট"), t)

    # percent
    t = re.sub(r"(" + _NUM + r")\s*%", lambda m: number_to_words(m.group(1)) + " পার্সেন্ট", t)

    # ordinals: ১ম, ২য়, ৪র্থ, ৬ষ্ঠ
    t = re.sub(N(r"(\d+)(?:ম|য়|র্থ|ষ্ঠ)(?![ঀ-৿])"),
               lambda m: N(_ORDINALS.get(int(m.group(1)), m.group(0))), t)

    # phone numbers: 01712345678, +8801712345678 -> digit by digit
    t = re.sub(r"\+?\d{7,}", lambda m: ("প্লাস " if m.group(0).startswith("+") else "")
               + digits_to_words(m.group(0).lstrip("+")) if m.group(0).startswith(("0", "+")) else m.group(0), t)

    # any number left
    t = re.sub(_NUM, lambda m: number_to_words(m.group(0)), t)

    t = t.replace("&", " এবং ")
    if english:
        t = re.sub(r"[A-Za-z][A-Za-z']*", _english_word, t)

    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" +([,।?!])", r"\1", t)
    return N(t.strip())


# ---------------------------------------------------------------- sentences

def split_sentences(text, max_chars=None):
    """Split at । ? ! ॥ newlines (and '.' after a non-digit). Keeps the end mark.

    If max_chars is set, sentences longer than that are split again at commas,
    then at spaces, so each piece fits an API's per-request limit.
    """
    t = re.sub(r"(?<=\D)\.(?=\s|$)", "।", N(text))
    pieces = [p.strip() for p in re.findall(r"[^।?!॥\n]+[।?!॥]*", t)]
    pieces = [p for p in pieces if re.search(r"\w", p)]
    if not max_chars:
        return pieces
    out = []
    for p in pieces:
        out.extend(_chunk(p, max_chars))
    return out


def _chunk(text, limit):
    """Split one long sentence into pieces of at most limit chars."""
    if len(text) <= limit:
        return [text]
    sep = next((x for x in (", ", "; ", " ") if x in text), None)
    if sep is None:  # one giant word: hard cut
        return [text[i:i + limit] for i in range(0, len(text), limit)]
    out, cur = [], ""
    for part in text.split(sep):
        cand = f"{cur}{sep}{part}" if cur else part
        if len(cand) <= limit or not cur:
            cur = cand
        else:
            out.append(cur + sep.rstrip())
            cur = part
    out.append(cur)
    return [y for x in out for y in _chunk(x.strip(), limit)]


def prepare(text, max_chars=None, english=True):
    """Normalise then split: what the clone scripts call."""
    return split_sentences(normalize(text, english=english), max_chars=max_chars)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Normalise Bangla text for TTS and show the sentences.")
    ap.add_argument("text", nargs="?", help="text to normalise")
    ap.add_argument("--file", help="read text from a UTF-8 file instead")
    ap.add_argument("--max-chars", type=int, default=None)
    ap.add_argument("--keep-english", action="store_true", help="don't convert English words")
    a = ap.parse_args()
    src = open(a.file, encoding="utf-8").read() if a.file else a.text
    if not src:
        ap.error("give some text or --file")
    sys.stdout.reconfigure(encoding="utf-8")
    for i, s in enumerate(prepare(src, a.max_chars, english=not a.keep_english), 1):
        print(f"{i:2}. {s}")
