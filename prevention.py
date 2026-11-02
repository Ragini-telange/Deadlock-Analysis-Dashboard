"""prevention.py - DEADLOCK PREVENTION policies (single-instance resources).

Deadlock needs all 4 Coffman conditions. Prevention removes one of them:
  * Resource ordering    -> removes CIRCULAR WAIT
  * Request-all-upfront  -> removes HOLD AND WAIT
A tiny tick-by-tick simulator compares the policies, so the trade-offs
(lower utilisation, less concurrency) are measured, not just described.
"""
import re


def parse_processes(text):
    """Lines like 'P1: R1:2, R2:3'  ->  {'P1': [('R1',2), ('R2',3)]}"""
    procs, errors = {}, []
    for line in str(text).splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            errors.append(f"Line '{line}' needs the form  P1: R1:2, R2:3")
            continue
        name, rest = line.split(":", 1)
        stages = []
        for part in re.split(r"[,;]\s*", rest.strip()):
            if not part:
                continue
            mt = re.fullmatch(r"(\w+):(\d+)", part.strip())
            if not mt or int(mt.group(2)) <= 0:
                errors.append(f"'{part}' in {name.strip()} must look like R1:2 (resource:time, time >= 1).")
                continue
            stages.append((mt.group(1), int(mt.group(2))))
        if not stages:
            errors.append(f"{name.strip()} has no stages.")
        else:
            procs[name.strip()] = stages
    if not procs and not errors:
        errors.append("Enter at least one process.")
    return procs, errors


def order_violations(procs, order):
    """Where does a process ask for a resource that is LOWER in the global
    order than one it already holds?  (That is what allows circular wait.)"""
    rank = {r: i for i, r in enumerate(order)}
    problems = []
    for p, stages in procs.items():
        seen = []
        for r, _ in stages:
            if r not in rank:
                problems.append(f"{p}: resource {r} is not in the global order.")
                continue
            for h in seen:
                if rank[r] < rank[h]:
                    problems.append(f"{p} requests {r} while already holding {h}, but {r} comes before {h} in the global order.")
            seen.append(r)
    return problems


def simulate(procs, policy, order=None, max_ticks=500):
    """policy: 'none' | 'ordering' | 'upfront'."""
    names = list(procs)
    all_res = sorted({r for s in procs.values() for r, _ in s})
    order = order or all_res
    rank = {r: i for i, r in enumerate(order)}

    stages = {}
    for p in names:
        orig = procs[p]
        if policy == "ordering":
            stages[p] = [({r}, d) for r, d in sorted(orig, key=lambda s: rank.get(s[0], 999))]
        elif policy == "upfront":
            stages[p] = [({r for r, _ in orig}, sum(d for _, d in orig))]
        else:
            stages[p] = [({r}, d) for r, d in orig]

    owner = {}
    st = {p: {"i": 0, "rem": None, "held": set(), "done": False} for p in names}
    finish, wait_ticks, held_ticks = {}, 0, 0
    t = 0
    while t < max_ticks and not all(st[p]["done"] for p in names):
        worked = False
        for p in names:
            s = st[p]
            if s["done"]:
                continue
            res, dur = stages[p][s["i"]]
            if s["rem"] is None:
                if all(owner.get(r, p) == p for r in res):
                    for r in res:
                        owner[r] = p
                        s["held"].add(r)
                    s["rem"] = dur
                else:
                    wait_ticks += 1
            working = s["rem"] is not None
            if working:
                s["rem"] -= 1
                worked = True
            held_ticks += len(s["held"])
            if working and s["rem"] == 0:
                s["i"] += 1
                s["rem"] = None
                if s["i"] == len(stages[p]):
                    s["done"] = True
                    finish[p] = t + 1
                    for r in s["held"]:
                        owner.pop(r, None)
                    s["held"] = set()
        t += 1
        if not worked and not all(st[p]["done"] for p in names):
            stuck = [p for p in names if not st[p]["done"]]
            return {"policy": policy, "deadlock": True, "deadlocked": stuck, "tick": t,
                    "makespan": None, "wait_ticks": wait_ticks, "utilisation": None,
                    "idle_held": None, "finish": finish}
    used = sum(d for p in names for _, d in procs[p])
    return {"policy": policy, "deadlock": False, "deadlocked": [], "tick": t,
            "makespan": t, "wait_ticks": wait_ticks,
            "utilisation": round(used / held_ticks, 2) if held_ticks else 1.0,
            "idle_held": held_ticks - used, "finish": finish}


COFFMAN = {
    "none": {"Mutual exclusion": "present", "Hold and wait": "present", "No preemption": "present", "Circular wait": "possible"},
    "ordering": {"Mutual exclusion": "present", "Hold and wait": "present", "No preemption": "present", "Circular wait": "ELIMINATED"},
    "upfront": {"Mutual exclusion": "present", "Hold and wait": "ELIMINATED", "No preemption": "present", "Circular wait": "possible but harmless"},
}
