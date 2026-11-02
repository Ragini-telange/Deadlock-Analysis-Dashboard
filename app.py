"""app.py - Streamlit dashboard: 'Deadlock Control Room'.
Run with:  streamlit run app.py
The UI only displays results; all algorithms live in banker.py, detection.py,
prevention.py and validation.py."""
import pandas as pd
import streamlit as st

import banker as bk
import detection as dt
import prevention as pv
import scenarios as sc
import validation as val
import ui

st.set_page_config(page_title="Deadlock Control Room", layout="wide")
ui.inject_css()
STATES = ui.STATES
verdict = ui.verdict


def set_status(key, text):
    st.session_state["status"] = (key, text)


def lamp_panel():
    key, text = st.session_state.get("status", (None, "Nothing evaluated yet. Run a scenario and the signal for its result lights up."))
    ui.gantry(key, text)


# ------------------------------------------------------------------ helpers
def rnames(m):
    return [val.rname(j) for j in range(m)]


def pnames(n):
    return [val.pname(i) for i in range(n)]


def to_df(mat, m=None):
    m = m or len(mat[0])
    return pd.DataFrame(mat, index=pnames(len(mat)), columns=rnames(m))


def vec_df(vec):
    return pd.DataFrame([vec], index=["Available"], columns=rnames(len(vec)))


def fmt(v):
    return "[" + ", ".join(str(int(x)) for x in v) + "]"


def load_system(d):
    st.session_state["sys_ver"] = st.session_state.get("sys_ver", 0) + 1
    st.session_state["base_alloc"] = to_df(d["allocation"])
    st.session_state["base_max"] = to_df(d["maximum"])
    st.session_state["base_avail"] = vec_df(d["available"])
    st.session_state["alloc_val"] = st.session_state["base_alloc"]
    st.session_state["max_val"] = st.session_state["base_max"]
    st.session_state["avail_val"] = st.session_state["base_avail"]
    st.session_state.pop("last_request", None)


if "base_alloc" not in st.session_state:
    load_system(sc.MAIN)


def get_system():
    a = st.session_state["alloc_val"].values.tolist()
    mx = st.session_state["max_val"].values.tolist()
    av = st.session_state["avail_val"].values.tolist()[0]
    return a, mx, av


def valid_system_or_stop():
    a, mx, av = get_system()
    check = val.validate_state(a, mx, av)
    if check["errors"]:
        set_status("INVALID", check["errors"][0])
        lamp_panel()
        for e in check["errors"]:
            st.error(e)
        st.info("Fix the numbers on the System Setup page first.")
        st.stop()
    return [[int(x) for x in r] for r in a], [[int(x) for x in r] for r in mx], [int(x) for x in av], check["notes"]


# ------------------------------------------------------------------ pages
def page_concepts():
    st.markdown('<div class="hero"><h1>Deadlock Control Room</h1>'
                '<p>A deadlock is a junction where every train waits for a track another one holds. '
                'This dashboard lets you prevent it, avoid it, detect it and recover from it, and shows the result on the signal gantry.</p></div>',
                unsafe_allow_html=True)
    lamp_panel()

    st.subheader("Four ways an OS deals with deadlock")
    c = st.columns(4)
    with c[0]:
        ui.panel("Prevention", "Make one Coffman condition impossible by policy (resource ordering, request all upfront). Cost: lower utilisation, less concurrency.", "#6B4FA0")
    with c[1]:
        ui.panel("Avoidance", "Banker's Algorithm. Needs each process's maximum claim; grants a request only if a safe sequence still exists. It does not find existing deadlocks.", "#1E8E5A")
    with c[2]:
        ui.panel("Detection", "Let deadlock happen, then look for it: wait-for-graph cycle (single instance) or matrix reduction (multiple instances).", "#D1342F")
    with c[3]:
        ui.panel("Recovery", "Terminate a victim or preempt resources so the rest can finish.", "#2F6FB5")

    st.subheader("Unsafe is not deadlocked")
    ui.unsafe_vs_deadlock()
    st.write("Every deadlocked state is unsafe, but an unsafe state may never deadlock. Banker's denies requests that lead to "
             "unsafe states; detection is a different tool that looks for processes that are already stuck.")

    st.subheader("The five signals")
    st.table(pd.DataFrame([
        ("Safe", "A safe sequence exists, or a granted request keeps the state safe"),
        ("Unsafe", "No safe sequence; the request that caused it is denied and the old state restored"),
        ("Waiting / deferred", "Request is within Need but exceeds Available. Legal, just not now"),
        ("Deadlocked", "Detection found processes that can never finish"),
        ("Invalid input", "Malformed data: bad id, negative number, Allocation > Maximum, request > Need"),
    ], columns=["Signal", "Meaning"]).set_index("Signal"))


