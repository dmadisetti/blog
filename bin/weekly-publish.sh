#!/usr/bin/env bash
# Safety-net weekly publisher.
#   If nothing has been published THIS WEEK (Mon–Sun), move the next ready post
#   from _queue/scheduled/ into docs/blog/posts/, commit, and push. Otherwise: no-op.
#
# Only ever publishes from _queue/scheduled/ (vetted, ready). drafts/ is never touched.
# Env: BLOG_DIR (default ~/blog), DRY_RUN=1 to preview without changing anything.
set -euo pipefail

BLOG="${BLOG_DIR:-/home/dylan/blog}"
QUEUE="$BLOG/_queue/scheduled"
POSTS="$BLOG/docs/posts"
DRY="${DRY_RUN:-0}"
log(){ printf '[blog-publish %s] %s\n' "$(date -Is)" "$*"; }

# True if the post is math/physics-tagged — the ONLY content Mathstodon (a topic
# instance) should receive; general posts are off-audience there. Scans the
# frontmatter `tags:` block only (sed+grep; no awk — not on the systemd PATH).
is_math(){
  sed -nE '/^tags:[[:space:]]*$/,/^(---|[A-Za-z_])/p' "$1" \
    | grep -qiE '^[[:space:]]*-[[:space:]]*(mathematics|physics|math)([[:space:]]|$)'
}
cd "$BLOG"

# Rolling 7-day window instead of week-boundary math. The old
# `date -d 'monday this week'` resolved to the *upcoming* Monday (on Tue
# 2026-06-23 it returned 2026-06-29), so a post published earlier the same week
# looked "before this week" and the net fired anyway (that's how rowdybot shipped
# a day after fathers_day). "Anything in the last 7 days?" has no weekday edges.
cutoff="$(date -d '-7 days' +%F)"

# 1) Already published recently? (any post dated within the last 7 days)
for f in "$POSTS"/*.md; do
  [ -e "$f" ] || continue
  case "$(basename "$f")" in queued.*) continue ;; esac   # skip gitignored queue-preview mirrors
  d="$(sed -nE 's/^date:[[:space:]]*([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/p' "$f" | head -n1)"
  [ -n "$d" ] || continue
  if [[ "$cutoff" < "$d" ]]; then              # d > cutoff → published within the last 7 days
    log "already published in the last 7 days ($(basename "$f"), $d) — no-op."
    exit 0
  fi
done

# 2) Next ready post = LOWEST ordinal in the queue. Ordinal prefix format:
#       [_]INT[_DEC]_name.md
#    INT          integer part (e.g. 00_rowdybot.md -> 0).
#    leading '_'  NEGATIVE ordinal (_01_x.md -> -1), so it ships before 0. We use
#                 '_' not '-' because '-'-prefixed filenames act like CLI flags.
#    _DEC         optional fractional sub-ordinal, read as digits AFTER a decimal
#                 point — so _2 (.2) sorts AFTER _1999 (.1999). Lets you wedge a
#                 post between 1 and 2 (1_5 -> 1.5), then between those (1_55), ...
#    Everything after the ordinal is the name; the date is stamped at publish time
#    (NN_name.md -> YYYY-MM-DD-name.md). Sort is numeric, so decimals compare right.
next="$(
  for f in "$QUEUE"/*_*.md; do
    [ -e "$f" ] || continue
    b="$(basename "$f")"
    core="$b"; sign=""
    case "$core" in _*) sign="-"; core="${core#_}" ;; esac   # leading '_' => negative
    int="${core%%_*}"; after="${core#*_}"
    case "$int" in ''|*[!0-9]*) continue ;; esac             # integer part must be digits
    # A numeric token immediately after INT (with a name still following it) is the
    # decimal part; otherwise it's the start of the name.
    dec=""
    case "$after" in *_*)
      t1="${after%%_*}"; case "$t1" in ''|*[!0-9]*) ;; *) dec="$t1" ;; esac ;;
    esac
    if [ -n "$dec" ]; then key="${sign}${int}.${dec}"; else key="${sign}${int}"; fi
    printf '%s\t%s\n' "$key" "$f"
  done | sort -k1,1n | head -n1 | cut -f2-
)"
if [ -z "${next:-}" ]; then
  log "queue empty — nothing to publish. (Add NN_name.md files to _queue/scheduled/.)"
  exit 0
fi

# Strip the ordinal prefix: optional '_' (negative), INT, optional '_DEC', then '_'.
slug="$(basename "$next" | sed -E 's/^_?[0-9]+(_[0-9]+)?_//')"
today="$(date +%F)"
dest="$POSTS/${today}-${slug}"

if [ "$DRY" = "1" ]; then
  log "DRY RUN: would publish '${slug%.md}' as ${dest#$BLOG/} (date $today). No changes made."
  exit 0
fi

# 3) Materialize: set date to today, strip queue-only frontmatter lines
sed -E "s/^date:.*/date: ${today}/; /^# QUEUE/d; /^# DRAFT/d" "$next" > "$dest"
rm -f "$next"
log "published ${slug%.md} -> ${dest#$BLOG/}"

# 4) Commit + push
git add "$dest"
if git diff --cached --quiet; then log "nothing staged (?) — done."; exit 0; fi
git commit -q -m "blog: publish ${slug%.md} (weekly safety-net)"
if git remote get-url origin >/dev/null 2>&1; then
  if git push -q 2>/tmp/blog-push.err; then
    log "pushed to origin — GitHub Pages will rebuild."
  else
    log "PUSH FAILED (committed locally): $(cat /tmp/blog-push.err 2>/dev/null)"
  fi
else
  log "no 'origin' remote yet — committed locally only (safe; nothing went public)."
fi

# 5) Optional announce. OFF by default — the weekly drip is silent (publish +
#    push only) unless ANNOUNCE=1 (set in the systemd unit). Best-effort: a
#    syndication failure never fails the publish, since the post is already live.
if [ "${ANNOUNCE:-0}" = "1" ]; then
  base="${SITE_BASE:-https://dmadisetti.github.io/blog}"
  url="${base%/}/${slug%.md}/"
  title="$(sed -nE 's/^title:[[:space:]]*(.+)$/\1/p' "$dest" | head -n1)"
  [ -n "$title" ] || title="${slug%.md}"
  # Bluesky always; add Mathstodon ONLY for math/physics-tagged posts (topic
  # instance etiquette — see is_math / the channel strategy).
  if is_math "$dest"; then target="both"; else target="bluesky"; fi
  if command -v uv >/dev/null 2>&1; then
    if (cd "$BLOG" && uv run --group publish python bin/syndicate.py "$target" "New post: ${title}" --link "$url"); then
      log "announced to ${target} ($url)"
    else
      log "announce failed (post is still live) — syndicate manually if needed."
    fi
  else
    log "ANNOUNCE=1 but 'uv' not on PATH — skipped (the systemd unit provides it)."
  fi
fi
