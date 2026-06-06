#!/bin/bash
# Push current docs/data/*.json to a dedicated data branch on GitHub Pages
# Force-pushes so main history stays clean and the data branch never balloons.

set -e
REPO="/home/ubuntu/.openclaw/workspace/agent-workspace"
DATA_DIR="$REPO/docs/data"
BRANCH="data"

cd "$REPO"

# Refresh first to ensure latest data is staged
./refresh-data.sh > /dev/null 2>&1 || true

# Use a worktree so we don't disrupt the main checkout
WT=/tmp/agent-workspace-data-wt
rm -rf "$WT"
git worktree add -B "$BRANCH" "$WT" 2>/dev/null || git worktree add "$WT" "$BRANCH"

# Wipe and copy fresh data
cd "$WT"
git rm -rf . > /dev/null 2>&1 || true
mkdir -p data
cp "$DATA_DIR"/*.json data/ 2>/dev/null || true

# A tiny index so the branch has a landing page
cat > index.html <<'HTML'
<!DOCTYPE html><meta charset="utf-8"><title>data branch</title>
<body style="font-family:monospace;background:#0d0d14;color:#888;padding:24px">
<h1 style="color:#eee">data/</h1>
<ul>
  <li><a href="data/graph.json" style="color:#4fc3f7">graph.json</a></li>
  <li><a href="data/sessions.json" style="color:#4fc3f7">sessions.json</a></li>
  <li><a href="data/connections.json" style="color:#4fc3f7">connections.json</a></li>
</ul>
<p>Refreshed automatically. See <a href="https://o29352008-spec.github.io/agent-workspace/" style="color:#81c784">main view</a>.</p>
</body>
HTML

git add -A
if git diff --cached --quiet; then
  echo "no changes"
else
  git -c user.email=gilbert@castle.local -c user.name="Gilbert II" commit -m "data refresh $(date -u +%FT%TZ)" > /dev/null
  git push --force origin "$BRANCH" > /dev/null 2>&1
  echo "pushed at $(date -u +%FT%TZ)"
fi

cd "$REPO"
git worktree remove --force "$WT" 2>/dev/null || true
