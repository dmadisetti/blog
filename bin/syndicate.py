#!/usr/bin/env python
"""Syndicate a post to Bluesky and/or Mathstodon.

Reads credentials from agenix (``/run/agenix/<name>``) with env-var overrides
for local dev. Non-secret config (identifier, instance URL) has sane defaults,
so a bare ``syndicate.py both "..."`` works once the secrets are in place.

Secrets (env overrides agenix file):
  Bluesky app password : $BLUESKY_APP_PASSWORD   else /run/agenix/bsky-key
  Mathstodon token     : $MASTODON_ACCESS_TOKEN   else /run/agenix/mathstodon-key

Config (non-secret):
  $BLUESKY_IDENTIFIER  default: the readme.dm DID (stable across handle renames)
  $MASTODON_BASE_URL   default: https://mathstodon.xyz

Usage:
  syndicate.py bluesky  "text" [--link URL]
  syndicate.py mastodon "text" [--lang en]
  syndicate.py both     "text" [--link URL] [--lang en]
  --dry-run  print what would post, hit no network, need no deps/secrets.

Deps live in the optional 'publish' group:  uv sync --group publish
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Stable account identity (public, not a secret). The DID survives handle
# renames, so this keeps working when the handle becomes @readme.dm.
_DEFAULT_DID = "did:plc:s2fkhpplh3qlqdrixlx3zvgd"
_DEFAULT_MASTODON = "https://mathstodon.xyz"


def _read_secret(env_name: str, agenix_path: str) -> str:
    """Env var wins (local dev / .env); else the agenix-mounted file."""
    val = os.environ.get(env_name)
    if val:
        return val.strip()
    p = Path(agenix_path)
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    raise SystemExit(
        f"missing credential: set ${env_name} or provision {agenix_path} "
        f"(nixos-rebuild to mount the agenix secret)."
    )


def _http_get(url: str, *, limit: int | None = None) -> bytes:
    """Fetch a URL over httpx (bundles CA certs; atproto already pulls it in;
    stdlib urllib has no CA bundle under the uv-managed CPython)."""
    import httpx

    r = httpx.get(
        url,
        headers={"User-Agent": "readme.dm-syndicate"},
        timeout=15,
        follow_redirects=True,
    )
    r.raise_for_status()
    return r.content[:limit] if limit else r.content


def _fetch_og(url: str) -> dict[str, str]:
    """Best-effort scrape of og:title / og:description / og:image from HTML.

    Handles either attribute order (property-then-content or the reverse).
    Returns whatever it finds; missing keys just fall back at the call site.
    """
    html_text = _http_get(url, limit=200_000).decode("utf-8", "replace")
    og: dict[str, str] = {}
    for prop in ("title", "description", "image"):
        m = re.search(
            rf'<meta[^>]+property=["\']og:{prop}["\'][^>]+content=["\']([^"\']*)["\']',
            html_text,
            re.I,
        ) or re.search(
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']og:{prop}["\']',
            html_text,
            re.I,
        )
        if m:
            og[prop] = m.group(1)
    return og


def post_bluesky(text: str, link: str | None, *, dry_run: bool) -> str:
    identifier = os.environ.get("BLUESKY_IDENTIFIER", _DEFAULT_DID)
    if dry_run:
        return f"[dry-run] bluesky as {identifier}: {text!r}" + (
            f" +card {link}" if link else ""
        )
    from atproto import Client, models

    password = _read_secret("BLUESKY_APP_PASSWORD", "/run/agenix/bsky-key")
    client = Client()
    client.login(identifier, password)

    if not link:
        return client.send_post(text).uri

    # Build an external embed ("link card") so the post renders the OG title,
    # description and image — not just a bare clickable URL.
    og = {}
    try:
        og = _fetch_og(link)
    except Exception as e:  # noqa: BLE001 — card is best-effort, never fatal
        print(f"warning: could not read OG tags from {link}: {e}", file=sys.stderr)

    thumb = None
    if og.get("image"):
        try:
            thumb = client.upload_blob(_http_get(og["image"])).blob
        except Exception as e:  # noqa: BLE001 — Bluesky caps blobs ~1MB
            print(f"warning: could not attach card image: {e}", file=sys.stderr)

    embed = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            uri=link,
            title=og.get("title") or link,
            description=og.get("description") or "",
            thumb=thumb,
        )
    )
    return client.send_post(text=text, embed=embed).uri


def post_mastodon(text: str, lang: str | None, *, dry_run: bool) -> str:
    base = os.environ.get("MASTODON_BASE_URL", _DEFAULT_MASTODON)
    if dry_run:
        return f"[dry-run] mastodon at {base}: {text!r}" + (
            f" lang={lang}" if lang else ""
        )
    from mastodon import Mastodon

    token = _read_secret("MASTODON_ACCESS_TOKEN", "/run/agenix/mathstodon-key")
    masto = Mastodon(access_token=token, api_base_url=base)
    status = masto.status_post(text, visibility="public", language=lang)
    return status["url"]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Syndicate a post to Bluesky / Mathstodon.")
    ap.add_argument("target", choices=["bluesky", "mastodon", "both"])
    ap.add_argument("text")
    ap.add_argument("--link", help="URL to attach as a link card / external embed (Bluesky).")
    ap.add_argument("--lang", help="BCP-47 language tag for the Mastodon post.")
    ap.add_argument("--dry-run", action="store_true", help="Print, don't post.")
    args = ap.parse_args(argv)

    results: list[str] = []
    if args.target in ("bluesky", "both"):
        results.append(post_bluesky(args.text, args.link, dry_run=args.dry_run))
    if args.target in ("mastodon", "both"):
        results.append(post_mastodon(args.text, args.lang, dry_run=args.dry_run))

    for r in results:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
