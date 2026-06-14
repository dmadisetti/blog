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
POSTS="$BLOG/docs/blog/posts"
DRY="${DRY_RUN:-0}"
log(){ printf '[blog-publish %s] %s\n' "$(date -Is)" "$*"; }
cd "$BLOG"

week_start="$(date -d 'monday this week' +%F)"

# 1) Already published this week? (any post dated >= this Monday)
for f in "$POSTS"/*.md; do
  [ -e "$f" ] || continue
  d="$(sed -nE 's/^date:[[:space:]]*([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/p' "$f" | head -n1)"
  [ -n "$d" ] || continue
  if ! [[ "$d" < "$week_start" ]]; then        # d >= week_start  → published this week
    log "already published this week ($(basename "$f"), $d) — no-op."
    exit 0
  fi
done

# 2) Next ready post = LOWEST ordinal in the queue. Files are NN_name.md where NN is a
#    (possibly negative, possibly unpadded) integer — so -1_jump-the-queue.md ships before
#    00_name.md. We sort numerically on that prefix; the date is stamped at publish time
#    (rename NN_name.md -> YYYY-MM-DD-name.md).
next="$(
  for f in "$QUEUE"/*_*.md; do
    [ -e "$f" ] || continue
    b="$(basename "$f")"; n="${b%%_*}"
    case "$n" in -[0-9]* | [0-9]*) printf '%s\t%s\n' "$n" "$f" ;; esac
  done | sort -k1,1n | head -n1 | cut -f2-
)"
if [ -z "${next:-}" ]; then
  log "queue empty — nothing to publish. (Add NN_name.md files to _queue/scheduled/.)"
  exit 0
fi

slug="$(basename "$next" | sed -E 's/^-?[0-9]+_//')"   # strip the (maybe negative) ordinal
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
