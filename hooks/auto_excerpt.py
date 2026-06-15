"""mkdocs hook: auto-summarize blog posts on index/archive pages.

The Material blog plugin truncates a post at a `<!-- more -->` separator when it
lists it on the index. Rather than adding that marker to every post by hand,
this inserts one automatically after the first paragraph — so every post gets a
summary by default. A post that wants a different cut can still place its own
`<!-- more -->`, and this hook leaves it alone.
"""

from __future__ import annotations

from typing import Any

_SEP = "<!-- more -->"


def on_page_markdown(markdown: str, *, page: Any, **_: Any) -> str:
    meta = getattr(page, "meta", {}) or {}
    # Blog posts only (they carry a date); skip if the author set their own cut.
    if not meta.get("date") or _SEP in markdown:
        return markdown

    lines = markdown.split("\n")
    n = len(lines)
    i = 0
    # Skip leading blanks and heading lines to reach the first prose paragraph.
    while i < n and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
        i += 1
    # Advance to the end of that paragraph (next blank line / EOF).
    while i < n and lines[i].strip():
        i += 1
    if i >= n:
        return markdown  # no prose paragraph found; nothing to summarize

    lines[i:i] = ["", _SEP, ""]
    return "\n".join(lines)
