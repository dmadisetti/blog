"""mkdocs hook: grouped inline tooltips.

Authoring shorthand — two adjacent bracket pairs (reference-link shaped):

    [visible phrase][caption]

renders "visible phrase" with "caption" as a hover tooltip. The grouping lets
the visible part be a whole phrase, not a single word:

    [ideally something][like this]

Emitted as <abbr title="caption">visible phrase</abbr>; with Material's
`content.tooltips` feature that becomes a styled tooltip (plain browsers still
show the native title on hover).

Plain links stay native Markdown: [text](url). Images (![alt][ref]) and fenced
or inline code are left untouched. We don't use Markdown *reference* links on
this site, so `[a][b]` is unambiguously a tooltip here.
"""

from __future__ import annotations

import html
import re
from typing import Any

# [visible][caption] — both non-empty, no nested brackets/newlines. A leading
# '!' (image) is excluded via lookbehind.
_TIP = re.compile(r"(?<!\!)\[([^\]\n]+)\]\[([^\]\n]+)\]")

# Fenced code blocks and inline code, masked out before the transform so code
# containing [a][b] is never rewritten.
_CODE = re.compile(r"```.*?```|~~~.*?~~~|`[^`\n]+`", re.S)

_SENTINEL = "\x00{}\x00"
_RESTORE = re.compile(r"\x00(\d+)\x00")


def _tip(m: re.Match[str]) -> str:
    visible, caption = m.group(1), m.group(2)
    return f'<abbr title="{html.escape(caption, quote=True)}">{visible}</abbr>'


def on_page_markdown(markdown: str, **_: Any) -> str:
    if "][" not in markdown:
        return markdown
    blocks: list[str] = []

    def stash(m: re.Match[str]) -> str:
        blocks.append(m.group(0))
        return _SENTINEL.format(len(blocks) - 1)

    protected = _CODE.sub(stash, markdown)
    transformed = _TIP.sub(_tip, protected)
    return _RESTORE.sub(lambda m: blocks[int(m.group(1))], transformed)