def show_tables(A, MX, AV):
    """Allocation / Maximum / Need side by side, then the Available vector and bars."""
    need = bk.calculate_need(MX, A)
    c = st.columns(3)
    c[0].markdown("**1. Allocation matrix**"); c[0].dataframe(to_df(A))
    c[1].markdown("**2. Maximum matrix**"); c[1].dataframe(to_df(MX))
    c[2].markdown("**3. Need matrix** (auto: Max - Alloc)"); c[2].dataframe(to_df(need))
    st.markdown("**Current Available vector**")
    st.dataframe(vec_df(AV))
    total = [sum(A[i][j] for i in range(len(A))) + AV[j] for j in range(len(AV))]
    ui.resource_bars(rnames(len(AV)), AV, total, "Free resources right now (free / total)")


def show_safety(r):
    """Banker's safety check result: banner, finished-order track, step-by-step trace."""
    st.markdown("#### Banker's Algorithm: safety check")
    if r["safe"]:
        verdict("SAFE", "Safe sequence found: " + " -> ".join(f"P{i}" for i in r["sequence"]))
    else:
        verdict("UNSAFE", "No complete safe sequence. Cannot finish: " + ", ".join(f"P{i}" for i in r["stuck"]))
    ui.track(r["sequence"], len(r["sequence"]), r["stuck"])
    if r["trace"]:
        st.markdown("**Step-by-step execution trace**")
        rows = [{"Step": t["step"], "Process picked": f"P{t['process']}", "Its Need": fmt(t["need"]),
                 "Work before": fmt(t["work_before"]), "Work after (+ its Allocation)": fmt(t["work_after"])}
                for t in r["trace"]]
        st.dataframe(pd.DataFrame(rows).set_index("Step"))


def show_detection(d, det):
    c = st.columns(3)
    c[0].markdown("**1. Allocation matrix**"); c[0].dataframe(to_df(d["allocation"]))
    c[1].markdown("**2. Request matrix** (waiting for)"); c[1].dataframe(to_df(d["request"]))
    c[2].markdown("**3. Available vector**"); c[2].dataframe(vec_df(d["available"]))
    st.markdown("#### Detection: matrix reduction")
    if det["deadlock"]:
        verdict("DEADLOCKED", "Cannot finish: " + ", ".join(f"P{i}" for i in det["deadlocked"]))
    if det["trace"]:
        rows = [{"Process": f"P{t['process']}", "Request": fmt(t["request"]), "Work before": fmt(t["work_before"]),
                 "Work after": fmt(t["work_after"])} for t in det["trace"]]
        st.dataframe(pd.DataFrame(rows).set_index("Process"))


DEMO = [
    ("A", "Safe state", "Need matrix, Work updates, full safe sequence.", "SAFE"),
    ("B", "Request exceeds Available", "Within Need, not within Available: waits.", "WAITING"),
    ("C", "Request makes state unsafe", "Simulate, run safety, deny, restore.", "UNSAFE"),
    ("D", "Deadlock detection and recovery", "Circular wait found; terminate a victim.", "DEADLOCKED"),
    ("E", "Deadlock prevention", "Compare original with two policies.", "SAFE"),
    ("F", "Boundary and invalid inputs", "Valid edge cases vs rejected input.", "INVALID"),
]


