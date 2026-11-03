r"""`@` media-reference token resolution (ported from ComfyUI-MiniMaxH3-Easy).

Source mechanism (nkxx188/ComfyUI-MiniMaxH3-Easy):
  - The rich editor's `@` trigger lists attached media + named elements; selecting
    one inserts an `@이미지N` (index mode) or `@이름` (named mode) chip into the prompt.
  - At prompt-build time the backend maps `@이미지N` -> H3's `<Picture N>` tag, which
    binds the Nth reference image by ordinal (H3-Multishot's ref_image_N identity
    binding). The editor serialises a placeholder; the resolver fills it.

comfy-webui's Gradio path has NO rich editor and NO such resolver, so a prompt that
carries `@이미지N` reaches the H3/LTX graph as literal text and the reference is NEVER
addressed by that token -- it only ever gets the auto-declared <Picture N> in the
named-template assembly. That is the gap this module closes for the INDEX mode:

  * MiniMax H3 (`minimax_h3` `prompt` input): `@이미지N` -> `<Picture N>` in place.
    Ordinal N is the position of the reference image in the ref list (1-based), which
    is exactly how h3NamedTemplate numbers <Picture N>, so the token and the auto-declared
    subject agree.
  * LTX 2.5: there is no free-reference stack -- only a start and an end anchor
    (FLF2VA). `@이미지1` -> "the starting frame", `@이미지2` -> "the ending frame",
    `@이미지N>=3` -> "reference frame N" (the honest adapter emission mirroring the
    comfyui_media_refs MediaRefResolve ltx target; full free reference needs IC-LoRA
    wiring, documented gap -- the guide_plan carries that note, not the text).
  * `keep`: leave `@이미지N` intact (normalisation only, no tag swap).

Named `@이름` is intentionally left unresolved here: comfy-webui has no element-name ->
ordinal map at the text level (named elements live on the OpenHiggsfield side, and the
name -> reference mapping must travel with the plane, not be re-derived from text).
Resolving `@이름` end-to-end is tracked in the dock rich-editor card (t_369bfe36).

Video chips (t_e441cf76 design decision, YES): the dock emits `@동영상N` for an attached
video with type-based independent numbering (tray=add order), and h3NamedTemplate labels
the Nth video `<Video ${index + 1}>` -- ordinal independent of the image count
(to-platform.ts L405). The two coordinate systems agree exactly, so `@동영상N` ->
`<Video N>` is a faithful numeric transposition on the H3 target, and it lands on the
same slot as the auto-declared label when both appear. The audio chip is deliberately
NOT resolved: the template's audio ordinal is `videos.length + audio_index + 1`
(to-platform.ts L409), which mismatches the dock's `@오디오N` type-local numbering --
transposing would silently point at a different slot, so `@오디오N` stays literal.
LTX target: video tokens are a no-op (LTX 2.5 has no free-reference stack at all --
start/end anchors are images only).

Korean-particle safety (from the t_e92daf19 convention): the token is `@이미지<digits>` /
`@동영상<digits>` and the following particle (이/가/을/를/로/으로 ...) sits OUTSIDE the
token, so replacing only the token leaves the particle intact -- `@이미지2가` ->
`<Picture 2>가`, `@동영상1가` -> `<Video 1>가`, no case destruction.

Zero-regression guarantee: a prompt carrying no token that THIS target can resolve is
returned byte-identical (the original string object itself, CRLF and all), mirroring
apply_dialog_prefixes. A video-only prompt is therefore byte-identical on the LTX target.
"""

import re

# The index token the dock emits for an attached image (Korean "image N"). Aliases are
# accepted defensively so a prompt written in English or a variant still resolves.
_INDEX_TOKEN_ALIASES = (r"이미지", r"image", r"Image", r"img", r"그림")
_INDEX_RE = re.compile(
    r"@(?:" + "|".join(_INDEX_TOKEN_ALIASES) + r")\s*(\d+)"
)

H3_PICTURE_OPEN = "<Picture "
H3_PICTURE_CLOSE = ">"

LTX_START = "the starting frame"
LTX_END = "the ending frame"
LTX_REF_PREFIX = "reference frame "


def has_reference_tokens(prompt: str) -> bool:
    """True when the prompt carries at least one `@이미지N` index token."""
    if not isinstance(prompt, str):
        return False
    return bool(_INDEX_RE.search(prompt))


def _picture_tag(n: int) -> str:
    return "{}{}{}".format(H3_PICTURE_OPEN, n, H3_PICTURE_CLOSE)


def _ltx_phrase(n: int) -> str:
    if n == 1:
        return LTX_START
    if n == 2:
        return LTX_END
    return "{}{}".format(LTX_REF_PREFIX, n)


def apply_reference_tokens(prompt: str, target: str = "h3") -> str:
    """Rewrite `@이미지N` index tokens into the target model's reference convention.

    target:
      "h3"  -> `@이미지N` becomes `<Picture N>` in place (H3 picture tag).
      "ltx" -> `@이미지1` -> "the starting frame", `@이미지2` -> "the ending frame",
               `@이미지N>=3` -> "reference frame N".
      "keep"-> the `@이미지N` text is left intact (no tag swap).

    Particles and surrounding text are preserved (only the token is replaced). Prompts
    without index tokens are returned byte-identical.
    """
    if not isinstance(prompt, str):
        return prompt
    if not has_reference_tokens(prompt):
        return prompt  # zero-regression: exact original object

    if target == "keep":
        return prompt

    def _sub(match: "re.Match") -> str:
        n = int(match.group(1))
        if target == "h3":
            return _picture_tag(n)
        if target == "ltx":
            return _ltx_phrase(n)
        raise ValueError("unknown reference target: {!r}".format(target))

    return _INDEX_RE.sub(_sub, prompt)
