#!/usr/bin/env bash
# Cloud-session preflight for the episode pipeline. Run from anywhere in the repo.
#   source templates/session-preflight.sh
set -u

cd "$(git rev-parse --show-toplevel)" || return 1

# 1. Output goes into the repo — the ONLY thing that survives the container.
export DECK_OUT=output
echo "DECK_OUT=$DECK_OUT"

# 2. Are the upstreams reachable? If this fails, it's the network policy
#    (needs Full, or an allowlist with sec.gov / api.nasdaq.com /
#    query1.finance.yahoo.com / trends.google.com), not a broken service.
echo "--- network check ---"
if python3 marketdata.py quote NVDA >/dev/null 2>&1; then
  echo "OK  upstreams reachable"
else
  echo "FAIL  set the environment's network policy to Full and retry"
fi

# 3. What already exists
echo "--- covered so far ---"
ls decks/ episodes/ 2>/dev/null
echo "--- built episodes ---"
ls output/ 2>/dev/null
echo "--- where we left off ---"
git log --oneline -5
git status --short
