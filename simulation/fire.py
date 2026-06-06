#!/usr/bin/env python3
"""
fire.py — removes an employee from the simulation state.

Usage:
  python3 fire.py <employee-id> [--reason "performance"]
"""
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
STATE = ROOT / "state.json"
EVENTS = ROOT / "events.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("employee_id")
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    state = json.load(open(STATE))
    emp = next((e for e in state["employees"] if e["id"] == args.employee_id), None)
    if not emp:
        print(f"unknown employee: {args.employee_id}. current: {[e['id'] for e in state['employees']]}", file=sys.stderr)
        sys.exit(1)

    now = int(time.time() * 1000)
    state["employees"] = [e for e in state["employees"] if e["id"] != args.employee_id]
    # Morale hit on firing
    state["company"]["morale"] = max(0, state["company"]["morale"] - 5)

    evt = {"ts": now, "tick": state["tick"], "kind": "fire", "name": args.employee_id, "role": emp["role"], "reason": args.reason}
    state["log"] = (state.get("log", []) + [evt])[-30:]
    with open(EVENTS, "a") as f:
        f.write(json.dumps(evt) + "\n")

    json.dump(state, open(STATE, "w"), indent=2)
    print(json.dumps({"ok": True, "fired": emp, "remaining": len(state["employees"])}))


if __name__ == "__main__":
    main()
