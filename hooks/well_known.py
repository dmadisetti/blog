"""mkdocs hook: ship docs/.well-known/ verbatim into the built site.

mkdocs skips dot-directories during the build, but identity/verification files
have to live at `/.well-known/` — e.g. `atproto-did`, which proves to Bluesky
that this domain owns the custom handle (the static-file method). Copy the tree
in `on_post_build` so it lands in the deployed site. `mkdocs gh-deploy` writes a
`.nojekyll`, so GitHub Pages serves the dot-dir without Jekyll filtering it.

This only matters once the apex domain (readme.dm) points at this Pages site;
until then the file rides along harmlessly.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

log_prefix = "well-known"


def on_post_build(*, config: Any, **_: Any) -> None:
    src = Path(config["docs_dir"]) / ".well-known"
    if not src.is_dir():
        return
    dst = Path(config["site_dir"]) / ".well-known"
    shutil.copytree(src, dst, dirs_exist_ok=True)
