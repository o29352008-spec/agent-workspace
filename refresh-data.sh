#!/bin/bash
# Refresh live session data into the canvas-served directory
DATA_DIR="/home/ubuntu/.openclaw/canvas/documents/agent-workspace/data"
mkdir -p "$DATA_DIR"

# Fetch sessions and save as static JSON
openclaw sessions --all-agents --active 1440 --json 2>/dev/null > "$DATA_DIR/sessions.json.tmp" && \
  mv "$DATA_DIR/sessions.json.tmp" "$DATA_DIR/sessions.json"

# Build edges from session transcripts (parent-child relationships from sessions_spawn)
python3 <<'PYEOF' > "$DATA_DIR/connections.json.tmp" && mv "$DATA_DIR/connections.json.tmp" "$DATA_DIR/connections.json"
import json, os, glob, re
from pathlib import Path

connections = []
recent_messages = {}

# Scan transcripts for sub-agent spawns and recent activity
sessions_dir = Path('/home/ubuntu/.openclaw/agents/main/sessions')
for jsonl in sessions_dir.glob('*.jsonl'):
    session_id = jsonl.stem
    try:
        with open(jsonl, 'r') as f:
            lines = f.readlines()[-50:]  # last 50 events
        last_user_msg = None
        last_assistant_msg = None
        for line in lines:
            try:
                evt = json.loads(line)
                if evt.get('role') == 'user':
                    content = evt.get('content', '')
                    if isinstance(content, list):
                        content = ' '.join(c.get('text','') for c in content if isinstance(c, dict))
                    last_user_msg = str(content)[:200]
                elif evt.get('role') == 'assistant':
                    content = evt.get('content', '')
                    if isinstance(content, list):
                        content = ' '.join(c.get('text','') for c in content if isinstance(c, dict))
                    last_assistant_msg = str(content)[:200]
            except:
                pass
        recent_messages[session_id] = {
            'user': last_user_msg,
            'assistant': last_assistant_msg,
            'updated': os.path.getmtime(jsonl) * 1000
        }
    except Exception as e:
        pass

print(json.dumps({'recentMessages': recent_messages}))
PYEOF

echo "Refreshed at $(date)"
