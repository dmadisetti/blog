# Copyright 2026 Marimo. All rights reserved.
"""Convert host markdown (with marimo fences) into embeddable islands.

VENDORED into the blog from the upstream ``marimo export islands-json`` work
(marimo/_convert/markdown/to_islands.py). It is deliberately self-contained: it
imports only *stable, unmodified* marimo internals (``to_ir``,
``_island_generator``, ``_version``), so the blog runs against a stock published
marimo (>=0.23.9) instead of an editable checkout of a patched clone. When
``islands-json`` lands upstream, delete this file and call marimo directly.

It parses a host markdown document, extracts the marimo code cells -- leaving
prose for the host renderer -- builds them as a single *reactive* app, and
returns a JSON-able bundle that ``hooks/marimo_islands.py`` splices back into the
page. The bundle is presentation-light: a shared ``head`` (islands runtime
scripts/styles) plus one entry per cell, in document order, with both the
structured output (``mimetype`` + ``data``) and ready-to-hydrate island ``html``.

This mirrors the logic validated in the ``quarto-marimo`` extension's
``extract.py``, but leaves the Quarto-specific concerns (``#|`` execution
directives, the ``sql {.marimo}`` dot-fence rewrite, and the MIME-sensitive
PDF/Pandoc degradation path) out. The ``--sandbox`` Pyodide re-exec that the CLI
offered is also dropped: in-process, cells execute against the blog's own venv.
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
    MarimoIslandGenerator,
    MarimoIslandStub,
)
from marimo._version import __version__

# One emitted slot per marimo fence, in document order: the per-cell
# display_code resolution plus the stub (None for a disabled cell, which is
# still kept as a slot so the outputs list stays aligned with the fences the
# consumer must splice).
_Slot = tuple[bool, Optional[MarimoIslandStub]]


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


def _build_payload(
    root: Element,
    *,
    execute: bool,
    display_code: bool,
    reactive: bool,
    development_url: str | bool,
) -> SafeWrap[dict[str, Any]]:
    """Build islands from a parsed marimo-markdown tree and serialize them.

    Prose blocks (``marimo-md``) are skipped -- they belong to the host
    document. Code and SQL cells are normalized through marimo's own
    ``get_source_from_tag`` so we inherit the canonical fence handling rather
    than re-deriving it.
    """
    generator = MarimoIslandGenerator()
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
        asyncio.run(generator.build())

    head = generator.render_head(_development_url=development_url)
    outputs = [
        _serialize_output(display_code, stub, reactive=reactive)
        for display_code, stub in slots
    ]

    return SafeWrap(
        {
            "version": __version__,
            "head": head,
            "count": len(slots),
            "outputs": outputs,
        }
    )


def _make_parser(
    *,
    execute: bool,
    display_code: bool,
    reactive: bool,
    development_url: str | bool,
) -> MarimoMdParser:
    """Build a one-shot parser whose serializer emits the islands bundle."""

    def serialize(root: Element) -> SafeWrap[dict[str, Any]]:
        return _build_payload(
            root,
            execute=execute,
            display_code=display_code,
            reactive=reactive,
            development_url=development_url,
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

    Returns:
        A JSON-serializable dict ``{version, head, count, outputs}`` where each
        output is ``{code, mimetype, data, html, disabled, reactive}``.
    """
    parser = _make_parser(
        execute=execute,
        display_code=display_code,
        reactive=reactive,
        development_url=development_url,
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
    return {
        "version": __version__,
        "head": head,
        "count": len(stubs),
        "outputs": outputs,
    }
