#!/usr/bin/env python3
"""
status.py — print a compact CEO-readable summary of company state.

Used by Gilbert (the CEO agent) to know what's going on before deciding
whether to hire, fire, ship product, or sweat the runway.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
STATE = ROOT / "state.json"


def main():
    s = json.load(open(STATE))
    c = s["company"]
    runway_burn = c["burnRate"] - c["revenuePerTick"]
    runway = (c["treasury"] / runway_burn) if runway_burn > 0 else None

    print(f"=== {c['name']} (tick {s['tick']}) ===")
    print(f"Treasury    : ${c['treasury']:,}")
    print(f"Revenue/tick: ${c['revenuePerTick']:,}")
    print(f"Burn/tick   : ${c['burnRate']:,}")
    print(f"Net/tick    : ${c['revenuePerTick'] - c['burnRate']:+,}")
    print(f"Runway      : {f'{runway:.0f} ticks' if runway else 'profitable'}")
    print(f"Valuation   : ${c['valuation']:,}")
    print(f"Morale      : {c['morale']}/100")

    print(f"\n--- Employees ({len(s['employees'])}) ---")
    if not s["employees"]:
        print("  (none — solo founder mode)")
    for e in s["employees"]:
        print(f"  {e['icon']} {e['id']:18} {e['title']:14} ${e['salary']}/tick  task: {e.get('task','')[:50]}")

    print(f"\n--- Products ---")
    for p in s["products"]:
        print(f"  {p['name']:18} stage={p['stage']:10} quality={p['quality']:.0f}/100")

    print(f"\n--- Markets ---")
    for mid, m in s["markets"].items():
        evt = m.get("lastEvent", {}) or {}
        print(f"  {mid:11} demand={m['demand']:.0f} competition={m['competition']:.0f} trend={m['trend']:+.1f}  last: {evt.get('label','')}")

    print(f"\n--- Recent log ---")
    for entry in s.get("log", [])[-8:]:
        kind = entry.get("kind", "?")
        if kind == "market":
            print(f"  T{entry['tick']:3}  market   {entry['market']}: {entry['label']}")
        elif kind == "hire":
            print(f"  T{entry['tick']:3}  HIRE     {entry['name']} ({entry['role']})")
        elif kind == "fire":
            print(f"  T{entry['tick']:3}  FIRE     {entry['name']} ({entry['role']})  {entry.get('reason','')}")
        elif kind == "alert":
            print(f"  T{entry['tick']:3}  ALERT    {entry.get('message','')}")
        elif kind == "financial":
            print(f"  T{entry['tick']:3}  fin      tres=${entry['treasury']:,} rev=${entry['revenue']} burn=${entry['burn']}")


if __name__ == "__main__":
    main()
