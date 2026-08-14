# Copyright 2026 Marimo. All rights reserved.
"""Convert host markdown (with marimo fences) into embeddable islands.

First-class island-JSON hydration landed upstream in marimo 0.23.12
(``MarimoIslandStub.to_payload`` / ``MarimoIslandGenerator.render_payload``) and
session-cache-backed WASM in 0.23.14. This file no longer hand-rolls the islands
serialization: it now *delegates* to that official public API. What remains here
is the one thing marimo's own loaders don't cover -- extracting marimo cells out
of a *host markdown* document (``from_file`` only reads standalone ``.py``
notebooks). So we parse the host doc for its ``{.marimo}`` fences, feed the code
to a stock ``MarimoIslandGenerator``, build it as a single reactive app, and let
marimo produce both the per-cell island HTML (``stub.render``) and the app-wide
JSON payload (``render_payload``) that the islands runtime hydrates from.

The returned bundle is presentation-light: a shared ``head`` (islands runtime
scripts/styles), one entry per cell in document order (structured
``mimetype``/``data`` plus ready-to-hydrate island ``html``), and a single
``payload_script`` -- the ``application/vnd.marimo.islands+json`` ``<script>``
that carries the first-class hydration manifest. ``hooks/marimo_islands.py``
splices the per-cell HTML back into the page and injects the payload once.

The output HTML carries the executed outputs (instant, no-JS first paint = the
"cache"); the JSON payload carries code + reactivity so the cells go live in the
browser via Pyodide (= "wasm"). Together that is marimo's first-class
wasm + cache path, embedded inline in an SSG page.

Requires marimo >=0.23.14. The Quarto-specific concerns (``#|`` execution
directives, PDF/Pandoc MIME degradation) and the CLI's ``--sandbox`` Pyodide
re-exec are intentionally out of scope: in-process, cells execute against the
blog's own venv.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional
from xml.etree.ElementTree import Element

from marimo._convert.markdown.to_ir import (
    MARIMO_MD,
    MarimoMdParser,
    SafeWrap,
    get_cell_config_from_tag,
    get_source_from_tag,
)
from marimo._islands._island_generator import (
    ISLANDS_JSON_SCHEMA_VERSION,
    ISLANDS_JSON_SCRIPT_TYPE,
    MarimoIslandGenerator,
    MarimoIslandStub,
    json_script,
)
from marimo._version import __version__

# One emitted slot per marimo fence, in document order: the per-cell
# display_code resolution plus the stub (None for a disabled cell, which is
# still kept as a slot so the outputs list stays aligned with the fences the
# consumer must splice).
_Slot = tuple[bool, Optional[MarimoIslandStub]]


# Injected as the app's first cell. In the browser, marimo resolves the cache
# store's base URL from `notebook_location()`, which reads `js.location` -- but
# the islands runtime builds its Pyodide worker from a Blob, so that is
# `blob:<origin>/<uuid>` and every cache fetch dies inside the worker without
# ever reaching the site (observed: cache miss, zero HTTP requests). The origin
# survives in that string, so recover it and point the store at the page, which
# is where `on_post_build` bundles the blobs. No-op outside the browser.
# The single name is underscore-prefixed -- marimo treats those as cell-local, so
# this cannot collide with the post's own definitions and nothing here joins the
# graph. Everything else lives inside the function: a conditional import at cell
# scope leaves a name the cell cache expects but cannot find off-emscripten
# ("Cache save failed ... variable not present"), which is just noise.
_WASM_LOCATION_SHIM = '''def _marimo_islands_patch_cache_location():
    import sys

    if sys.platform != "emscripten":
        return
    import js

    import marimo._runtime.runtime as rt

    origin = "/".join(str(js.location.href).removeprefix("blob:").split("/")[:3])
    rt.notebook_location = lambda: rt.URLPath(origin + {base!r})


_marimo_islands_patch_cache_location()
'''


async def _build_with_cache(generator: MarimoIslandGenerator) -> None:
    """Run the app like ``generator.build()``, but with caching turned on.

    ``MarimoIslandGenerator.build`` closes the kernel non-gracefully, and the
    kernel only flushes its cache writes on a graceful close -- so an island
    build computes caches and then throws them away, and every rebuild re-runs
    every cell (re-fetching over the network, if that is what the cell does).
    ``marimo export html-wasm --execute`` avoids this by asking for a cache
    export; that flag is what forces both ``cache_cells`` and the graceful
    close. There is no public seam to pass it through, so this reproduces
    ``build()`` with the flag set, and falls back to stock behaviour if
    marimo's internals move.
    """
    from marimo._export.file import run_notebook
    from marimo._export.requests import (
        NotebookExecutionOptions,
        RunNotebookRequest,
    )
    from marimo._session.notebook import AppFileManager

    try:
        session, _ = await run_notebook(
            RunNotebookRequest(
                file_manager=AppFileManager.from_app(
                    generator._app, filename=generator._source_filename
                ),
                options=NotebookExecutionOptions(
                    cli_args={}, argv=None, cache_export=True
                ),
            )
        )
    except Exception:
        await generator.build()
        return

    generator.has_run = True
    for stub in generator._stubs:
        stub._internal_app = generator._app
        stub._session_view = session


def _serialize_output(
    display_code: bool,
    stub: Optional[MarimoIslandStub],
    *,
    reactive: bool,
) -> dict[str, Any]:
    """Serialize one island slot into the bundle's structured form."""
    if stub is None:
        # Disabled cell: keep the slot so ordering matches the doc's fences,
        # but emit nothing executable.
        return {
            "code": "",
            "mimetype": None,
            "data": None,
            "html": "",
            "disabled": True,
            "reactive": False,
        }

    output = stub.output
    return {
        "code": stub.code,
        "mimetype": output.mimetype if output is not None else None,
        "data": output.data if output is not None else None,
        "html": stub.render(
            display_code=display_code,
            display_output=True,
            is_reactive=reactive,
        ),
        "disabled": False,
        "reactive": reactive,
    }


