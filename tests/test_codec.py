import unittest

from puny.codec import PunyError, char_to_digit, decode_label, digit_to_char, encode_label


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


class LabelTest(unittest.TestCase):
    def test_ascii_label_is_unchanged(self):
        self.assertEqual(encode_label("abc"), "abc")

    def test_ascii_roundtrip(self):
        self.assertEqual(decode_label("abc-"), "abc")

    def test_empty_label(self):
        self.assertEqual(encode_label(""), "")
        self.assertEqual(decode_label(""), "")

    def test_basic_prefix_kept(self):
        self.assertTrue(encode_label("bcher").startswith("bcher"))
