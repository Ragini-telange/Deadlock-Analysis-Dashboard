"""detection.py - DEADLOCK DETECTION and RECOVERY.

Two resource models (always say which one you use!):
  * Single-instance  : every resource has exactly 1 copy.
                       A cycle in the wait-for graph  <=>  deadlock.
  * Multiple-instance: a resource can have several copies.
                       A cycle in the resource-allocation graph is NOT enough,
                       so we use matrix reduction (Work / Allocation / Request).
"""
from banker import less_equal, vec_add


# ---------------------------------------------------------------- multi-instance
def detect_multi(allocation, request, available):
    """Matrix-reduction detection. Returns deadlocked process list + trace."""
    n = len(allocation)
    work = list(available)
    finish = [all(v == 0 for v in allocation[i]) for i in range(n)]
    order, trace = [], []
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and less_equal(request[i], work):
                before = list(work)
                work = vec_add(work, allocation[i])
                finish[i] = True
                order.append(i)
                trace.append({"process": i, "request": list(request[i]),
                              "work_before": before, "work_after": list(work)})
                progress = True
    deadlocked = [i for i in range(n) if not finish[i]]
    return {"deadlock": bool(deadlocked), "deadlocked": deadlocked,
            "finish_order": order, "trace": trace, "final_work": work}


def rag_edges(allocation, request):
    """Resource-allocation graph edges: R->P (held), P->R (waiting)."""
    n, m = len(allocation), len(allocation[0]) if allocation else 0
    edges = []
    for i in range(n):
        for j in range(m):
            if allocation[i][j] > 0:
                edges.append((f"R{j}", f"P{i}", allocation[i][j]))
            if request[i][j] > 0:
                edges.append((f"P{i}", f"R{j}", request[i][j]))
    return edges


def find_cycle(edges):
    """Return one directed cycle (list of nodes) or []. edges: (a, b, ...)"""
    graph = {}
    for e in edges:
        graph.setdefault(e[0], []).append(e[1])
        graph.setdefault(e[1], [])
    color, stack = {}, []

    def dfs(u):
        color[u] = 1
        stack.append(u)
        for v in graph[u]:
            if color.get(v, 0) == 0:
                c = dfs(v)
                if c:
                    return c
            elif color.get(v) == 1:
                return stack[stack.index(v):] + [v]
        stack.pop()
        color[u] = 2
        return []

    for node in list(graph):
        if color.get(node, 0) == 0:
            c = dfs(node)
            if c:
                return c
    return []


def choose_victim(deadlocked, allocation):
    """Recovery rule: terminate the deadlocked process holding the FEWEST
    resources (cheapest to restart). Ties -> lowest process number."""
    return min(deadlocked, key=lambda i: (sum(allocation[i]), i))


def recover_multi(allocation, request, available, victim):
    """Terminate `victim`: it releases everything it holds."""
    released = list(allocation[victim])
    new_alloc = [list(r) for r in allocation]
    new_req = [list(r) for r in request]
    new_alloc[victim] = [0] * len(released)
    new_req[victim] = [0] * len(released)
    new_avail = vec_add(available, released)
    return {"allocation": new_alloc, "request": new_req, "available": new_avail,
            "released": released, "after": detect_multi(new_alloc, new_req, new_avail)}


# ---------------------------------------------------------------- single-instance
def build_wait_for(holds, waits):
    """holds/waits: {process: set(resources)}.  Returns (edges, errors).
    Edge (A, B) means 'A waits for B'."""
    owner, errors = {}, []
    for p, rs in holds.items():
        for r in rs:
            if r in owner and owner[r] != p:
                errors.append(f"Resource {r} is held by both {owner[r]} and {p} - single-instance resources have only one copy.")
            owner[r] = p
    edges = set()
    for p, rs in waits.items():
        for r in rs:
            if r in owner and owner[r] != p:
                edges.add((p, owner[r], r))
    return sorted(edges), errors


def detect_single(holds, waits):
    edges, errors = build_wait_for(holds, waits)
    if errors:
        return {"deadlock": False, "deadlocked": [], "cycle": [], "edges": edges, "errors": errors}
    graph = {}
    for a, b, _ in edges:
        graph.setdefault(a, set()).add(b)

    def reach(start):
        seen, todo = set(), list(graph.get(start, ()))
        while todo:
            x = todo.pop()
            if x not in seen:
                seen.add(x)
                todo.extend(graph.get(x, ()))
        return seen

    deadlocked = sorted(p for p in graph if p in reach(p))
    cycle = find_cycle(edges)
    return {"deadlock": bool(deadlocked), "deadlocked": deadlocked,
            "cycle": cycle, "edges": edges, "errors": []}


def recover_single(holds, waits, victim):
    released = sorted(holds.get(victim, set()))
    new_holds = {p: set(r) for p, r in holds.items() if p != victim}
    new_waits = {p: set(r) for p, r in waits.items() if p != victim}
    return {"holds": new_holds, "waits": new_waits, "released": released,
            "after": detect_single(new_holds, new_waits)}
