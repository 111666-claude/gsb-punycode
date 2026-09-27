import random
import unittest

from puny.codec import BASE, PunyError, adapt, char_to_digit, decode_label, digit_to_char, encode_label


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


class AdaptTest(unittest.TestCase):
    def test_first_round_damps(self):
        self.assertEqual(adapt(700, 1, True), 1)

    def test_decays_with_delta(self):
        self.assertGreater(adapt(1, 10, False), adapt(100000, 10, False) - BASE * 10)
        self.assertNotEqual(adapt(1000, 5, False), 72)

    def test_matches_rfc_formula(self):
        delta = 1000
        points = 5
        d = delta // 2
        d += d // points
        k = 0
        while d > ((36 - 1) * 26) // 2:
            d //= 36 - 1
            k += 36
        self.assertEqual(adapt(delta, points, False), k + (36 - 1 + 1) * d // (d + 38))


class LabelTest(unittest.TestCase):
    def test_ascii_label_roundtrip_unchanged(self):
        self.assertEqual(decode_label(encode_label("abc")), "abc")

    def test_ascii_matches_stdlib(self):
        self.assertEqual(encode_label("abc"), "abc".encode("punycode").decode("ascii"))

    def test_empty_label(self):
        self.assertEqual(encode_label(""), "")
        self.assertEqual(decode_label(""), "")

    def test_basic_prefix_kept(self):
        self.assertTrue(encode_label("bcher").startswith("bcher"))

    def test_delimiter_between_basic_and_extended(self):
        self.assertEqual(encode_label("bücher"), "bcher-kva")

    def test_no_delimiter_without_basic(self):
        self.assertEqual(encode_label("日本語"), "wgv71a119e")
        self.assertNotIn("-", encode_label("日本語"))

    def test_decode_japanese(self):
        self.assertEqual(decode_label("wgv71a119e"), "日本語")

    def test_decode_muenchen(self):
        self.assertEqual(decode_label("mnchen-3ya"), "münchen")

    def test_decode_uppercase_digits(self):
        self.assertEqual(decode_label("WGv71A119E"), "日本語")

    def test_decode_is_deterministic(self):
        self.assertEqual(encode_label("bücher"), encode_label("bücher"))
        self.assertEqual(decode_label("bcher-kva"), decode_label("bcher-kva"))


class DecodeValidationTest(unittest.TestCase):
    def test_second_dash_rejected_with_position(self):
        with self.assertRaises(PunyError) as ctx:
            decode_label("a-b-c")
        self.assertEqual(ctx.exception.pos, 3)
        self.assertIn("4", str(ctx.exception))

    def test_leading_dash_rejected(self):
        with self.assertRaises(PunyError) as ctx:
            decode_label("-abc")
        self.assertEqual(ctx.exception.pos, 0)

    def test_trailing_dash_ok(self):
        self.assertEqual(decode_label("abc-"), "abc")

    def test_invalid_digit_with_position(self):
        with self.assertRaises(PunyError) as ctx:
            decode_label("bcher-kv!")
        self.assertEqual(ctx.exception.pos, 8)
        self.assertIn("9", str(ctx.exception))

    def test_truncated_extension_with_position(self):
        with self.assertRaises(PunyError) as ctx:
            decode_label("bcher-kva0")
        self.assertIsNotNone(ctx.exception.pos)

    def test_non_ascii_basic_rejected(self):
        with self.assertRaises(PunyError) as ctx:
            decode_label("bücher-kva")
        self.assertEqual(ctx.exception.pos, 1)


class StdlibComparisonTest(unittest.TestCase):
    def random_text(self, rng):
        kind = rng.randrange(5)
        if kind == 0:
            alphabet = "abcdefgXYZ019"
            size = rng.randrange(0, 30)
        elif kind == 1:
            alphabet = "日本語テスト中文汉字"
            size = rng.randrange(1, 30)
        elif kind == 2:
            alphabet = "ab日本c語😀🎉éü"
            size = rng.randrange(1, 40)
        elif kind == 3:
            alphabet = "😀🎉🚀💡"
            size = rng.randrange(1, 20)
        else:
            alphabet = "a1日😀"
            size = rng.randrange(200, 400)
        return "".join(rng.choice(alphabet) for _ in range(size))

    def test_1000_random_texts_match_stdlib(self):
        rng = random.Random(20260928)
        for _ in range(1000):
            text = self.random_text(rng)
            expected = text.encode("punycode").decode("ascii")
            self.assertEqual(encode_label(text), expected, text)
            self.assertEqual(decode_label(expected), text, text)
            self.assertEqual(decode_label(encode_label(text)), text, text)


class ScaleTest(unittest.TestCase):
    def test_one_megabyte_roundtrip(self):
        text = "abc日本語123😀" * (1024 * 1024 // 14)
        encoded = encode_label(text)
        self.assertEqual(encoded, text.encode("punycode").decode("ascii"))
        self.assertEqual(decode_label(encoded), text)


if __name__ == "__main__":
    unittest.main()