def run_demo(letter):
    """Runs one required scenario on the real functions; returns what to show."""
    M = sc.MAIN
    ban = {"kind": "banker", "A": M["allocation"], "MX": M["maximum"], "AV": M["available"]}
    if letter in "ABC":
        load_system(sc.MAIN)
    if letter == "A":
        need = bk.calculate_need(M["maximum"], M["allocation"])
        r = bk.safety_check(M["allocation"], need, M["available"])
        lines = [f"Need matrix = Maximum - Allocation: {need}", f"Start: Work = Available = {M['available']}"]
        lines += [f"P{t['process']}: Need {t['need']} <= Work {t['work_before']}, so it finishes; Work becomes {t['work_after']}" for t in r["trace"]]
        lines.append("Safe sequence: " + " -> ".join(f"P{i}" for i in r["sequence"]))
        return {"key": "SAFE", "head": "Safe sequence found", "lines": lines, "system": ban, "safety": r,
                "say": "The state is safe because every process can finish in turn, each returning its resources for the next."}
    if letter in "BC":
        pid, vec = (0, [3, 0, 0]) if letter == "B" else (0, [2, 2, 1])
        r = bk.handle_request(pid, vec, M["allocation"], M["maximum"], M["available"])
        lines = [("OK: " if c["ok"] else "FAILED: ") + c["label"] for c in r["checks"]]
        lines.append(r["message"])
        if letter == "C":
            lines.append(f"Pretend Available would be {r['simulated']['available']}; processes that cannot finish: {['P%d' % i for i in r['safety']['stuck']]}")
            lines.append("Pretend allocation discarded; original Allocation and Available are unchanged.")
            return {"key": "UNSAFE", "head": "Denied: unsafe", "lines": lines, "system": ban, "request": (pid, vec),
                    "pretend": r["simulated"], "safety": r["safety"],
                    "say": "Unsafe is not deadlocked: nobody is blocked yet, but no safe order exists, so Banker's refuses the request."}
        return {"key": "WAITING", "head": "Waiting / deferred, not invalid", "lines": lines, "system": ban, "request": (pid, vec),
                "say": "The request is legal (within Need) so it is not invalid; it just cannot be served now. Nothing changed."}
    if letter == "D":
        d = sc.DET_DEADLOCK
        det = dt.detect_multi(d["allocation"], d["request"], d["available"])
        cyc = dt.find_cycle(dt.rag_edges(d["allocation"], d["request"]))
        v = dt.choose_victim(det["deadlocked"], d["allocation"])
        rec = dt.recover_multi(d["allocation"], d["request"], d["available"], v)
        s = dt.detect_single(sc.SINGLE_DEADLOCK["holds"], sc.SINGLE_DEADLOCK["waits"])
        lines = ["Model 1: multiple-instance, matrix reduction (Detection page).",
                 f"Graph cycle: {' -> '.join(cyc)}; reduction leaves {['P%d' % i for i in det['deadlocked']]} unable to finish = confirmed deadlock.",
                 "Model 2: single-instance, wait-for graph: cycle " + " -> ".join(s["cycle"]) + " = deadlock.",
                 f"Recovery: terminate P{v} (holds fewest resources). It releases {rec['released']}.",
                 "After recovery, finish order: " + " -> ".join(f"P{i}" for i in rec["after"]["finish_order"]) + "."]
        return {"key": "DEADLOCKED", "head": "Deadlock detected, then recovered", "lines": lines,
                "system": {"kind": "detect", "data": d}, "detect": det,
                "say": "With multiple instances a cycle is only a possible circular wait; the reduction algorithm confirms it. Banker's cannot do this job."}
    if letter == "E":
        procs, _ = pv.parse_processes(sc.PREVENTION_TEXT)
        lines = []
        for k, name in (("none", "Original"), ("ordering", "Resource ordering"), ("upfront", "Request all upfront")):
            r = pv.simulate(procs, k, sc.PREVENTION_ORDER)
            lines.append(f"{name}: " + (f"DEADLOCK {r['deadlocked']}" if r["deadlock"] else
                         f"completes in {r['makespan']} units, resource use {r['utilisation']}, held-but-idle {r['idle_held']}"))
        lines.append("Ordering breaks circular wait; upfront breaks hold-and-wait. Trade-off: idle held resources and less concurrency.")
        return {"key": "SAFE", "head": "Deadlock prevented", "lines": lines,
                "say": "Both policies remove a Coffman condition, but upfront wastes more resources because processes hold what they do not use yet."}
    cases = sc.tc6_cases()
    lines = [("OK: " if c["ok"] else "MISMATCH: ") + f"{c['case']} -> {c['actual']}. {c['detail']}" for c in cases]
    return {"key": "INVALID", "head": "Valid boundary cases accepted, invalid input rejected", "lines": lines,
            "say": "Zero Available or zero Need are legal; negative numbers, bad ids, Allocation > Maximum and Request > Need are invalid."}


def page_demo():
    st.title("Demo board")
    st.write("One click runs a required scenario on the real algorithms and lights the matching signal. "
             "Scenarios A to C also load the main dataset into the other pages.")
    lamp_panel()
    cols = st.columns(3)
    for i, (letter, title, blurb, key) in enumerate(DEMO):
        with cols[i % 3]:
            ui.panel(f"Scenario {letter}: {title}", blurb, STATES[key][1])
            if st.button(f"Run scenario {letter}", key=f"demo_{letter}"):
                res = run_demo(letter)
                st.session_state["demo"] = (letter, title, res)
                set_status(res["key"], res["head"])
                st.rerun()
            st.write("")
    if "demo" in st.session_state:
        letter, title, res = st.session_state["demo"]
        st.subheader(f"Scenario {letter}: {title}")
        sysd = res.get("system")
        if sysd and sysd["kind"] == "banker":
            show_tables(sysd["A"], sysd["MX"], sysd["AV"])
            if res.get("request"):
                pid, vec = res["request"]
                st.markdown(f"**Request submitted:** P{pid} asks for {fmt(vec)}")
            if res.get("pretend"):
                st.markdown("**Pretend allocation (temporary, then discarded)**")
                p = res["pretend"]
                pc = st.columns(3)
                pc[0].dataframe(to_df(p["allocation"])); pc[1].dataframe(to_df(p["need"])); pc[2].dataframe(vec_df(p["available"]))
            if res.get("safety"):
                show_safety(res["safety"])
        elif sysd and sysd["kind"] == "detect":
            show_detection(sysd["data"], res["detect"])
        with st.expander("Written explanation of every step", expanded=not sysd):
            for ln in res["lines"]:
                st.write("- " + ln)
        st.info("Say in the demo: " + res["say"])


