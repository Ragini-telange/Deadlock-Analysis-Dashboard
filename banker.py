"""banker.py - DEADLOCK AVOIDANCE (Banker's Algorithm).

Banker's does NOT detect an existing deadlock. It only decides whether granting
a request keeps the system in a SAFE state.
"""
from copy import deepcopy


def calculate_need(maximum, allocation):
    """Need = Maximum - Allocation (computed automatically)."""
    return [[mx - al for mx, al in zip(mr, ar)] for mr, ar in zip(maximum, allocation)]


def less_equal(a, b):
    return all(x <= y for x, y in zip(a, b))


def vec_add(a, b):
    return [x + y for x, y in zip(a, b)]


def vec_sub(a, b):
    return [x - y for x, y in zip(a, b)]


def safety_check(allocation, need, available):
    """Banker's safety algorithm. Returns a dict with the safe flag, the safe
    sequence, and a step-by-step trace of the Work vector."""
    n = len(allocation)
    work = list(available)
    finish = [False] * n
    sequence, trace = [], []
    while len(sequence) < n:
        picked = None
        for i in range(n):
            if not finish[i] and less_equal(need[i], work):
                picked = i
                break
        if picked is None:
            break
        before = list(work)
        work = vec_add(work, allocation[picked])      # process finishes, returns its resources
        finish[picked] = True
        sequence.append(picked)
        trace.append({"step": len(sequence), "process": picked,
                      "need": list(need[picked]), "work_before": before,
                      "work_after": list(work)})
    return {"safe": len(sequence) == n, "sequence": sequence, "trace": trace,
            "stuck": [i for i in range(n) if not finish[i]], "final_work": work}


def _result(status, message, checks, **extra):
    r = {"status": status, "message": message, "checks": checks,
         "new_allocation": None, "new_available": None,
         "simulated": None, "safety": None}
    r.update(extra)
    return r


def invalid_result(message):
    return _result("INVALID", message, [{"label": "Input is well-formed", "ok": False}])


def handle_request(pid, request, allocation, maximum, available):
    """Resource-request algorithm. Status is one of:
    GRANTED | WAITING | DENIED_UNSAFE | INVALID.
    The original state is never modified; the caller commits new_* if it wants."""
    n, m = len(allocation), len(available)
    checks = []

    ok_pid = isinstance(pid, int) and not isinstance(pid, bool) and 0 <= pid < n
    ok_vec = (isinstance(request, (list, tuple)) and len(request) == m
              and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in request))
    checks.append({"label": "Process id and request vector are valid", "ok": ok_pid and ok_vec})
    if not (ok_pid and ok_vec):
        return _result("INVALID", "Invalid input: bad process id, wrong length, negative or non-integer request.", checks)

    need = calculate_need(maximum, allocation)

    within_need = less_equal(request, need[pid])
    checks.append({"label": f"Request {list(request)} <= Need {need[pid]}", "ok": within_need})
    if not within_need:
        return _result("INVALID", f"P{pid} asked for more than its remaining Need - it would exceed its declared maximum claim.", checks)

    within_avail = less_equal(request, available)
    checks.append({"label": f"Request {list(request)} <= Available {list(available)}", "ok": within_avail})
    if not within_avail:
        return _result("WAITING", f"P{pid} must wait: the request is legal (within Need) but not enough resources are free right now. Nothing was changed.", checks)

    # Pretend to allocate, then run the safety algorithm on the pretend state.
    new_alloc = deepcopy(allocation)
    new_alloc[pid] = vec_add(new_alloc[pid], request)
    new_avail = vec_sub(available, request)
    new_need = calculate_need(maximum, new_alloc)
    safety = safety_check(new_alloc, new_need, new_avail)
    sim = {"allocation": new_alloc, "available": new_avail, "need": new_need}
    checks.append({"label": "Pretend-allocation leaves the system SAFE", "ok": safety["safe"]})

    if safety["safe"]:
        return _result("GRANTED", f"Request granted: a safe sequence still exists ({' -> '.join('P%d' % i for i in safety['sequence'])}).",
                       checks, new_allocation=new_alloc, new_available=new_avail, simulated=sim, safety=safety)
    return _result("DENIED_UNSAFE", "Request denied: granting it would leave no safe sequence. The pretend allocation was rolled back and the original state is kept.",
                   checks, simulated=sim, safety=safety)
