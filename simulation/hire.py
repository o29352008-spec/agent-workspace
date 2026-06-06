#!/usr/bin/env python3
"""
hire.py — adds an employee to the simulation state.

Usage:
  python3 hire.py <role> [--name NAME] [--task "starting task"] [--session-key KEY]

The CEO (Gilbert) calls this when it decides to spawn a new sub-agent. After running
this, the CEO should call sessions_spawn with the role's prompt template to actually
bring the agent online.
"""
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
STATE = ROOT / "state.json"
ROLES = ROOT / "roles.json"
EVENTS = ROOT / "events.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role")
    ap.add_argument("--name", default=None)
    ap.add_argument("--task", default="")
    ap.add_argument("--session-key", default=None)
    args = ap.parse_args()

    roles = json.load(open(ROLES))
    if args.role not in roles["roles"]:
        print(f"unknown role: {args.role}. options: {list(roles['roles'].keys())}", file=sys.stderr)
        sys.exit(1)

    state = json.load(open(STATE))
    role_def = roles["roles"][args.role]
    now = int(time.time() * 1000)

    name = args.name or f"{args.role}-{len(state['employees']) + 1}"
    emp = {
        "id": name,
        "role": args.role,
        "title": role_def["title"],
        "salary": role_def["salaryPerTick"],
        "icon": role_def["icon"],
        "color": role_def["color"],
        "task": args.task,
        "sessionKey": args.session_key,
        "hiredAt": now,
        "hiredAtTick": state["tick"],
        "status": "active"
    }
    state["employees"].append(emp)

    # Log
    evt = {"ts": now, "tick": state["tick"], "kind": "hire", "role": args.role, "name": name, "task": args.task}
    state["log"] = (state.get("log", []) + [evt])[-30:]
    with open(EVENTS, "a") as f:
        f.write(json.dumps(evt) + "\n")

    json.dump(state, open(STATE, "w"), indent=2)
    print(json.dumps({"ok": True, "employee": emp, "state_summary": summarize(state)}))


def summarize(state):
    c = state["company"]
    return {
        "tick": state["tick"],
        "treasury": c["treasury"],
        "burn": c["burnRate"],
        "revenue": c["revenuePerTick"],
        "morale": c["morale"],
        "employees": len(state["employees"]),
        "markets": {k: {"demand": v["demand"], "competition": v["competition"]} for k, v in state["markets"].items()}
    }


if __name__ == "__main__":
    main()
