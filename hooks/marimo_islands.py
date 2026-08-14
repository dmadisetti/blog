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
import io
import json
import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

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
# Pages whose cells wrote a cache, as {page url: notebook path}. Copied into the
# built site in on_post_build, once mkdocs has finished writing the pages.
_cached_pages: dict[str, str] = {}


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


def _notebook_path(src_path: str) -> Path:
    """Stable notebook path handed to the kernel for a page's cells.

    Deliberately not the page's own source: a queued post is a transient mirror
    under `docs/`, so caching beside it would publish the blobs and lose them on
    the next mirror sweep. Keyed by file name, so the cache survives edits.
    """
    return _CACHE_DIR / "nb" / Path(src_path).name


def _bundle_cache(nb_path: Path, out_dir: Path) -> None:
    """Copy this notebook's cached cell values into `<out_dir>/public/cache/`.

    Same call `marimo export html-wasm --execute` makes, pointed at the page's
    directory in the built site: that is where the browser runtime looks
    (`notebook_location()/public/cache/`). Without it a cached cell has nothing
    to hydrate from and re-runs in WebAssembly.
    """
    try:
        from marimo._export.file import bundle_cache_export
        from marimo._export.requests import CacheBundleRequest
        from marimo._utils.marimo_path import MarimoPath

        bundle_cache_export(
            CacheBundleRequest(
                notebook_path=MarimoPath(str(nb_path)),
                output_directory=out_dir,
                stdout=io.StringIO(),  # "Bundled N cache files" is not ours to print
            )
        )
    except Exception:
        log.warning("marimo: cache bundling failed for %s", nb_path, exc_info=True)


def _page_base_url(config: Any, page: Any) -> str:
    """Absolute path (no origin) at which this page will be served.

    The browser kernel needs it to find `public/cache/`; it cannot work it out
    itself (see `_WASM_LOCATION_SHIM`). `site_url`'s path carries any subpath
    the site is deployed under — empty here, but not for a project Pages site.
    """
    prefix = urlsplit(str(config.get("site_url") or "")).path
    return "/" + f"{prefix}/{page.url}".strip("/")


def _build_bundle(src_path: str, mode: str, base_url: str) -> dict[str, Any] | None:
    """Build islands for a source file, with an on-disk content-hash cache."""
    source = Path(src_path).read_bytes()
    execute, reactive = _MODE_KWARGS.get(mode, _MODE_KWARGS[_DEFAULT_MODE])
    display_code = os.environ.get("MARIMO_ISLANDS_SHOW_CODE") == "1"

    # Cache key folds in everything that changes the output: source bytes, the
    # render tier, code visibility, the page's own URL (baked into the payload
    # so the browser can find the cache), and the engine/marimo version.
    key_material = b"\0".join(
        [
            source,
            mode.encode(),
            b"1" if display_code else b"0",
            base_url.encode(),
            _islands_export.__version__.encode(),
        ]
    )
    key = hashlib.sha256(key_material).hexdigest()
    cache_file = _CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    # The kernel roots its on-disk caches (`__marimo__/`, which backs both
    # `mo.persistent_cache` and `cache_cells`) next to the notebook path it is
    # given.
    nb_path = _notebook_path(src_path)
    nb_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        bundle = convert_md_to_islands(
            source.decode("utf-8"),
            execute=execute,
            display_code=display_code,
            reactive=reactive,
            source_path=str(nb_path),
            base_url=base_url,
        )
    except Exception:
        log.warning("marimo islands build failed for %s", src_path, exc_info=True)
        return None

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(bundle), encoding="utf-8")
    return bundle


def on_page_markdown(markdown: str, *, page: Any, config: Any, **_: Any) -> str:
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

    bundle = _build_bundle(
        page.file.abs_src_path, mode, _page_base_url(config, page)
    )
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
    if _MODE_KWARGS[mode][0]:  # cells ran, so there may be a cache to ship
        _cached_pages[page.url] = str(_notebook_path(page.file.abs_src_path))
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
    # The first-class island-JSON payload (empty for a static, no-kernel page)
    # goes *after* the spliced islands so every <marimo-island> cellId it
    # references is already in the DOM when the runtime hydrates from it.
    payload_script = bundle.get("payload_script", "")
    return _clean_head(bundle["head"]) + "\n" + spliced + "\n" + payload_script


def on_post_build(config: Any, **_: Any) -> None:
    """Ship each page's cell cache next to the page, after mkdocs writes it."""
    site_dir = Path(config["site_dir"])
    for url, nb_path in _cached_pages.items():
        _bundle_cache(Path(nb_path), site_dir / url.strip("/"))
    _cached_pages.clear()
