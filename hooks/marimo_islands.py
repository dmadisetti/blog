"""mkdocs hook: render marimo cells as reactive islands, in-process.

Replaces the mkdocs-marimo plugin. For each page that contains ```` ```python {marimo} ````
fences, this builds *all* of the page's marimo cells together as one reactive
app (so a variable defined in one fence is visible in the next), then splices
the rendered islands back where the fences were and injects the islands runtime
into the page.

The conversion engine is vendored alongside this hook in `_islands_export.py`
(the self-contained core of the upstream `marimo export islands-json` work),
called directly in-process. That keeps the blog on a *stock* published marimo
(>=0.23.9) — no editable checkout of a patched clone, no subprocess. Cells
execute against the blog's own venv, so a post's runtime deps just go in
`pyproject.toml`. (The CLI's `--sandbox` Pyodide re-exec is intentionally not
carried over; see `_islands_export.py`.)

Why a hook and not a pymdownx custom fence: marimo cells are reactive across the
whole document, so every fence must be built together. A per-fence formatter
cannot do that. `on_page_markdown` runs the engine; `on_page_content` does the
splice after rendering so Markdown never mangles the island HTML.

Configuration (env vars):
  MARIMO_ISLANDS_SHOW_CODE "1" to show cell code by default (per-cell hide_code wins).
  MARIMO_ISLANDS_CACHE     Cache dir (default: ".cache/marimo-islands").
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

log = logging.getLogger("mkdocs.plugins.marimo_islands")

# Load the vendored engine by path — hooks aren't a package, so a plain sibling
# import isn't reliable across mkdocs' loader.
_spec = importlib.util.spec_from_file_location(
    "_islands_export", Path(__file__).with_name("_islands_export.py")
)
assert _spec is not None and _spec.loader is not None
_islands_export = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_islands_export)
convert_md_to_islands = _islands_export.convert_md_to_islands

# Opening fence with a {marimo} / {.marimo} brace, e.g. ```python {marimo},
# ```python {.marimo disabled="true"}, ```{marimo}. The closing fence is matched
# dynamically (same character, length >= the opener) by the line scanner.
_FENCE_OPEN = re.compile(
    r"^(?P<indent>[ \t]*)(?P<ticks>`{3,}|~{3,})[ \t]*"
    r"(?P<info>[^\n]*\{[ \t]*\.?marimo\b[^}]*\})[ \t]*$"
)
_SLOT = '<div class="marimo-island-slot" data-marimo-slot="{i}"></div>'
_SLOT_RE = re.compile(
    r'<div class="marimo-island-slot" data-marimo-slot="(?P<i>\d+)"></div>'
)
_CACHE_DIR = Path(os.environ.get("MARIMO_ISLANDS_CACHE", ".cache/marimo-islands"))

# Per-post render tier (frontmatter `marimo_mode`), borrowed from marimo-book.
# Maps to the engine's (execute, reactive) kwargs:
#   hybrid  – prerender outputs AND hydrate in the browser (default)
#   static  – prerender outputs, ship no kernel (lightest, not interactive)
#   wasm    – no prerender, hydrate from scratch in the browser
_MODE_KWARGS = {
    "hybrid": (True, True),
    "static": (True, False),
    "wasm": (False, True),
}
_DEFAULT_MODE = "hybrid"

# The islands runtime ships its own Google Fonts (Lora / PT Sans / Fira Mono),
# which fight the site font. We inherit Material's font in CSS, so drop the
# <link>s rather than download unused fonts.
_FONT_LINK_RE = re.compile(
    r'[ \t]*<link\b[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*', re.I
)

# Per-page bundles, keyed by source uri, populated in on_page_markdown and
# consumed in on_page_content within the same build.
_bundles: dict[str, dict[str, Any]] = {}


def _replace_fences(markdown: str) -> tuple[str, int]:
    """Swap each marimo fence for an ordered slot marker. Returns (text, count)."""
    lines = markdown.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    slot = 0
    while i < len(lines):
        m = _FENCE_OPEN.match(lines[i].rstrip("\n"))
        if not m:
            out.append(lines[i])
            i += 1
            continue
        ticks = m.group("ticks")
        close = re.compile(r"^[ \t]*" + re.escape(ticks[0]) + "{%d,}[ \t]*$" % len(ticks))
        j = i + 1
        while j < len(lines) and not close.match(lines[j].rstrip("\n")):
            j += 1
        # Replace the whole fenced block (open..close) with a standalone slot.
        out.append("\n" + _SLOT.format(i=slot) + "\n\n")
        slot += 1
        i = j + 1
    return "".join(out), slot


def _clean_head(head: str) -> str:
    """Drop the islands runtime's Google-font <link>s (we inherit Material's)."""
    return _FONT_LINK_RE.sub("", head)


def _build_bundle(src_path: str, mode: str) -> dict[str, Any] | None:
    """Build islands for a source file, with an on-disk content-hash cache."""
    source = Path(src_path).read_bytes()
    execute, reactive = _MODE_KWARGS.get(mode, _MODE_KWARGS[_DEFAULT_MODE])
    display_code = os.environ.get("MARIMO_ISLANDS_SHOW_CODE") == "1"

    # Cache key folds in everything that changes the output: source bytes, the
    # render tier, code visibility, and the engine/marimo version.
    key_material = b"\0".join(
        [
            source,
            mode.encode(),
            b"1" if display_code else b"0",
            _islands_export.__version__.encode(),
        ]
    )
    key = hashlib.sha256(key_material).hexdigest()
    cache_file = _CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    try:
        bundle = convert_md_to_islands(
            source.decode("utf-8"),
            execute=execute,
            display_code=display_code,
            reactive=reactive,
        )
    except Exception:
        log.warning("marimo islands build failed for %s", src_path, exc_info=True)
        return None

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(bundle), encoding="utf-8")
    return bundle


def on_page_markdown(markdown: str, *, page: Any, **_: Any) -> str:
    if "marimo" not in markdown or page.file.abs_src_path is None:
        return markdown

    new_markdown, count = _replace_fences(markdown)
    if count == 0:
        return markdown

    mode = str(getattr(page, "meta", {}).get("marimo_mode", _DEFAULT_MODE)).lower()
    if mode not in _MODE_KWARGS:
        log.warning(
            "marimo: unknown marimo_mode %r in %s; using %s.",
            mode,
            page.file.src_uri,
            _DEFAULT_MODE,
        )
        mode = _DEFAULT_MODE

    bundle = _build_bundle(page.file.abs_src_path, mode)
    if bundle is None:
        return markdown  # leave the page untouched; failure already logged

    outputs = bundle.get("outputs", [])
    if len(outputs) != count:
        # Slot order and island order both follow document order; a mismatch
        # means our fence scan and marimo's parser disagree. Don't risk a
        # misaligned splice -- skip and warn.
        log.warning(
            "marimo: found %d fences but %d islands in %s; skipping splice.",
            count,
            len(outputs),
            page.file.src_uri,
        )
        return markdown

    _bundles[page.file.src_uri] = bundle
    return new_markdown


def on_page_content(html: str, *, page: Any, **_: Any) -> str:
    bundle = _bundles.pop(page.file.src_uri, None)
    if bundle is None:
        return html

    outputs = bundle["outputs"]

    def _swap(m: re.Match[str]) -> str:
        return outputs[int(m.group("i"))]["html"]

    spliced = _SLOT_RE.sub(_swap, html)
    # Inject the islands runtime (scripts/styles) once per page. mkdocs has no
    # per-page <head> hook, so prepend it to the content; browsers honor
    # <script>/<link> in the body and the islands runtime bootstraps from there.
    return _clean_head(bundle["head"]) + "\n" + spliced
