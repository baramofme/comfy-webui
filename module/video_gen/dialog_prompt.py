r"""`#` dialogue-prefix preprocessing (ported from ComfyUI-MiniMaxH3-Easy).

Source mechanism (nkxx188/ComfyUI-MiniMaxH3-Easy, 2026-11-03 clone):
  - The `#` key in the rich prompt editor is a *frontend shortcut*: it inserts a
    dialogue block into the contenteditable DOM
    (`web/minimax_h3_easy_ui.js` keydown handler line ~6451 ->
    `insertDialogueBlockAtSelection` 4113 -> `makeDialogueBlock` 3482).
  - Serialization (`buildRuntimePrompt` line ~2638) converts each
    `{type: "dialogue"}` part into `<d>...text...</d>` inline in the prompt string
    sent to the server.
  - The backend (nodes.py) NEVER parses a `#` prefix. The `#` -> meaning conversion
    happens purely inside the editor's block model + serializer. (Dialogue semantics
    are H3's own convention: `<d>...</d>` marks spoken dialogue, per the official
    MiniMax H3 prompt guide.)

comfy-webui uses plain Gradio textboxes (no contenteditable editor), so this module
reproduces the same *semantics* at the text level: a line whose first non-whitespace
character is exactly one `#` is treated as a dialogue/sound cue instead of visual
description, and is routed into the target model's audio convention:

  * MiniMax H3 (`minimax_h3` node `prompt` input): serialized inline as
    `<d>content</d>` — the model's dialogue marker. H3 synthesizes audio from the
    same caption, and `<d>` tells it "this span is spoken dialogue".
  * LTX 2.5: there is NO dedicated audio/dialog text token. LTX is a joint AV model
    whose audio latents are conditioned by the *same* positive text conditioning
    (LTXVConditioning is a pass-through; `LTXVSetAudioRefTokens` only attaches
    reference-audio speaker identity, not text). The official LTX prompting guide
    requires spoken dialogue inside quotation marks within the flowing caption and
    warns that tag syntax from other models underperforms. So each `#` segment
    becomes a quoted speech cue sentence placed at its original position — that is
    the audio routing for LTX.

Zero-regression guarantee: a prompt with no `#` dialogue lines and no `\#` escapes
is returned byte-identical (the original string object itself, CRLF and all).
"""

import re

DIALOG_PREFIX = "#"

# Speech cue template for LTX (no speaker binding available at text level;
# official guide's phrasing pattern: '<subject> says, "<dialogue>"').
LTX_SPEECH_PREFIX = "The character says, "

H3_DIALOGUE_OPEN = "<d>"
H3_DIALOGUE_CLOSE = "</d>"

# Sentinel returned for an escaped line (`\#`): kept as visual text, backslash removed.
ESCAPE = object()

_TRAILING_SPEECH_PUNCT = ".!?"
_QUOTE_CHARS_OPEN = '"\u201c'
_QUOTE_CHARS_CLOSE = '"\u201d'

# A bare hex color token (e.g. '#ff0000') is visual text, not dialogue.
_HEX_COLOR_RE = re.compile(r"[0-9a-fA-F]{3,8}$")


def dialogue_line_content(line: str):
    """Return the dialogue text of `line` if it is a `#` dialogue line, else None.

    Rules (single choke point for the convention):
      - Trigger: the line's first non-whitespace character is exactly one `#`.
        `##...` (markdown-style) and mid-line `#` (hashtags, hex colors) are NOT
        dialogue — left untouched. A bare hex color token (`#ff0000`) is also
        treated as visual text so color words in the prompt never become dialogue.
      - Escape: a line starting with `\#` (backslash-hash after optional indent)
        is a literal `#` in the visual prompt; the backslash is consumed.
      - A bare `#` line with no content is dropped entirely.
    """
    stripped = line.lstrip()
    if not stripped:
        return None
    # escape hatch: literal hash in the visual prompt
    if stripped.startswith("\\#"):
        return ESCAPE
    if not stripped.startswith(DIALOG_PREFIX):
        return None
    after = stripped[len(DIALOG_PREFIX):]
    if after.startswith(DIALOG_PREFIX):  # '##' etc -> not dialogue
        return None
    content = after.strip()
    if not content:
        return ""  # marks an empty dialogue line to drop
    if _HEX_COLOR_RE.fullmatch(content):
        return None  # bare hex color token -> visual text, not dialogue
    return content


def _speech_cue(text: str) -> str:
    """Format one dialogue segment as an LTX quoted-speech cue sentence."""
    body = text.strip()
    # Already quoted? unwrap it so we never produce doubled quote marks.
    if len(body) >= 2 and body[0] in _QUOTE_CHARS_OPEN and body[-1] in _QUOTE_CHARS_CLOSE:
        body = body[1:-1].strip()
    if body and body[-1] not in _TRAILING_SPEECH_PUNCT:
        body = body + "."
    return '{}"{}"'.format(LTX_SPEECH_PREFIX, body)


def has_dialogue_lines(prompt: str) -> bool:
    """True when the prompt contains at least one `#` dialogue line."""
    if not isinstance(prompt, str):
        return False
    for line in prompt.splitlines():
        content = dialogue_line_content(line)
        if content is not None:
            return True
    return False


def apply_dialog_prefixes(prompt: str, target: str = "h3") -> str:
    """Rewrite `#` dialogue segments into the target model's audio convention.

    target:
      "h3"  -> dialogue lines become `<d>content</d>` in place (H3 marker).
      "ltx" -> dialogue lines become `The character says, "content".` in place.

    Segments keep their original order and positions; all non-dialogue text is
    preserved verbatim (visual prompt never corrupted). Prompts without dialogue
    lines are returned byte-identical.
    """
    if not isinstance(prompt, str):
        return prompt
    if not has_dialogue_lines(prompt):
        return prompt  # zero-regression: exact original object

    lines = prompt.splitlines()
    out = []
    for line in lines:
        content = dialogue_line_content(line)
        if content is ESCAPE:
            # escaped literal hash: keep the text, drop the backslash
            out.append(line.replace("\\#", "#", 1))
            continue
        if content is None:
            out.append(line)
            continue
        content = content.strip()
        if not content:
            continue  # drop bare '#' lines
        if target == "h3":
            out.append("{}{}{}".format(H3_DIALOGUE_OPEN, content, H3_DIALOGUE_CLOSE))
        elif target == "ltx":
            out.append(_speech_cue(content))
        else:
            raise ValueError("unknown dialog target: {!r}".format(target))
    return "\n".join(out)