def page_setup():
    st.title("System setup")
    st.write("Define processes, resource types and the three inputs. **Need = Maximum - Allocation** is calculated for you.")
    lamp_panel()

    c = st.columns([1, 1, 2])
    n_old, m_old = len(st.session_state["base_alloc"]), len(st.session_state["base_avail"].columns)
    n = c[0].number_input("Processes", 1, 10, n_old)
    m = c[1].number_input("Resource types", 1, 8, m_old)
    if (n, m) != (n_old, m_old):
        load_system({"allocation": [[0] * m for _ in range(n)], "maximum": [[0] * m for _ in range(n)], "available": [0] * m})
        st.rerun()

    preset = c[2].selectbox("Load a dataset", ["Our main system (safe, 4 x 3)", "Zero-need variant (P3 holds its full maximum)"])
    if c[2].button("Load dataset"):
        load_system(sc.MAIN if preset.startswith("Our") else sc.ZERO_NEED)
        st.rerun()

    ver = st.session_state["sys_ver"]
    left, right = st.columns(2)
    with left:
        st.markdown("**Allocation** (what each process holds now)")
        st.session_state["alloc_val"] = st.data_editor(st.session_state["base_alloc"], key=f"alloc_{ver}")
    with right:
        st.markdown("**Maximum** (most each process may ever need)")
        st.session_state["max_val"] = st.data_editor(st.session_state["base_max"], key=f"max_{ver}")
    st.markdown("**Available** (free instances right now)")
    st.session_state["avail_val"] = st.data_editor(st.session_state["base_avail"], key=f"avail_{ver}")

    a, mx, av = get_system()
    check = val.validate_state(a, mx, av)
    if check["errors"]:
        set_status("INVALID", check["errors"][0])
        for e in check["errors"]:
            st.error(e)
        return
    for note in check["notes"]:
        st.info(note)
    A = [[int(x) for x in r] for r in a]
    MX = [[int(x) for x in r] for r in mx]
    need = bk.calculate_need(MX, A)
    st.markdown("**Need** (calculated)")
    st.dataframe(to_df(need))
    total = [sum(A[i][j] for i in range(len(A))) + int(av[j]) for j in range(len(av))]
    st.caption(f"Implied total instances per resource type: {dict(zip(rnames(len(av)), total))}")


