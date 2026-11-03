"""Unit tests for the `@이미지N` media-reference index resolver (media_ref_prompt)."""

import unittest

from module.video_gen.media_ref_prompt import (
    apply_reference_tokens,
    has_reference_tokens,
)


class TestReferenceTokens(unittest.TestCase):
    def test_zero_regression_no_token(self):
        p = "고양이가 골목을 걷는다\r\n@아무개"  # '@아무개' is a NAME, not an index token
        out = apply_reference_tokens(p, "h3")
        self.assertIs(out, p)  # exact same object -> byte identical

    def test_zero_regression_crlf(self):
        p = "plain visual prompt\r\nno tokens here"
        out = apply_reference_tokens(p, "ltx")
        self.assertIs(out, p)

    def test_h3_substitution(self):
        p = "@이미지1가 골목을 걷고 @이미지2가 배경, @이미지3 색감"
        out = apply_reference_tokens(p, "h3")
        self.assertEqual(out, "<Picture 1>가 골목을 걷고 <Picture 2>가 배경, <Picture 3> 색감")

    def test_particle_preserved(self):
        p = "@이미지2가"
        out = apply_reference_tokens(p, "h3")
        self.assertEqual(out, "<Picture 2>가")  # Korean particle survives, no case destruction

    def test_ltx_anchors_and_free(self):
        p = "@이미지1가 골목을 걷고 @이미지2가 배경, @이미지5 소품"
        out = apply_reference_tokens(p, "ltx")
        self.assertEqual(out, "the starting frame가 골목을 걷고 the ending frame가 배경, reference frame 5 소품")

    def test_keep_leaves_text(self):
        p = "@이미지1가 걷고 @이미지2 뒤풀이"
        out = apply_reference_tokens(p, "keep")
        self.assertEqual(out, p)

    def test_aliases(self):
        p = "@image1 walks, @Image2 behind, @img3 prop"
        out = apply_reference_tokens(p, "h3")
        self.assertEqual(out, "<Picture 1> walks, <Picture 2> behind, <Picture 3> prop")

    def test_name_not_resolved(self):
        p = "@고양이가 골목을 걷고 @홍길동"
        out = apply_reference_tokens(p, "h3")
        self.assertIs(out, p)  # named handles left untouched (no name->ordinal map here)

    def test_has_tokens(self):
        self.assertTrue(has_reference_tokens("@이미지3"))
        self.assertFalse(has_reference_tokens("@고양이"))
        self.assertFalse(has_reference_tokens(None))  # pyright: ignore[reportArgumentType]

    def test_non_string(self):
        self.assertEqual(apply_reference_tokens(None, "h3"), None)  # pyright: ignore[reportArgumentType]

    def test_compose_after_dialog(self):
        # reference resolver runs AFTER dialog wrapping; the <d> span stays intact and
        # the index token inside the rest of the prompt still resolves.
        p = "@이미지1가 골목을 걷는다\n#안녕"
        out = apply_reference_tokens(p, "h3")
        self.assertIn("<Picture 1>가 골목을 걷는다", out)
        self.assertIn("#안녕", out)  # dialog token untouched by THIS module


if __name__ == "__main__":
    unittest.main()
