# Agent Workspace

A visual graph of OpenClaw agent sessions and their connections.

🌐 **Live demo:** https://o29352008-spec.github.io/agent-workspace/

## What it does

- Visualizes AI agents as nodes in a force-directed graph
- Shows connections between agents (conversations, sub-agent spawns)
- Animated pulses traveling along active connections
- Click connections to see conversation messages
- Click agents to see model, token usage, and session details
- Drag nodes to rearrange

## Run locally

The standalone version (`docs/index.html`) works as a single file — just open it in a browser.

For live OpenClaw session data, run the server:

```bash
node server.js
```

Then open http://localhost:8090. Requires the OpenClaw CLI on PATH for live data.

## Architecture

- `docs/index.html` — Standalone visualization (GitHub Pages serves from here)
- `server.js` — Optional Node server that polls OpenClaw CLI for live session data
- `refresh-data.sh` — Shell script that writes session data to JSON files for static hosting

Built with vanilla JS + Canvas API. No frameworks, no build step.