def page_avoidance():
    st.title("Deadlock avoidance: Banker's Algorithm")
    A, MX, AV, notes = valid_system_or_stop()
    need = bk.calculate_need(MX, A)
    lamp_panel()
    for nte in notes:
        st.info(nte)

    c = st.columns(3)
    c[0].markdown("**Allocation**"); c[0].dataframe(to_df(A))
    c[1].markdown("**Need = Max - Alloc**"); c[1].dataframe(to_df(need))
    c[2].markdown("**Available**"); c[2].dataframe(vec_df(AV))
    total = [sum(A[i][j] for i in range(len(A))) + AV[j] for j in range(len(AV))]
    ui.resource_bars(rnames(len(AV)), AV, total, "Free resources right now (free / total)")

    st.subheader("1. Safety check")
    if st.button("Run safety algorithm"):
        r = bk.safety_check(A, need, AV)
        r["sig"] = repr((A, MX, AV))
        st.session_state["safety"] = r
        if r["safe"]:
            set_status("SAFE", "Safe sequence: " + " -> ".join(f"P{i}" for i in r["sequence"]))
        else:
            set_status("UNSAFE", f"No complete safe sequence. Processes that cannot finish: {', '.join('P%d' % i for i in r['stuck'])}.")
        st.rerun()
    r = st.session_state.get("safety")
    if r and r.get("sig") != repr((A, MX, AV)):
        st.session_state.pop("safety", None)   # system was edited: old trace no longer applies
        r = None
    if r:
        if r["trace"]:
            step = st.slider("Step through the safe sequence", 0, len(r["trace"]), len(r["trace"]), key="step_slider")
            ui.track(r["sequence"], step, r["stuck"] if not r["safe"] else ())
            work = AV if step == 0 else r["trace"][step - 1]["work_after"]
            ui.resource_bars(rnames(len(AV)), work, total, f"Work vector after {step} process(es) finished", "#1E8E5A")
        else:
            ui.track([], 0, r["stuck"])
        rows = [{"Step": t["step"], "Process picked": f"P{t['process']}", "Its Need": fmt(t["need"]),
                 "Work before": fmt(t["work_before"]), "Work after (+ its Allocation)": fmt(t["work_after"])} for t in r["trace"]]
        st.dataframe(pd.DataFrame(rows).set_index("Step") if rows else pd.DataFrame())
        if r["safe"]:
            st.success("Safe sequence: " + " -> ".join(f"P{i}" for i in r["sequence"]) +
                       ". Each process in turn can finish with the Work vector, then returns its Allocation, "
                       "so everyone can finish. That is why the state is safe.")
        else:
            st.warning("Unsafe. Stuck processes: " + ", ".join(f"P{i}" for i in r["stuck"]) +
                       ". Unsafe is a risk warning, not a deadlock: nobody is blocked yet, but no order is guaranteed.")
        st.caption("Press the button again after changing the system to refresh this trace.")

    st.subheader("2. Resource request")
    c = st.columns([1, 2, 1])
    pid_text = c[0].text_input("Process", "P0")
    req_text = c[1].text_input("Request vector (comma separated)", "2,2,1")
    go = c[2].button("Evaluate request")
    if go:
        pid, vec, err = val.parse_request_inputs(pid_text, req_text, len(A), len(AV))
        res = bk.invalid_result(err) if err else bk.handle_request(pid, vec, A, MX, AV)
        res["who"] = (pid_text, req_text)
        st.session_state["last_request"] = res
        key = {"GRANTED": "SAFE", "WAITING": "WAITING", "DENIED_UNSAFE": "UNSAFE", "INVALID": "INVALID"}[res["status"]]
        set_status(key, res["message"])
        st.rerun()

    res = st.session_state.get("last_request")
    if res:
        st.markdown(f"Last request: **{res['who'][0]}** asks for **{res['who'][1]}**")
        for chk in res["checks"]:
            st.write(("✅ " if chk["ok"] else "❌ ") + chk["label"])
        if res["status"] == "DENIED_UNSAFE":
            sim = res["simulated"]
            st.markdown("**Pretend allocation (temporary):**")
            cc = st.columns(3)
            cc[0].dataframe(to_df(sim["allocation"])); cc[1].dataframe(to_df(sim["need"])); cc[2].dataframe(vec_df(sim["available"]))
            st.error("Safety algorithm on the pretend state: no process can finish (stuck: " +
                     ", ".join(f"P{i}" for i in res["safety"]["stuck"]) + "). Request denied, pretend allocation discarded.")
            st.success("Original state restored: the matrices above are unchanged.")
            st.info("Why this is *unsafe* and not *deadlocked*: nobody is waiting yet; the system has simply lost its guarantee. "
                    "Denying the request keeps it safe.")
        elif res["status"] == "WAITING":
            st.info("The request stays pending. Allocation and Available are unchanged; it can be retried once resources are released.")
        elif res["status"] == "GRANTED":
            st.success("Safe sequence after granting: " + " -> ".join(f"P{i}" for i in res["safety"]["sequence"]))
            if st.button("Commit this allocation to the system"):
                st.session_state["alloc_val"] = to_df(res["new_allocation"])
                st.session_state["base_alloc"] = st.session_state["alloc_val"]
                st.session_state["avail_val"] = vec_df(res["new_available"])
                st.session_state["base_avail"] = st.session_state["avail_val"]
                st.session_state["sys_ver"] += 1
                st.session_state.pop("last_request", None)
                st.session_state.pop("safety", None)
                set_status("SAFE", "Allocation committed; system is still safe.")
                st.rerun()
        elif res["status"] == "INVALID":
            st.error(res["message"])


# ---- detection ---------------------------------------------------------------
def dot_rag(alloc, request, bad):
    n, m = len(alloc), len(alloc[0])
    lines = ["digraph G { rankdir=LR; node [fontname=Helvetica];"]
    for i in range(n):
        col = "#c0392b" if i in bad else "#7a8594"
        lines.append(f'P{i} [shape=circle, color="{col}", penwidth=2];')
    for j in range(m):
        lines.append(f'R{j} [shape=box, label="{val.rname(j)}"];')
    for a, b, k in dt.rag_edges(alloc, request):
        style = 'color="#1f8a5b"' if a.startswith("R") else 'color="#c0392b", style=dashed'
        lines.append(f'{a} -> {b} [label="{k}", {style}];')
    return "\n".join(lines) + "}"


