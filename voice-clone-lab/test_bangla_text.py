"""Tests for bangla_text.py. Run: python -m unittest test_bangla_text -v"""

import unittest

from bangla_text import N, int_to_words, normalize, prepare, split_sentences, year_to_words


class Numbers(unittest.TestCase):
    def check(self, n, words):
        self.assertEqual(int_to_words(n), N(words))

    def test_small(self):
        self.check(0, "শূন্য")
        self.check(7, "সাত")
        self.check(19, "উনিশ")
        self.check(29, "ঊনত্রিশ")
        self.check(99, "নিরানব্বই")

    def test_hundreds_bangladeshi(self):
        self.check(100, "একশো")
        self.check(200, "দুইশো")
        self.check(250, "দুইশো পঞ্চাশ")

    def test_large(self):
        self.check(1250, "এক হাজার দুইশো পঞ্চাশ")
        self.check(100000, "এক লাখ")
        self.check(2500000, "পঁচিশ লাখ")
        self.check(10000000, "এক কোটি")
        self.check(12345678, "এক কোটি তেইশ লাখ পঁয়তাল্লিশ হাজার ছয়শো আটাত্তর")

    def test_years(self):
        self.assertEqual(year_to_words(1971), N("উনিশশো একাত্তর"))
        self.assertEqual(year_to_words(1900), N("উনিশশো"))
        self.assertEqual(year_to_words(2026), N("দুই হাজার ছাব্বিশ"))


class Normalize(unittest.TestCase):
    def check(self, src, out, **kw):
        self.assertEqual(normalize(src, **kw), N(out))

    def test_bangla_and_ascii_digits(self):
        self.check("৫টা আম", "পাঁচটা আম")
        self.check("5টা আম", "পাঁচটা আম")

    def test_thousands_separators(self):
        self.check("১,২৫০ জন", "এক হাজার দুইশো পঞ্চাশ জন")
        self.check("1,00,000", "এক লাখ")

    def test_money(self):
        self.check("১২৫০ টাকা", "এক হাজার দুইশো পঞ্চাশ টাকা")
        self.check("৳১,২৫০", "এক হাজার দুইশো পঞ্চাশ টাকা")
        self.check("৳ 99", "নিরানব্বই টাকা")
        self.check("500 tk", "পাঁচশো টাকা")
        self.check("৳১২.৫০", "বারো টাকা পঞ্চাশ পয়সা")
        self.check("$5", "পাঁচ ডলার")

    def test_percent_decimal(self):
        self.check("৫০% ছাড়", "পঞ্চাশ পার্সেন্ট ছাড়")
        self.check("২.৫ কেজি", "দুই দশমিক পাঁচ কেজি")

    def test_dates(self):
        self.check("২৬/১১/২০২৬", "ছাব্বিশে নভেম্বর দুই হাজার ছাব্বিশ")
        self.check("1-1-26", "পহেলা জানুয়ারি দুই হাজার ছাব্বিশ")
        self.check("২১শে ফেব্রুয়ারি", "একুশে ফেব্রুয়ারি")
        self.check("১ বৈশাখ", "পহেলা বৈশাখ")
        self.check("5 December", "পাঁচই ডিসেম্বর")
        self.check("১৯৭১ সালে", "উনিশশো একাত্তর সালে")

    def test_time(self):
        self.check("১০:৩০ এ", "দশটা ত্রিশ মিনিট এ")
        self.check("8:00", "আটটা")

    def test_ordinals(self):
        self.check("১ম পুরস্কার", "প্রথম পুরস্কার")
        self.check("২য় দিন", "দ্বিতীয় দিন")
        self.check("৪র্থ", "চতুর্থ")

    def test_phone(self):
        self.check("০১৭১২৩৪৫৬৭৮", "শূন্য এক সাত এক দুই তিন চার পাঁচ ছয় সাত আট")
        self.check("+৮৮০১৭১১", "প্লাস আট আট শূন্য এক সাত এক এক")
        self.check("১২৩৪৫৬৭৮ জন", "এক কোটি তেইশ লাখ পঁয়তাল্লিশ হাজার ছয়শো আটাত্তর জন")

    def test_english(self):
        self.check("AI দিয়ে TikTok ভিডিও", "এআই দিয়ে টিকটক ভিডিও")
        self.check("BRAC", "বিআরএসি")
        self.check("Pathao", "Pathao")  # unknown word left alone
        self.check("AI", "AI", english=False)
        self.check("চা & বিস্কুট", "চা এবং বিস্কুট")


class Sentences(unittest.TestCase):
    def test_split(self):
        self.assertEqual(
            split_sentences("কেমন আছো? আমি ভালো আছি। চলো শুরু করি!\nনতুন লাইন"),
            [N("কেমন আছো?"), N("আমি ভালো আছি।"), N("চলো শুরু করি!"), N("নতুন লাইন")],
        )

    def test_multiple_marks_and_dot(self):
        self.assertEqual(split_sentences("সত্যি?! হ্যাঁ. দাম 2.5"),
                         [N("সত্যি?!"), N("হ্যাঁ।"), N("দাম 2.5")])

    def test_drops_empty(self):
        self.assertEqual(split_sentences("।।  \n\n ? হাই"), [N("হাই")])

    def test_max_chars(self):
        long = "এক, দুই, তিন, চার, পাঁচ, ছয়, সাত, আট, নয়, দশ।"
        parts = split_sentences(long, max_chars=15)
        self.assertTrue(all(len(p) <= 15 for p in parts), parts)
        self.assertEqual("".join(parts).replace(",", "").replace(" ", ""),
                         N(long).replace(",", "").replace(" ", ""))

    def test_prepare(self):
        self.assertEqual(prepare("দাম ৳১২৫০। কিনবেন?"),
                         [N("দাম এক হাজার দুইশো পঞ্চাশ টাকা।"), N("কিনবেন?")])


if __name__ == "__main__":
    unittest.main()
