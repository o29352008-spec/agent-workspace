#!/usr/bin/env python3
"""
Tick the Castle AI startup simulation forward by one step.

Reads:  simulation/state.json, simulation/roles.json
Writes: simulation/state.json (advanced), simulation/events.jsonl (append),
        docs/data/sim.json (frontend payload)

Each tick:
  - Roll a market event per market (weighted random)
  - Update demand/competition/trend per market
  - Compute revenue from products + employee multipliers
  - Pay salaries (drain treasury)
  - Update morale based on cash runway and recent firings
  - Calculate runway/valuation
  - Append a structured event log entry
"""
import json
import os
import random
import time
from pathlib import Path

ROOT = Path(__file__).parent
STATE_PATH = ROOT / "state.json"
ROLES_PATH = ROOT / "roles.json"
EVENTS_PATH = ROOT / "events.jsonl"
SIM_OUT = ROOT.parent / "docs" / "data" / "sim.json"
CANVAS_OUT = Path("/home/ubuntu/.openclaw/canvas/documents/agent-workspace/data/sim.json")


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def append_event(event):
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENTS_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")


def weighted_choice(events):
    total = sum(e.get("weight", 1) for e in events)
    r = random.uniform(0, total)
    acc = 0
    for e in events:
        acc += e.get("weight", 1)
        if r <= acc:
            return e
    return events[-1]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def tick():
    state = load_json(STATE_PATH)
    roles = load_json(ROLES_PATH)
    if not state or not roles:
        print("missing state or roles")
        return

    now_ms = int(time.time() * 1000)
    state["tick"] = state.get("tick", 0) + 1
    state["lastTickAt"] = now_ms
    log_entries = []

    # Roll market events
    for mkt_id, mkt in state.get("markets", {}).items():
        evt = weighted_choice(roles["marketEvents"])
        mkt["demand"] = clamp(mkt["demand"] + evt.get("demandDelta", 0) + random.randint(-3, 3), 0, 100)
        mkt["competition"] = clamp(mkt["competition"] + evt.get("competitionDelta", 0) + random.randint(-2, 2), 0, 100)
        mkt["trend"] = clamp(mkt["trend"] + evt.get("trendDelta", 0), -50, 50)
        mkt["trend"] *= 0.9  # decay
        mkt["lastEvent"] = {"type": evt["type"], "label": evt["label"], "tick": state["tick"]}
        if evt["type"] != "neutral":
            log_entries.append({
                "ts": now_ms, "tick": state["tick"], "kind": "market",
                "market": mkt_id, "event": evt["type"], "label": evt["label"]
            })

    # Tally employee effects
    employees = state.get("employees", [])
    quality_boost = 0
    demand_boost = 0
    revenue_mult = 1.0
    burn_mult = 1.0
    salary_total = 0

    for emp in employees:
        role_def = roles["roles"].get(emp.get("role", ""), {})
        salary_total += role_def.get("salaryPerTick", 0)
        quality_boost += role_def.get("qualityContribution", 0)
        demand_boost += role_def.get("demandBoost", 0)
        revenue_mult *= role_def.get("revenueBoost", 1.0)
        burn_mult *= role_def.get("burnReduction", 1.0)

    # Apply employee effects to products + markets
    for product in state.get("products", []):
        product["quality"] = clamp(product.get("quality", 0) + quality_boost * 0.5, 0, 100)
        # Stage progression based on quality
        q = product["quality"]
        product["stage"] = (
            "idea" if q < 20 else
            "alpha" if q < 40 else
            "beta" if q < 65 else
            "launched" if q < 85 else
            "scaling"
        )

    for mkt in state["markets"].values():
        mkt["demand"] = clamp(mkt["demand"] + demand_boost, 0, 100)

    # Revenue: product quality * primary market demand * revenue multiplier
    primary_market = state["markets"].get("ai-saas", {})
    market_factor = (primary_market.get("demand", 0) / 100) * (1 - primary_market.get("competition", 0) / 200)
    base_revenue = sum(p.get("quality", 0) for p in state["products"]) * 8 * market_factor
    revenue = base_revenue * revenue_mult

    # Burn: salaries + base
    base_burn = 300
    burn = (base_burn + salary_total) * burn_mult

    # Update treasury
    company = state["company"]
    company["treasury"] = round(company["treasury"] + revenue - burn)
    company["burnRate"] = round(burn)
    company["revenuePerTick"] = round(revenue)
    company["valuation"] = max(0, round(company["treasury"] + (revenue - burn) * 50 + sum(p.get("quality", 0) for p in state["products"]) * 200))

    # Morale: cash runway sensitivity
    runway_ticks = (company["treasury"] / max(1, burn - revenue)) if burn > revenue else 999
    if runway_ticks < 5:
        company["morale"] = clamp(company["morale"] - 5, 0, 100)
    elif runway_ticks > 30 and revenue > burn:
        company["morale"] = clamp(company["morale"] + 2, 0, 100)
    else:
        company["morale"] = clamp(company["morale"] + random.randint(-1, 1), 0, 100)

    # Log financials
    log_entries.append({
        "ts": now_ms, "tick": state["tick"], "kind": "financial",
        "treasury": company["treasury"], "revenue": company["revenuePerTick"],
        "burn": company["burnRate"], "valuation": company["valuation"],
        "morale": company["morale"], "runwayTicks": round(runway_ticks, 1) if runway_ticks < 999 else None,
        "employees": len(employees)
    })

    # Bankruptcy
    if company["treasury"] < 0:
        log_entries.append({
            "ts": now_ms, "tick": state["tick"], "kind": "alert",
            "level": "critical", "message": "BANKRUPT — treasury exhausted. CEO must act."
        })
        company["morale"] = 0

    # Trim in-state log to last 30 entries (full history is in events.jsonl)
    state["log"] = (state.get("log", []) + log_entries)[-30:]

    # Persist
    save_json(STATE_PATH, state)
    for entry in log_entries:
        append_event(entry)

    # Frontend payload (lighter, includes derived fields)
    sim_payload = {
        "generatedAt": now_ms,
        "tick": state["tick"],
        "company": company,
        "products": state["products"],
        "markets": state["markets"],
        "employees": employees,
        "log": state["log"],
        "runwayTicks": round(runway_ticks, 1) if runway_ticks < 999 else None,
    }
    save_json(SIM_OUT, sim_payload)
    try:
        save_json(CANVAS_OUT, sim_payload)
    except Exception:
        pass

    print(f"Tick {state['tick']}: treasury=${company['treasury']:,} rev=${company['revenuePerTick']} burn=${company['burnRate']} morale={company['morale']} emp={len(employees)}")


if __name__ == "__main__":
    tick()