def dot_wfg(edges, procs, bad):
    lines = ['digraph G { rankdir=LR; node [shape=circle, fontname=Helvetica];']
    for p in procs:
        lines.append(f'"{p}" [color="{"#c0392b" if p in bad else "#7a8594"}", penwidth=2];')
    for a, b, r in edges:
        lines.append(f'"{a}" -> "{b}" [label="waits for {r}"];')
    return "\n".join(lines) + "}"


def load_det(key, d):
    st.session_state["det_ver"] = st.session_state.get("det_ver", 0) + 1
    st.session_state[key] = d


MULTI_PRESETS = {
    "Deadlock: P0, P1, P2 stuck": sc.DET_DEADLOCK,
    "Cycle in graph but NO deadlock": sc.DET_CYCLE_NO_DEADLOCK,
}


def page_detection():
    st.title("Deadlock detection and recovery")
    st.caption("Detection looks at the current allocations and *waiting requests* of a system that may already be stuck. "
               "This is a separate job from Banker's avoidance, which only decides whether to grant a request.")
    lamp_panel()
    model = st.radio("Resource model", ["Multiple-instance (matrix reduction)", "Single-instance (wait-for graph)"], horizontal=True)
    if model.startswith("Multiple"):
        detection_multi()
    else:
        detection_single()


def detection_multi():
    st.info("Model: **multiple-instance** resources. A cycle in the resource-allocation graph is not conclusive here, "
            "so we run matrix reduction: repeatedly let any process whose Request <= Work finish and return its Allocation.")
    names = list(MULTI_PRESETS)
    if "det_multi" not in st.session_state:
        load_det("det_multi", MULTI_PRESETS[names[0]])
    c = st.columns([2, 1])
    pick = c[0].selectbox("Dataset", names)
    if c[1].button("Load dataset", key="ld_multi"):
        load_det("det_multi", MULTI_PRESETS[pick]); st.rerun()
    d = st.session_state["det_multi"]
    ver = st.session_state["det_ver"]
    cc = st.columns(2)
    alloc_df = cc[0].data_editor(to_df(d["allocation"]), key=f"da_{ver}")
    req_df = cc[1].data_editor(to_df(d["request"]), key=f"dr_{ver}")
    av_df = st.data_editor(vec_df(d["available"]), key=f"dv_{ver}")
    cc[0].caption("Allocation: what each process holds")
    cc[1].caption("Request: what each is waiting for")

    A, R, AV = alloc_df.values.tolist(), req_df.values.tolist(), av_df.values.tolist()[0]
    errs = [e for e in val.validate_state(A, A, AV)["errors"]]
    errs += [] if all(val.is_int(x) and x >= 0 for r in R for x in r) else ["Request matrix must contain whole numbers >= 0."]
    if errs:
        set_status("INVALID", errs[0]); st.error(errs[0]); return
    A = [[int(x) for x in r] for r in A]; R = [[int(x) for x in r] for r in R]; AV = [int(x) for x in AV]

    det = dt.detect_multi(A, R, AV)
    cycle = dt.find_cycle(dt.rag_edges(A, R))
    st.graphviz_chart(dot_rag(A, R, det["deadlocked"]))
    st.markdown(f"**Graph check:** {'a cycle exists (' + ' -> '.join(cycle) + ')' if cycle else 'no cycle'}.  "
                f"**Matrix-reduction verdict:** {'DEADLOCK' if det['deadlock'] else 'no deadlock'}.")
    rows = [{"Process": f"P{t['process']}", "Request": fmt(t["request"]), "Work before": fmt(t["work_before"]),
             "Work after": fmt(t["work_after"])} for t in det["trace"]]
    if rows:
        st.dataframe(pd.DataFrame(rows).set_index("Process"))

    if det["deadlock"]:
        txt = f"Processes that can never finish: {', '.join('P%d' % i for i in det['deadlocked'])}."
        set_status("DEADLOCKED", txt); verdict("DEADLOCKED", txt)
    else:
        txt = "No deadlock: every process can eventually finish."
        set_status("SAFE", txt); verdict("SAFE", txt)
        if cycle:
            st.warning("The graph has a cycle, which looks like a circular wait, but with several instances of a resource "
                       "another process (not waiting) can release one, so the cycle is only a *potential* circular wait, not a confirmed deadlock.")

    if det["deadlock"]:
        st.subheader("Recovery: terminate a process")
        suggested = dt.choose_victim(det["deadlocked"], A)
        st.caption(f"Rule: terminate the deadlocked process holding the fewest resources. Suggested victim: P{suggested}.")
        victim = st.selectbox("Victim", det["deadlocked"], index=det["deadlocked"].index(suggested), format_func=lambda i: f"P{i}")
        if st.button("Terminate victim and re-check"):
            rec = dt.recover_multi(A, R, AV, victim)
            st.write(f"P{victim} terminated. It releases **{fmt(rec['released'])}**, so Available becomes **{fmt(rec['available'])}**.")
            cc = st.columns(2)
            cc[0].dataframe(to_df(rec["allocation"])); cc[1].dataframe(to_df(rec["request"]))
            after = rec["after"]
            if after["deadlock"]:
                st.error("Still deadlocked: " + ", ".join(f"P{i}" for i in after["deadlocked"]) + ". Pick another victim.")
            else:
                st.success("Deadlock resolved. Finish order now possible: " + " -> ".join(f"P{i}" for i in after["finish_order"]) +
                           ". The released resources let the waiting processes proceed.")


