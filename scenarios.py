"""scenarios.py - the group's OWN datasets and the automatic TC1-TC6 runner.
Every 'actual' value is produced by running the real functions."""
from copy import deepcopy
import banker as bk
import detection as dt
import prevention as pv
import validation as val

# 4 processes, 3 resource types (A, B, C).  Totals: A=9, B=5, C=7
MAIN = {
    "allocation": [[1, 0, 2], [2, 1, 0], [3, 0, 1], [1, 1, 1]],
    "maximum":    [[4, 2, 3], [3, 2, 2], [5, 1, 2], [3, 3, 3]],
    "available":  [2, 3, 3],
}
ZERO_NEED = {  # P3 already holds its full maximum
    "allocation": [[1, 0, 2], [2, 1, 0], [3, 0, 1], [3, 3, 3]],
    "maximum":    [[4, 2, 3], [3, 2, 2], [5, 1, 2], [3, 3, 3]],
    "available":  [2, 3, 3],
}
DET_DEADLOCK = {
    "allocation": [[1, 0, 1], [0, 1, 1], [1, 1, 0], [0, 0, 1]],
    "request":    [[0, 1, 0], [1, 0, 0], [0, 0, 2], [0, 0, 0]],
    "available":  [0, 0, 0],
}
DET_CYCLE_NO_DEADLOCK = {
    "allocation": [[1, 0], [0, 1], [1, 0]],
    "request":    [[0, 1], [1, 0], [0, 0]],
    "available":  [0, 0],
}
SINGLE_DEADLOCK = {"holds": {"P1": {"R1"}, "P2": {"R2"}, "P3": {"R3"}},
                   "waits": {"P1": {"R2"}, "P2": {"R1"}, "P3": set()}}
PREVENTION_TEXT = "P1: R1:2, R2:2\nP2: R2:2, R1:2\nP3: R3:3"
PREVENTION_ORDER = ["R1", "R2", "R3"]


def _fmt(seq):
    return " -> ".join(f"P{i}" for i in seq)


def tc1():
    d = MAIN
    need = bk.calculate_need(d["maximum"], d["allocation"])
    r = bk.safety_check(d["allocation"], need, d["available"])
    actual = f"SAFE. Safe sequence: {_fmt(r['sequence'])}" if r["safe"] else f"UNSAFE. Stuck: {r['stuck']}"
    return actual, r["safe"] and r["sequence"] == [1, 0, 2, 3]


def tc2():
    d = MAIN
    r = bk.handle_request(0, [3, 0, 0], d["allocation"], d["maximum"], d["available"])
    unchanged = r["new_allocation"] is None and d["available"] == [2, 3, 3]
    return f"{r['status']} (state unchanged: {unchanged})", r["status"] == "WAITING" and unchanged


def tc3():
    d = MAIN
    r = bk.handle_request(0, [2, 2, 1], d["allocation"], d["maximum"], d["available"])
    sim = r["simulated"]
    unchanged = r["new_allocation"] is None
    actual = (f"{r['status']}; pretend Available={sim['available']}; "
              f"no safe sequence (stuck: {['P%d' % i for i in r['safety']['stuck']]}); original state kept: {unchanged}")
    return actual, r["status"] == "DENIED_UNSAFE" and unchanged


def tc4():
    d = DET_DEADLOCK
    det = dt.detect_multi(d["allocation"], d["request"], d["available"])
    victim = dt.choose_victim(det["deadlocked"], d["allocation"])
    rec = dt.recover_multi(d["allocation"], d["request"], d["available"], victim)
    s = dt.detect_single(SINGLE_DEADLOCK["holds"], SINGLE_DEADLOCK["waits"])
    actual = (f"Multi-instance: DEADLOCKED {['P%d' % i for i in det['deadlocked']]}; "
              f"Single-instance: cycle {' -> '.join(s['cycle'])}; "
              f"recovery: terminate P{victim}, released {rec['released']}, deadlock after = {rec['after']['deadlock']}")
    ok = det["deadlocked"] == [0, 1, 2] and s["deadlock"] and not rec["after"]["deadlock"]
    return actual, ok