def _payload_script(
    generator: MarimoIslandGenerator, slots: list[_Slot]
) -> str:
    """Emit the first-class island-JSON hydration manifest for the app.

    One ``application/vnd.marimo.islands+json`` script for the whole page, keyed
    by ``appId`` and matched to the spliced ``<marimo-island>`` elements by
    ``cellId``. Built from ``stub.to_payload`` (the official serializer). We keep
    ``display_output`` on so the executed output rides in the payload too: that
    is the "cache" the browser kernel hydrates *from* instead of recomputing on
    load (the whole point of the cache export). The same output also ships inline
    in the per-cell island HTML for a no-JS / pre-hydration first paint; carrying
    it in both places is exactly what marimo's own ``render_body(include_payload)``
    does, and is correct whether the runtime rehydrates from the payload or the
    DOM. ``display_code`` mirrors the per-slot resolution so the manifest and the
    spliced island agree on whether the editor is shown.
    """
    cells = [
        stub.to_payload(display_code=display_code)
        for display_code, stub in slots
        if stub is not None
    ]
    payload = {
        "schemaVersion": ISLANDS_JSON_SCHEMA_VERSION,
        "appId": generator._app_id,
        "cells": cells,
    }
    return f'<script type="{ISLANDS_JSON_SCRIPT_TYPE}">{json_script(payload)}</script>'


def _build_payload(
    root: Element,
    *,
    execute: bool,
    display_code: bool,
    reactive: bool,
    development_url: str | bool,
    source_path: str | None,
    base_url: str | None,
) -> SafeWrap[dict[str, Any]]:
    """Build islands from a parsed marimo-markdown tree and serialize them.

    Prose blocks (``marimo-md``) are skipped -- they belong to the host
    document. Code and SQL cells are normalized through marimo's own
    ``get_source_from_tag`` so we inherit the canonical fence handling rather
    than re-deriving it.
    """
    generator = MarimoIslandGenerator()
    # Give the kernel a notebook path. Everything cache-shaped hangs off it:
    # `mo.notebook_dir()`, `mo.persistent_cache(...)` and (with
    # `[tool.marimo.runtime] cache_cells`) the per-cell cache all write to
    # `<parent>/__marimo__/`. Left unset, each build gets an anonymous kernel
    # with no stable place to look, so a cell that fetches over the network
    # re-fetches on every build.
    if source_path is not None:
        generator._source_filename = os.path.abspath(source_path)

    # The shim rides in the hydration payload (so it runs in the browser, first)
    # but never in `slots`, which must stay one-to-one with the document's
    # fences or the splice misaligns.
    shim_slots: list[_Slot] = []
    if reactive and base_url is not None:
        shim_slots.append(
            (
                False,
                generator.add_code(
                    _WASM_LOCATION_SHIM.format(base=base_url), is_raw=True
                ),
            )
        )
    slots: list[_Slot] = []

    for child in root:
        if child.tag == MARIMO_MD:
            continue  # prose stays in the host doc; the SSG renders it

        config = get_cell_config_from_tag(child)
        source = get_source_from_tag(child)  # native code + sql handling

        if config.disabled:
            # Still added to neither graph nor output, but keep a slot.
            slots.append((False, None))
            continue

        stub = generator.add_code(source, is_raw=True)
        # Per-cell ``hide_code`` overrides the global default.
        slots.append((display_code and not config.hide_code, stub))

    # Reactivity (in-browser hydration) is independent of whether we ran the
    # cells now: --no-execute is exactly the case where you want code-only
    # islands that hydrate in the browser (the WASM tier).
    if execute:
        asyncio.run(_build_with_cache(generator))

    head = generator.render_head(_development_url=development_url)
    outputs = [
        _serialize_output(display_code, stub, reactive=reactive)
        for display_code, stub in slots
    ]

    # First-class hydration manifest -- only meaningful when the cells actually
    # run in the browser. A ``static`` tier (reactive=False) ships no kernel, so
    # there is nothing to hydrate and we omit the payload entirely.
    payload_script = (
        _payload_script(generator, shim_slots + slots) if reactive else ""
    )

    return SafeWrap(
        {
            "version": __version__,
            "head": head,
            "count": len(slots),
            "outputs": outputs,
            "payload_script": payload_script,
        }
    )


