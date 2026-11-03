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
        self.assertTrue(has_reference_tokens("@동영상2"))  # video chips count too
        self.assertFalse(has_reference_tokens("@고양이"))
        self.assertFalse(has_reference_tokens("@오디오1"))  # audio is never a token here
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

    # ---- @동영상N -> <Video N> (H3 target, t_e441cf76 design YES) ----

    def test_h3_video_substitution(self):
        p = "@동영상1가 골목을 걷고 @동영상2가 배경, @동영상3 색감"
        out = apply_reference_tokens(p, "h3")
        self.assertEqual(out, "<Video 1>가 골목을 걷고 <Video 2>가 배경, <Video 3> 색감")

    def test_video_particle_preserved(self):
        p = "@동영상1가"
        out = apply_reference_tokens(p, "h3")
        self.assertEqual(out, "<Video 1>가")  # Korean particle survives, no case destruction

    def test_video_double_digit(self):
        p = "@동영상10과 @동영상11"
        out = apply_reference_tokens(p, "h3")
        self.assertEqual(out, "<Video 10>과 <Video 11>")

    def test_video_aliases(self):
        p = "@video1 walks, @Video2 behind, @vid3 prop"
        out = apply_reference_tokens(p, "h3")
        self.assertEqual(out, "<Video 1> walks, <Video 2> behind, <Video 3> prop")

    def test_video_space_variant(self):
        p = "@동영상 1가"
        out = apply_reference_tokens(p, "h3")
        self.assertEqual(out, "<Video 1>가")

    def test_mixed_image_video_h3(self):
        p = "@이미지1가 걷고 @동영상2가 웃고 @이미지3 색감"
        out = apply_reference_tokens(p, "h3")
        self.assertEqual(out, "<Picture 1>가 걷고 <Video 2>가 웃고 <Picture 3> 색감")

    def test_auto_label_coexistence(self):
        # The named-template may already declare <Video 1> verbatim; a user chip resolves
        # to the SAME slot, so both carriers must end up on the same tag (no renumbering).
        p = "<Video 1>의 motion을 살리고 @동영상1는 그대로"
        out = apply_reference_tokens(p, "h3")
        self.assertEqual(out, "<Video 1>의 motion을 살리고 <Video 1>는 그대로")

    # ---- @오디오N stays literal (t_e441cf76 design NO: ordinal mismatch) ----

    def test_audio_literal_zero_regression(self):
        p = "@동영상1의 motion을 살리고 @오디오1은 그대로"  # video resolvable, audio not
        out = apply_reference_tokens(p, "h3")
        self.assertIn("@오디오1", out)  # audio chip survives the rewrite
        self.assertNotIn("@동영상", out)

    def test_audio_only_is_byte_identical(self):
        p = "@오디오1은 그대로\r\n@고양이"
        out = apply_reference_tokens(p, "h3")
        self.assertIs(out, p)  # nothing resolvable -> exact same object

    # ---- LTX target: video tokens are a no-op ----

    def test_ltx_video_noop_zero_regression(self):
        p = "@동영상1가 골목을 걷는다"  # video-only prompt
        out = apply_reference_tokens(p, "ltx")
        self.assertIs(out, p)  # LTX cannot bind video -> byte-identical, same object

    def test_ltx_video_intact_alongside_image(self):
        p = "@이미지1가 걷고 @동영상2 소품, @오디오3 음성"
        out = apply_reference_tokens(p, "ltx")
        self.assertEqual(out, "the starting frame가 걷고 @동영상2 소품, @오디오3 음성")

    def test_keep_video(self):
        p = "@동영상1가 걷고 @오디오2 뒤풀이"
        out = apply_reference_tokens(p, "keep")
        self.assertIs(out, p)


if __name__ == "__main__":
    unittest.main()