def tc5():
    procs, _ = pv.parse_processes(PREVENTION_TEXT)
    res = {p: pv.simulate(procs, p, PREVENTION_ORDER) for p in ("none", "ordering", "upfront")}
    actual = (f"Original: deadlock={res['none']['deadlock']}; "
              f"Ordering: deadlock={res['ordering']['deadlock']} (makespan {res['ordering']['makespan']}); "
              f"All-upfront: deadlock={res['upfront']['deadlock']} (makespan {res['upfront']['makespan']})")
    ok = res["none"]["deadlock"] and not res["ordering"]["deadlock"] and not res["upfront"]["deadlock"]
    return actual, ok


def tc6_cases():
    """List of boundary / invalid checks with their real outcomes."""
    cases = []
    m = MAIN

    def add(name, expected, actual, detail):
        cases.append({"case": name, "expected": expected, "actual": actual, "detail": detail,
                      "ok": expected == actual})

    # zero available
    z = val.validate_state(m["allocation"], m["maximum"], [0, 0, 0])
    need = bk.calculate_need(m["maximum"], m["allocation"])
    s = bk.safety_check(m["allocation"], need, [0, 0, 0])
    add("Zero Available [0,0,0]", "VALID BOUNDARY", "VALID BOUNDARY" if not z["errors"] else "INVALID",
        f"Accepted. Safety verdict: {'SAFE' if s['safe'] else 'UNSAFE'} (a verdict, not an input error).")
    # zero need
    zn = ZERO_NEED
    z = val.validate_state(zn["allocation"], zn["maximum"], zn["available"])
    need = bk.calculate_need(zn["maximum"], zn["allocation"])
    s = bk.safety_check(zn["allocation"], need, zn["available"])
    add("Process with zero Need (P3)", "VALID BOUNDARY", "VALID BOUNDARY" if not z["errors"] else "INVALID",
        f"Accepted. P3 can finish at once; sequence {_fmt(s['sequence'])}.")
    # request invalid pid
    pid, vec, err = val.parse_request_inputs("P9", "1,0,0", 4, 3)
    add("Invalid process id P9", "INVALID", "INVALID" if err else "VALID", err or "")
    # negative
    pid, vec, err = val.parse_request_inputs("P1", "-1,0,0", 4, 3)
    add("Negative request [-1,0,0]", "INVALID", "INVALID" if err else "VALID", err or "")
    # allocation > max
    bad = deepcopy(m["allocation"])
    bad[1][0] = 9
    z = val.validate_state(bad, m["maximum"], m["available"])
    add("Allocation exceeds Maximum (P1 holds 9 of A)", "INVALID", "INVALID" if z["errors"] else "VALID",
        z["errors"][0] if z["errors"] else "")
    # request > need
    r = bk.handle_request(1, [2, 0, 0], m["allocation"], m["maximum"], m["available"])
    add("Request exceeds Need (P1 asks [2,0,0], Need [1,1,2])", "INVALID", r["status"], r["message"])
    # zero request
    r = bk.handle_request(1, [0, 0, 0], m["allocation"], m["maximum"], m["available"])
    add("All-zero request [0,0,0]", "VALID BOUNDARY", "VALID BOUNDARY" if r["status"] == "GRANTED" else r["status"],
        "A harmless no-op: accepted and safe.")
    return cases


def tc6():
    cases = tc6_cases()
    ok = all(c["ok"] for c in cases)
    valid = sum(1 for c in cases if c["actual"] == "VALID BOUNDARY")
    inval = sum(1 for c in cases if c["actual"] == "INVALID")
    return f"{valid} valid boundary cases accepted; {inval} invalid inputs rejected with messages ({'all as expected' if ok else 'MISMATCH'})", ok


def run_all():
    rows = []
    spec = [
        ("TC1", "Safe state", tc1, "Safe sequence found"),
        ("TC2", "Request exceeds Available", tc2, "Request not granted immediately (waiting)"),
        ("TC3", "Request makes state unsafe", tc3, "Request denied; state unchanged"),
        ("TC4", "Deadlocked scenario", tc4, "Deadlock identified by the selected detection method"),
        ("TC5", "Prevention policy applied", tc5, "Selected deadlock condition eliminated"),
        ("TC6", "Boundary and invalid inputs", tc6, "Correct handling or validation message"),
    ]
    for tid, cond, fn, expected in spec:
        actual, ok = fn()
        rows.append({"Test Case": tid, "System Condition": cond, "Actual Result": actual,
                     "Expected Result": expected, "Match": "PASS" if ok else "FAIL"})
    return rows
