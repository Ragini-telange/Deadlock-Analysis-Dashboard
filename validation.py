"""validation.py - input checks.

Key idea: INVALID input (malformed data) is different from a VALID BOUNDARY case
(unusual but legal data, e.g. zero available) and from a request that simply
cannot be served yet (WAITING).
"""
import re
from numbers import Integral


def is_int(x):
    """True for whole numbers (3, 3.0 yes; 1.5, NaN, 'a' no)."""
    if isinstance(x, bool):
        return False
    if isinstance(x, Integral):
        return True
    try:
        return float(x).is_integer()
    except (TypeError, ValueError, OverflowError):
        return False


def pname(i):
    return f"P{i}"


def rname(j):
    return chr(ord("A") + j)


def validate_state(allocation, maximum, available):
    """Check the matrices. Returns {'errors': [...], 'notes': [...]}.
    errors -> INVALID input.  notes -> valid boundary cases worth mentioning."""
    errors, notes = [], []
    try:
        n = len(allocation)
        m = len(available)
    except TypeError:
        return {"errors": ["Matrices/vectors are missing."], "notes": []}
    if n == 0 or m == 0:
        return {"errors": ["Need at least 1 process and 1 resource type."], "notes": []}
    if len(maximum) != n or any(len(r) != m for r in allocation) or any(len(r) != m for r in maximum):
        return {"errors": ["Shape mismatch: Allocation, Maximum and Available must share the same number of processes and resource types."], "notes": []}

    for name, mat in (("Allocation", allocation), ("Maximum", maximum)):
        for i in range(n):
            for j in range(m):
                v = mat[i][j]
                if not is_int(v):
                    errors.append(f"{name}[{pname(i)}][{rname(j)}] = {v!r} is not a whole number.")
                elif v < 0:
                    errors.append(f"{name}[{pname(i)}][{rname(j)}] = {int(v)} is negative.")
    for j in range(m):
        v = available[j]
        if not is_int(v):
            errors.append(f"Available[{rname(j)}] = {v!r} is not a whole number.")
        elif v < 0:
            errors.append(f"Available[{rname(j)}] = {int(v)} is negative.")
    if errors:
        return {"errors": errors, "notes": []}

    for i in range(n):
        for j in range(m):
            if allocation[i][j] > maximum[i][j]:
                errors.append(f"Allocation exceeds declared maximum: {pname(i)} holds {int(allocation[i][j])} of {rname(j)} but its Maximum is {int(maximum[i][j])}.")
    if errors:
        return {"errors": errors, "notes": []}

    if all(v == 0 for v in available):
        notes.append("Available is all zeros - valid boundary case (nothing free right now).")
    for i in range(n):
        if all(maximum[i][j] == allocation[i][j] for j in range(m)):
            notes.append(f"{pname(i)} has zero remaining Need - valid boundary case (it can finish immediately).")
    return {"errors": errors, "notes": notes}


def parse_process_id(text, n):
    """'P2' or '2' -> 2.  Returns (index, error)."""
    s = str(text).strip().upper()
    mt = re.fullmatch(r"P?(-?\d+)", s)
    if not mt:
        return None, f"Invalid process identifier '{text}'. Use P0..P{n-1} (or just a number)."
    idx = int(mt.group(1))
    if idx < 0 or idx >= n:
        return None, f"Invalid process identifier '{text}': this system has P0..P{n-1} only."
    return idx, None


def parse_vector(text, m):
    """'2,2,1' -> [2,2,1]. Returns (vector, error)."""
    parts = [p for p in re.split(r"[,\s]+", str(text).strip()) if p != ""]
    if len(parts) != m:
        return None, f"Request must have exactly {m} numbers (one per resource type), got {len(parts)}."
    vec = []
    for p in parts:
        try:
            f = float(p)
        except ValueError:
            return None, f"'{p}' is not a number."
        if not f.is_integer():
            return None, f"'{p}' is not a whole number."
        vec.append(int(f))
    if any(v < 0 for v in vec):
        return None, "Request contains a negative number - requests must be 0 or more."
    return vec, None


def parse_request_inputs(pid_text, req_text, n, m):
    """Returns (pid, request, error). Error is a message for INVALID input."""
    pid, err = parse_process_id(pid_text, n)
    if err:
        return None, None, err
    vec, err = parse_vector(req_text, m)
    if err:
        return None, None, err
    return pid, vec, None