SINGLE_PRESETS = {
    "Circular wait: P1 <-> P2": sc.SINGLE_DEADLOCK,
    "Chain without a cycle": {"holds": {"P1": {"R1"}, "P2": {"R2"}, "P3": {"R3"}},
                              "waits": {"P1": {"R2"}, "P2": {"R3"}, "P3": set()}},
}


def _parse_set(text):
    return {x for x in str(text or "").replace(",", " ").split() if x}


def detection_single():
    st.info("Model: **single-instance** resources (each has exactly one copy). Here a cycle in the wait-for graph "
            "*is* a deadlock.")
    names = list(SINGLE_PRESETS)
    if "det_single" not in st.session_state:
        load_det("det_single", SINGLE_PRESETS[names[0]])
    c = st.columns([2, 1])
    pick = c[0].selectbox("Dataset", names)
    if c[1].button("Load dataset", key="ld_single"):
        load_det("det_single", SINGLE_PRESETS[pick]); st.rerun()
    d = st.session_state["det_single"]
    df = pd.DataFrame([{"Process": p, "Holds": ", ".join(sorted(d["holds"].get(p, set()))),
                        "Waits for": ", ".join(sorted(d["waits"].get(p, set())))} for p in d["holds"]])
    edited = st.data_editor(df, num_rows="dynamic", key=f"ds_{st.session_state['det_ver']}")
    holds, waits = {}, {}
    for _, row in edited.iterrows():
        p = str(row["Process"]).strip()
        if p and p != "None":
            holds[p] = _parse_set(row["Holds"]); waits[p] = _parse_set(row["Waits for"])
    res = dt.detect_single(holds, waits)
    if res["errors"]:
        set_status("INVALID", res["errors"][0]); st.error(res["errors"][0]); return
    st.graphviz_chart(dot_wfg(res["edges"], list(holds), res["deadlocked"]))
    if res["deadlock"]:
        txt = f"Circular wait {' -> '.join(res['cycle'])}. Deadlocked: {', '.join(res['deadlocked'])}."
        set_status("DEADLOCKED", txt); verdict("DEADLOCKED", txt)
        st.subheader("Recovery: terminate a process")
        victim = st.selectbox("Victim", res["deadlocked"])
        if st.button("Terminate victim and re-check", key="rec_single"):
            rec = dt.recover_single(holds, waits, victim)
            st.write(f"{victim} terminated; it releases **{', '.join(rec['released']) or 'nothing'}**.")
            if rec["after"]["deadlock"]:
                st.error("Still deadlocked.")
            else:
                st.success("Deadlock resolved: the remaining processes can now obtain what they wait for and finish.")
    else:
        txt = "No cycle in the wait-for graph, so no deadlock."
        set_status("SAFE", txt); verdict("SAFE", txt)


