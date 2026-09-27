import random
import unittest

from puny.codec import PunyError, adapt, char_to_digit, decode_label, digit_to_char, encode_label


class DigitTest(unittest.TestCase):
    def test_letter_digits(self):
        self.assertEqual(digit_to_char(0), "a")
        self.assertEqual(digit_to_char(25), "z")

    def test_number_digits(self):
        self.assertEqual(digit_to_char(26), "0")
        self.assertEqual(char_to_digit("0"), 26)

    def test_roundtrip(self):
        for value in range(36):
            self.assertEqual(char_to_digit(digit_to_char(value)), value)

    def test_rejects_bad_digit(self):
        with self.assertRaises(PunyError):
            char_to_digit("!")

    def test_uppercase_digits(self):
        self.assertEqual(char_to_digit("A"), 0)
        self.assertEqual(char_to_digit("Z"), 25)
        for value in range(26):
            self.assertEqual(char_to_digit(digit_to_char(value).upper()), value)


class DelimiterTest(unittest.TestCase):
    def test_basic_points_followed_by_dash(self):
        self.assertEqual(encode_label("bücher"), "bcher-kva")
        self.assertEqual(encode_label("münchen"), "mnchen-3ya")

    def test_no_dash_without_basic_points(self):
        self.assertEqual(encode_label("日本語"), "wgv71a119e")
        self.assertNotIn("-", encode_label("日本語"))

    def test_ascii_label_gets_trailing_dash(self):
        self.assertEqual(encode_label("abc"), "abc-")
        self.assertEqual(decode_label("abc-"), "abc")

    def test_decode_examples(self):
        self.assertEqual(decode_label("bcher-kva"), "bücher")
        self.assertEqual(decode_label("wgv71a119e"), "日本語")
        self.assertEqual(decode_label("mnchen-3ya"), "münchen")


class AdaptTest(unittest.TestCase):
    def test_adapt_not_constant(self):
        values = {adapt(delta, 10, False) for delta in (1, 100, 10000, 1000000)}
        self.assertGreater(len(values), 1)

    def test_adapt_decays_with_delta(self):
        self.assertEqual(adapt(0, 1, True), 0)
        self.assertEqual(adapt(3, 1, False), 1)
        self.assertEqual(adapt(1000000, 10, False), 105)

    def test_first_time_uses_damp(self):
        self.assertNotEqual(adapt(1400, 10, True), adapt(1400, 10, False))

    def test_long_label_roundtrip_needs_real_bias(self):
        text = "日本語テストです" * 30
        self.assertEqual(decode_label(encode_label(text)), text)


class DecodeValidationTest(unittest.TestCase):
    def test_illegal_digit_reports_position(self):
        with self.assertRaises(PunyError) as ctx:
            decode_label("mnchen-3y!")
        self.assertEqual(ctx.exception.position, 9)
        self.assertIn("10", str(ctx.exception))

    def test_trailing_junk_reports_offset(self):
        with self.assertRaises(PunyError) as ctx:
            decode_label("wgv71a119e?")
        self.assertEqual(ctx.exception.position, 10)

    def test_leading_dash_rejected(self):
        with self.assertRaises(PunyError) as ctx:
            decode_label("-abc")
        self.assertEqual(ctx.exception.position, 0)

    def test_truncated_extension_rejected(self):
        with self.assertRaises(PunyError) as ctx:
            decode_label("abc-9")
        self.assertIsNotNone(ctx.exception.position)

    def test_uppercase_label_decodes(self):
        self.assertEqual(decode_label("WGV71A119E"), "日本語")
        self.assertEqual(decode_label("BCHER-KVA"), "BüCHER")


class InvariantTest(unittest.TestCase):
    def test_ascii_label_roundtrip_is_unchanged(self):
        for label in ("abc", "hello-world", "a", "x" * 100):
            self.assertEqual(decode_label(encode_label(label)), label)

    def test_empty_label(self):
        self.assertEqual(encode_label(""), "")
        self.assertEqual(decode_label(""), "")

    def test_deterministic(self):
        text = "bücher 日本語 😀"
        self.assertEqual(encode_label(text), encode_label(text))
        label = encode_label(text)
        self.assertEqual(decode_label(label), decode_label(label))

    def test_roundtrip_samples(self):
        samples = ["bücher", "日本語", "münchen", "☃", "hello世界", "😀🎉", "αβγ", "a-b-c"]
        for text in samples:
            self.assertEqual(decode_label(encode_label(text)), text)


class StdlibComparisonTest(unittest.TestCase):
    def test_matches_stdlib_on_random_texts(self):
        rng = random.Random(20260928)
        pools = [
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            "日本語テストあいうえお漢字",
            "üöäéèêñç",
            "😀😁😂🤣😊🎉🚀🌟",
            "αβγδεζηθικλμν",
            "ab",
        ]
        for _ in range(1000):
            length = rng.randint(0, 40)
            text = "".join(rng.choice(rng.choice(pools)) for _ in range(length))
            expected = text.encode("punycode").decode("ascii")
            self.assertEqual(encode_label(text), expected)
            self.assertEqual(decode_label(expected), text)

    def test_matches_stdlib_on_long_text(self):
        rng = random.Random(7)
        pool = "abc日本語😀🎉üöäαβγ漢字"
        text = "".join(rng.choice(pool) for _ in range(20000))
        expected = text.encode("punycode").decode("ascii")
        self.assertEqual(encode_label(text), expected)
        self.assertEqual(decode_label(expected), text)


class ScaleTest(unittest.TestCase):
    def test_one_megabyte_single_pass(self):
        rng = random.Random(11)
        pool = "abcdefghijklmnopqrstuvwxyz日本語テスト漢字😀🎉🚀üöäéαβγ"
        text = "".join(rng.choice(pool) for _ in range(1_000_000))
        label = encode_label(text)
        self.assertEqual(label, text.encode("punycode").decode("ascii"))
        self.assertEqual(decode_label(label), text)


if __name__ == "__main__":
    unittest.main()