def _make_parser(
    *,
    execute: bool,
    display_code: bool,
    reactive: bool,
    development_url: str | bool,
    source_path: str | None,
    base_url: str | None,
) -> MarimoMdParser:
    """Build a one-shot parser whose serializer emits the islands bundle."""

    def serialize(root: Element) -> SafeWrap[dict[str, Any]]:
        return _build_payload(
            root,
            execute=execute,
            display_code=display_code,
            reactive=reactive,
            development_url=development_url,
            source_path=source_path,
            base_url=base_url,
        )

    class _IslandsParser(MarimoMdParser):
        output_formats = {"islands": serialize}  # type: ignore[assignment]

    return _IslandsParser(output_format="islands")  # type: ignore[arg-type]


def _unwrap(result: Any) -> dict[str, Any]:
    # Python-Markdown's ``convert`` calls ``.strip()`` on the serializer output,
    # which SafeWrap maps to ``.inner``; tolerate either shape.
    if isinstance(result, SafeWrap):
        return result.inner
    return result


def convert_md_to_islands(
    text: str,
    *,
    execute: bool = True,
    display_code: bool = False,
    reactive: bool = True,
    development_url: str | bool = False,
    source_path: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Convert a host markdown document into an islands JSON bundle.

    Args:
        text: The host markdown, with marimo cells in fenced ``{.marimo}``
            blocks. Surrounding prose is ignored (left for the host renderer).
        execute: Run the cells and embed their rendered outputs. With
            ``False``, islands are emitted code-only for in-browser hydration.
        display_code: Show cell code in the emitted islands by default; a
            cell's own ``hide_code`` attribute still takes precedence.
        reactive: Whether the islands hydrate (run in the browser via Pyodide).
        development_url: Forwarded to ``render_head`` to point at a local
            islands bundle during development.
        source_path: Notebook path handed to the kernel, which roots
            ``mo.notebook_dir()`` and every on-disk cache (``__marimo__/``)
            beside it. Need not exist; only its directory is used.
        base_url: Site-root-relative path of the page the islands land on
            (e.g. ``/posts/watermarked``). Needed only for reactive islands:
            it tells the browser kernel where ``public/cache`` lives, which it
            otherwise cannot work out (see ``_WASM_LOCATION_SHIM``). Omit and
            the cells simply re-execute in the browser.

    Returns:
        A JSON-serializable dict ``{version, head, count, outputs,
        payload_script}`` where each output is ``{code, mimetype, data, html,
        disabled, reactive}`` and ``payload_script`` is the first-class
        island-JSON hydration ``<script>`` (empty when ``reactive`` is False).
    """
    parser = _make_parser(
        execute=execute,
        display_code=display_code,
        reactive=reactive,
        development_url=development_url,
        source_path=source_path,
        base_url=base_url,
    )
    return _unwrap(parser.convert(text))


def convert_notebook_to_islands(
    path: str,
    *,
    execute: bool = True,
    display_code: bool = False,
    reactive: bool = True,
    development_url: str | bool = False,
) -> dict[str, Any]:
    """Convert a marimo ``.py`` notebook file into an islands JSON bundle.

    Unlike :func:`convert_md_to_islands`, every cell is a code cell (a ``.py``
    notebook has no interleaved host prose), so all cells are emitted.
    """
    generator = MarimoIslandGenerator.from_file(
        os.fspath(path), display_code=display_code
    )
    stubs = list(generator._stubs)

    if execute:
        asyncio.run(generator.build())

    head = generator.render_head(_development_url=development_url)
    outputs = [
        _serialize_output(display_code, stub, reactive=reactive)
        for stub in stubs
    ]
    slots: list[_Slot] = [(display_code, stub) for stub in stubs]
    payload_script = _payload_script(generator, slots) if reactive else ""
    return {
        "version": __version__,
        "head": head,
        "count": len(stubs),
        "outputs": outputs,
        "payload_script": payload_script,
    }
