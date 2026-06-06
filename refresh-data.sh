#!/bin/bash
# Refresh live session data into the canvas-served directory + docs/data for Pages
DATA_DIR="/home/ubuntu/.openclaw/canvas/documents/agent-workspace/data"
PAGES_DATA="/home/ubuntu/.openclaw/workspace/agent-workspace/docs/data"
mkdir -p "$DATA_DIR" "$PAGES_DATA"

# Build a clean, frontend-friendly graph payload from the session registry + transcripts
python3 <<'PYEOF' > "$DATA_DIR/graph.json.tmp" && mv "$DATA_DIR/graph.json.tmp" "$DATA_DIR/graph.json"
import json, os, time, glob, re
from pathlib import Path

REG = Path('/home/ubuntu/.openclaw/agents/main/sessions/sessions.json')
SESS_DIR = Path('/home/ubuntu/.openclaw/agents/main/sessions')

now_ms = int(time.time() * 1000)

with open(REG) as f:
    registry = json.load(f)

nodes = []
edges = []

# Index sessions by sessionId so spawnedBy lookups can map cleanly
key_to_node = {}

for key, meta in registry.items():
    sid = meta.get('sessionId') or ''
    started = meta.get('sessionStartedAt') or meta.get('updatedAt') or 0
    last = meta.get('lastInteractionAt') or meta.get('updatedAt') or started
    age_ms = max(0, now_ms - last) if last else None

    # Classify
    kind = 'session'
    if key.startswith('agent:main:main'):
        kind = 'main'
    elif ':subagent:' in key:
        kind = 'subagent'
    elif ':direct:' in key:
        kind = 'direct'
    elif ':thread:' in key:
        kind = 'thread'

    short_name = key.split(':')[-1][:14]
    label = 'main' if kind == 'main' else short_name

    node = {
        'id': key,
        'sessionId': sid,
        'label': label,
        'kind': kind,
        'spawnedBy': meta.get('spawnedBy'),
        'spawnDepth': meta.get('spawnDepth', 0),
        'spawnLabel': meta.get('label'),
        'model': meta.get('model'),
        'channel': meta.get('lastChannel') or meta.get('channel'),
        'contextTokens': meta.get('contextTokens', 0),
        'inputTokens': meta.get('inputTokens', 0),
        'outputTokens': meta.get('outputTokens', 0),
        'totalTokens': (meta.get('inputTokens', 0) or 0) + (meta.get('outputTokens', 0) or 0),
        'cost': meta.get('estimatedCostUsd', 0),
        'startedAt': started,
        'lastInteractionAt': last,
        'ageMs': age_ms,
        'endedAt': meta.get('endedAt'),
        'active': age_ms is not None and age_ms < 5 * 60 * 1000 and not meta.get('endedAt'),
    }
    nodes.append(node)
    key_to_node[key] = node

# Build parent->child edges from spawnedBy
for n in nodes:
    parent = n.get('spawnedBy')
    if parent and parent in key_to_node:
        edges.append({
            'from': parent,
            'to': n['id'],
            'kind': 'spawn',
            'label': n.get('spawnLabel') or 'spawn',
            'lastActivity': n.get('lastInteractionAt') or 0,
        })

# Pull last user/assistant message from each session's transcript for previews
def tail_messages(jsonl_path, max_pairs=3):
    if not jsonl_path or not os.path.exists(jsonl_path):
        return []
    try:
        with open(jsonl_path, 'rb') as f:
            try:
                f.seek(-200_000, 2)
            except OSError:
                f.seek(0)
            chunk = f.read().decode('utf-8', errors='replace')
    except Exception:
        return []
    out = []
    for line in chunk.splitlines()[-200:]:
        try:
            evt = json.loads(line)
        except Exception:
            continue
        if evt.get('type') != 'message':
            continue
        msg = evt.get('message') or {}
        role = msg.get('role')
        if role not in ('user', 'assistant'):
            continue
        content = msg.get('content') or []
        text_parts = []
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'text':
                    text_parts.append(c.get('text', ''))
        elif isinstance(content, str):
            text_parts.append(content)
        text = ' '.join(t for t in text_parts if t).strip()
        if not text:
            continue
        # Skip injected runtime/system events
        if text.startswith('[Subagent Context]') or text.startswith('<<<BEGIN'):
            continue
        out.append({
            'role': role,
            'text': text[:240],
            'time': evt.get('timestamp', ''),
        })
    return out[-(max_pairs * 2):]

for n in nodes:
    sf = registry.get(n['id'], {}).get('sessionFile')
    n['recentMessages'] = tail_messages(sf, max_pairs=3)

graph = {
    'generatedAt': now_ms,
    'nodes': nodes,
    'edges': edges,
}

print(json.dumps(graph, indent=2))
PYEOF

# Mirror to GitHub Pages docs/data so a public-deployed view can serve fresh JSON when committed
cp "$DATA_DIR/graph.json" "$PAGES_DATA/graph.json" 2>/dev/null

# Backwards-compat: keep old filenames so the previous frontend doesn't break
python3 <<'PYEOF' 2>/dev/null
import json, os
g = json.load(open('/home/ubuntu/.openclaw/canvas/documents/agent-workspace/data/graph.json'))
sessions = []
for n in g['nodes']:
    sessions.append({
        'key': n['id'],
        'kind': n['kind'],
        'agentId': 'main',
        'model': n.get('model') or '',
        'totalTokens': n.get('totalTokens') or 0,
        'contextTokens': n.get('contextTokens') or 0,
        'updatedAt': n.get('lastInteractionAt') or 0,
        'ageMs': n.get('ageMs') or 0,
    })
out = {'count': len(sessions), 'sessions': sessions}
for d in ['/home/ubuntu/.openclaw/canvas/documents/agent-workspace/data',
          '/home/ubuntu/.openclaw/workspace/agent-workspace/docs/data']:
    os.makedirs(d, exist_ok=True)
    json.dump(out, open(f'{d}/sessions.json', 'w'))
    recent = {n['id'].split(':')[-1]: {
        'user': next((m['text'] for m in n.get('recentMessages',[]) if m['role']=='user'), None),
        'assistant': next((m['text'] for m in n.get('recentMessages',[]) if m['role']=='assistant'), None),
    } for n in g['nodes']}
    json.dump({'recentMessages': recent}, open(f'{d}/connections.json', 'w'))
PYEOF

echo "Refreshed at $(date -u +%FT%TZ)"
