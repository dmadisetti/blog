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


def post_bluesky(text: str, link: str | None, *, dry_run: bool) -> str:
    identifier = os.environ.get("BLUESKY_IDENTIFIER", _DEFAULT_DID)
    if dry_run:
        return f"[dry-run] bluesky as {identifier}: {text!r}" + (
            f" +link {link}" if link else ""
        )
    from atproto import Client, client_utils

    password = _read_secret("BLUESKY_APP_PASSWORD", "/run/agenix/bsky-key")
    client = Client()
    client.login(identifier, password)
    if link:
        body = client_utils.TextBuilder().text(f"{text}\n\n").link(link, link)
        post = client.send_post(body)
    else:
        post = client.send_post(text)
    return post.uri


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
    ap.add_argument("--link", help="URL to append as a rich-text link (Bluesky).")
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
