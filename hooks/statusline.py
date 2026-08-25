"""mkdocs hook: the facts the footer statusline needs.

The footer is a vim/lualine-style status bar (see overrides/partials/footer.html):

    docs/posts/watermarked.md   markdown+marimo  utf-8[unix]  CC BY  1,153 words  ea49217   15%:16/103 ☰ ℅:1

Everything left of the position readout is static per page, so it's computed
here at build time rather than in JS:

  * `config.extra.build`  — the deployed commit (short + full), whether the tree
    was dirty when built, and the repo-root prefix of `docs/`, so the path
    segment can link to the exact blob/commit on GitHub.
  * `page.meta.stat`      — per-page buffer facts: source line count, word
    count, and filetype (`markdown+marimo` when the page has islands).

Registered FIRST in mkdocs.yml's hook list so the word/filetype counts see the
author's markdown, before marimo_islands rewrites its fences.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

# Fenced marimo cells: ```python {.marimo} — matches the custom_fences config.
_MARIMO = re.compile(r"^\s*(?:```|~~~)[^\n]*\{\s*\.?marimo", re.M)
_WORD = re.compile(r"\S+")


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ("git", *args), capture_output=True, text=True, timeout=5, check=True
        )
        return out.stdout.strip()
    except Exception:  # not a repo, no git, shallow clone — degrade quietly
        return ""


def on_config(config: Any, **_: Any) -> Any:
    sha = _git("rev-parse", "HEAD")
    # `--untracked-files=no`: a scratch notebook lying around isn't a modified
    # buffer. Tracked edits are — that's what vim's [+] means.
    dirty = bool(_git("status", "--porcelain", "--untracked-files=no"))

    root = _git("rev-parse", "--show-toplevel")
    docs = Path(config["docs_dir"])
    try:
        prefix = docs.resolve().relative_to(Path(root).resolve()).as_posix()
    except Exception:
        prefix = docs.name

    config["extra"]["build"] = {
        "sha": sha[:7],
        "sha_full": sha,
        "dirty": dirty,
        "docs_prefix": prefix,
    }
    return config


def on_page_markdown(markdown: str, page: Any, **_: Any) -> str:
    words = len(_WORD.findall(markdown))
    page.meta["stat"] = {
        "lines": markdown.count("\n") + 1,
        "words": words,
        "words_display": f"{words:,}",
        "filetype": "markdown+marimo" if _MARIMO.search(markdown) else "markdown",
    }
    return markdown
