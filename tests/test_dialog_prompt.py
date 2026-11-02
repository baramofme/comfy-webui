"""Unit tests for the `#` dialogue-prefix port (module/video_gen/dialog_prompt.py).

Run: python -m unittest tests.test_dialog_prompt   (from the repo root)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module.video_gen.dialog_prompt import (  # noqa: E402
    apply_dialog_prefixes,
    has_dialogue_lines,
    dialogue_line_content,
)


class TestParsing(unittest.TestCase):
    def test_plain_line_is_not_dialogue(self):
        self.assertIsNone(dialogue_line_content("a cat runs"))

    def test_hash_midline_is_not_dialogue(self):
        self.assertIsNone(dialogue_line_content("a cat #orange fur"))
        self.assertIsNone(dialogue_line_content("color #ff0000 background"))

    def test_double_hash_is_not_dialogue(self):
        self.assertIsNone(dialogue_line_content("## heading style"))

    def test_leading_whitespace_still_triggers(self):
        self.assertEqual(dialogue_line_content("   # hello there"), "hello there")

    def test_bare_hash_marks_empty(self):
        self.assertEqual(dialogue_line_content("#"), "")

    def test_hash_without_space_still_triggers(self):
        self.assertEqual(dialogue_line_content("#hello"), "hello")


class TestZeroRegression(unittest.TestCase):
    def test_no_dialogue_returns_same_object(self):
        p = "a cat runs\r\n#ff0000 wall\r\n"
        out = apply_dialog_prefixes(p, "h3")
        self.assertIs(out, p)          # exact same object, byte-identical
        self.assertEqual(out, p)

    def test_ltx_identity_same_object(self):
        p = "a cat runs\n"
        self.assertIs(apply_dialog_prefixes(p, "ltx"), p)

    def test_none_input_passthrough(self):
        self.assertIsNone(apply_dialog_prefixes(None, "h3"))

    def test_has_dialogue_detects(self):
        self.assertTrue(has_dialogue_lines("visual\n# speak up\n"))
        self.assertFalse(has_dialogue_lines("visual #tag\n## md\n"))


class TestH3Format(unittest.TestCase):
    def test_single_segment(self):
        out = apply_dialog_prefixes("# I am ready.", "h3")
        self.assertEqual(out, "<d>I am ready.</d>")

    def test_inline_position_and_visual_untouched(self):
        src = "A woman at a window.\n# I get off at the next station.\nShe folds a letter."
        out = apply_dialog_prefixes(src, "h3")
        self.assertEqual(
            out,
            "A woman at a window.\n<d>I get off at the next station.</d>\nShe folds a letter.",
        )

    def test_multiple_segments_keep_order(self):
        src = "# first line\nvisual text\n# second line"
        out = apply_dialog_prefixes(src, "h3")
        self.assertEqual(out, "<d>first line</d>\nvisual text\n<d>second line</d>")

    def test_bare_hash_line_dropped(self):
        out = apply_dialog_prefixes("visual\n#\nmore visual", "h3")
        self.assertEqual(out, "visual\nmore visual")

    def test_escape_renders_literal_hash(self):
        src = "# real dialogue\n\\# not dialogue"
        out = apply_dialog_prefixes(src, "h3")
        self.assertEqual(out, "<d>real dialogue</d>\n# not dialogue")

    def test_hashtag_midline_survives(self):
        src = "# hello\na cat #fluffy cat"
        out = apply_dialog_prefixes(src, "h3")
        self.assertEqual(out, "<d>hello</d>\na cat #fluffy cat")


class TestLTXFormat(unittest.TestCase):
    def test_quoted_cue(self):
        out = apply_dialog_prefixes("# I will never go back", "ltx")
        self.assertEqual(out, 'The character says, "I will never go back."')

    def test_punctuation_kept_inside_quotes(self):
        out = apply_dialog_prefixes("# Wait for us!", "ltx")
        self.assertEqual(out, 'The character says, "Wait for us!"')

    def test_already_quoted_not_double_wrapped(self):
        out = apply_dialog_prefixes('# "I am ready"', "ltx")
        self.assertEqual(out, 'The character says, "I am ready".')

    def test_visual_prompt_untouched(self):
        src = "A medium shot of a baker.\n# First batch of the morning.\nSteam rises."
        out = apply_dialog_prefixes(src, "ltx")
        self.assertEqual(
            out,
            "A medium shot of a baker.\n"
            'The character says, "First batch of the morning."\n'
            "Steam rises.",
        )

    def test_unknown_target_raises(self):
        with self.assertRaises(ValueError):
            apply_dialog_prefixes("# hi", "sd")


if __name__ == "__main__":
    unittest.main()