# ---- prevention --------------------------------------------------------------
def page_prevention():
    st.title("Deadlock prevention")
    st.write("Prevention removes one Coffman condition by policy. Each process lists the resources it needs in the order it "
             "asks for them, with how long it uses each (`R1:2` = use R1 for 2 time units). Resources are single-instance "
             "and held until the process finishes.")
    lamp_panel()
    text = st.text_area("Processes", sc.PREVENTION_TEXT, height=120)
    order_text = st.text_input("Global resource order (for the ordering policy)", ", ".join(sc.PREVENTION_ORDER))
    procs, errs = pv.parse_processes(text)
    order = [x for x in order_text.replace(",", " ").split() if x]
    if errs:
        set_status("INVALID", errs[0])
        for e in errs: st.error(e)
        return
    used = {r for s in procs.values() for r, _ in s}
    if set(order) < used:
        e = f"Global order is missing: {', '.join(sorted(used - set(order)))}."
        set_status("INVALID", e); st.error(e); return

    viol = pv.order_violations(procs, order)
    if viol:
        st.warning("Ordering violations in the original request pattern (these allow circular wait):")
        for v in viol: st.write("- " + v)
    else:
        st.success("Every process already requests in the global order.")

    if st.button("Compare policies"):
        results = {k: pv.simulate(procs, k, order) for k in ("none", "ordering", "upfront")}
        labels = {"none": "Original (no policy)", "ordering": "Resource ordering", "upfront": "Request all upfront"}
        rows = []
        for k, r in results.items():
            rows.append({"Policy": labels[k],
                         "Outcome": f"DEADLOCK ({', '.join(r['deadlocked'])})" if r["deadlock"] else "completes",
                         "Finish time": str(r["makespan"]) if r["makespan"] is not None else "-",
                         "Time units spent waiting": r["wait_ticks"],
                         "Resource use / held": str(r["utilisation"]) if r["utilisation"] is not None else "-",
                         "Held but idle (units)": str(r["idle_held"]) if r["idle_held"] is not None else "-"})
        st.session_state["prev_rows"] = rows
        if results["none"]["deadlock"] and not results["ordering"]["deadlock"] and not results["upfront"]["deadlock"]:
            set_status("SAFE", "Original policy deadlocks; both prevention policies complete without deadlock.")
        elif results["none"]["deadlock"]:
            set_status("DEADLOCKED", "Original policy deadlocks and at least one prevention policy still does.")
        else:
            set_status("SAFE", "This workload does not deadlock even without a policy; compare the costs below.")
        st.rerun()
    if "prev_rows" in st.session_state:
        st.dataframe(pd.DataFrame(st.session_state["prev_rows"]).set_index("Policy"))

    st.subheader("Which condition each policy breaks")
    st.table(pd.DataFrame(pv.COFFMAN).rename(columns={"none": "Original", "ordering": "Ordering", "upfront": "All upfront"}))
    st.markdown("""**Trade-offs**
- *Resource ordering* removes circular wait, but processes may have to acquire resources earlier than they need them, and the order is hard to choose.
- *Request all upfront* removes hold and wait, but processes hold resources they are not using yet, so utilisation drops and fewer processes run at once; it can also starve a process that needs many resources.""")


# ---- test lab ----------------------------------------------------------------
def page_testlab():
    st.title("Test lab: TC1 - TC6")
    st.write("Each row is produced by running this dashboard's own functions on the group's datasets. "
             "Add your analysis, then download the table for the report.")
    lamp_panel()
    rows = sc.run_all()
    df = pd.DataFrame(rows).set_index("Test Case")
    st.dataframe(df)
    if all(r["Match"] == "PASS" for r in rows):
        st.success("All six test cases match their expected results.")
    else:
        st.error("Some test cases do not match; investigate before submitting.")

    st.subheader("TC6 detail")
    t6 = pd.DataFrame(sc.tc6_cases())[["case", "expected", "actual", "detail", "ok"]]
    t6.columns = ["Case", "Expected class", "Actual class", "Dashboard message", "As expected"]
    st.dataframe(t6.set_index("Case"))

    st.subheader("Your analysis / conclusion")
    notes = st.session_state.setdefault("analysis", {r["Test Case"]: "" for r in rows})
    for r in rows:
        notes[r["Test Case"]] = st.text_area(f"{r['Test Case']} - {r['System Condition']}", notes[r["Test Case"]], height=80, key=f"an_{r['Test Case']}")
    out = pd.DataFrame(rows)
    out["Analysis / Conclusion"] = [notes[r["Test Case"]] for r in rows]
    st.download_button("Download table (CSV)", out.to_csv(index=False).encode("utf-8"), "test_case_table.csv", "text/csv")


PAGES = {
    "Home": page_concepts,
    "Demo board": page_demo,
    "System setup": page_setup,
    "Avoidance (Banker's)": page_avoidance,
    "Detection and recovery": page_detection,
    "Prevention": page_prevention,
    "Test lab (TC1-TC6)": page_testlab,
}
with st.sidebar:
    st.markdown("### Deadlock Control Room")
    choice = st.radio("Go to", list(PAGES), label_visibility="collapsed")
    st.caption("Avoidance, detection and prevention/recovery are separate tools on purpose.")
PAGES[choice]()
