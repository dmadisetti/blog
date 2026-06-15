"""mkdocs hook: render queued drafts locally without hand-syncing.

`_queue/scheduled/` holds posts being worked on (ordinal-prefixed, gitignored).
Hand-copying them into `docs/posts/` to preview was painful and error-prone, so
this mirrors them automatically:

  * on `build` / `serve` — mirror each render-ready queued post (one with a
    `date:`) into `docs/posts/` as `queued.<name>.md`, and tell `serve` to watch
    the queue so edits live-reload.
  * on `gh-deploy` — do nothing, so production publishes only what the weekly
    pipeline has actually moved into `docs/posts/`.

Mirrors are transient: `queued.*.md` is gitignored, rewritten only on real
content change (so the dev server doesn't loop), and removed on shutdown.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import Any

QUEUE = Path("_queue/scheduled")
POSTS = Path("docs/posts")
PREFIX = "queued."
# Strip the queue ordinal prefix: optional leading '_' (negative), int, optional
# '_decimal', trailing '_'. e.g. _02_hello.md -> hello.md, 00_rowdybot -> rowdybot.
_ORDINAL = re.compile(r"^_?\d+(?:_\d+)?_")

_enabled = False


def _ordinal_value(name: str) -> float:
    """Queue ordinal as a number: _02_x -> -2, 00_x -> 0, 1_5_x -> 1.5."""
    s, sign = name, 1.0
    if s.startswith("_"):
        sign, s = -1.0, s[1:]
    parts = s.split("_")
    if not parts[0].isdigit():
        return 0.0
    if len(parts) > 2 and parts[1].isdigit():  # int_decimal_name
        return sign * float(f"{parts[0]}.{parts[1]}")
    return sign * float(parts[0])


def on_startup(command: str, **_: Any) -> None:
    global _enabled
    _enabled = command in ("build", "serve")  # never on gh-deploy


def _clean() -> None:
    for f in POSTS.glob(f"{PREFIX}*.md"):
        f.unlink()


def on_config(config: Any, **_: Any) -> Any:
    mirrors: dict[Path, str] = {}
    if _enabled and QUEUE.is_dir():
        # Order the preview by queue ordinal: HIGHER ordinal -> newer date -> top,
        # i.e. reverse-chronological / newest-published on top, matching the live
        # site (the launch post, lowest ordinal, sits at the bottom). Synthetic;
        # the pipeline stamps the real date at publish. Real queue files untouched.
        base = datetime.datetime.combine(datetime.date.today(), datetime.time(12))
        for src in sorted(QUEUE.glob("*.md")):
            text = src.read_text(encoding="utf-8")
            if not re.search(r"^date:", text, re.M):
                continue  # draft without a date — not render-ready, skip
            when = base + datetime.timedelta(days=_ordinal_value(src.name))
            text = re.sub(r"^date:.*$", f"date: {when:%Y-%m-%d %H:%M:%S}",
                          text, count=1, flags=re.M)
            name = _ORDINAL.sub("", src.name) or src.name
            mirrors[POSTS / f"{PREFIX}{name}"] = text

    # Drop stale mirrors (source removed / disabled).
    for f in POSTS.glob(f"{PREFIX}*.md"):
        if f not in mirrors:
            f.unlink()
    # Write only what changed, so the serve watcher doesn't loop on our own writes.
    for dest, text in mirrors.items():
        if not dest.exists() or dest.read_text(encoding="utf-8") != text:
            dest.write_text(text, encoding="utf-8")
    return config


def on_serve(server: Any, **_: Any) -> Any:
    if QUEUE.is_dir():
        server.watch(str(QUEUE))
    return server


def on_shutdown(**_: Any) -> None:
    _clean()
