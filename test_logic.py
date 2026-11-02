"""pytest tests - run with:  pytest -v"""
import banker as bk, detection as dt, prevention as pv, validation as val, scenarios as sc

M = sc.MAIN
NEED = bk.calculate_need(M["maximum"], M["allocation"])


def test_need_matrix():
    assert NEED == [[3, 2, 1], [1, 1, 2], [2, 1, 1], [2, 2, 2]]


def test_safe_sequence_and_work_trace():
    r = bk.safety_check(M["allocation"], NEED, M["available"])
    assert r["safe"] and r["sequence"] == [1, 0, 2, 3]
    assert [t["work_after"] for t in r["trace"]] == [[4, 4, 3], [5, 4, 5], [8, 4, 6], [9, 5, 7]]


def test_waiting_when_exceeds_available():
    r = bk.handle_request(0, [3, 0, 0], M["allocation"], M["maximum"], M["available"])
    assert r["status"] == "WAITING" and r["new_allocation"] is None


def test_unsafe_request_denied_and_state_untouched():
    alloc_before = [row[:] for row in M["allocation"]]
    r = bk.handle_request(0, [2, 2, 1], M["allocation"], M["maximum"], M["available"])
    assert r["status"] == "DENIED_UNSAFE" and r["new_allocation"] is None
    assert r["simulated"]["available"] == [0, 1, 2]
    assert M["allocation"] == alloc_before and M["available"] == [2, 3, 3]


def test_safe_request_granted():
    r = bk.handle_request(1, [1, 0, 2], M["allocation"], M["maximum"], M["available"])
    assert r["status"] == "GRANTED" and r["new_available"] == [1, 3, 1]


def test_request_above_need_is_invalid_not_waiting():
    r = bk.handle_request(1, [2, 0, 0], M["allocation"], M["maximum"], M["available"])
    assert r["status"] == "INVALID"


def test_input_parsing():
    assert val.parse_request_inputs("P9", "1,0,0", 4, 3)[2]
    assert val.parse_request_inputs("P1", "-1,0,0", 4, 3)[2]
    assert val.parse_request_inputs("P1", "1,0", 4, 3)[2]
    assert val.parse_request_inputs("P1", "1.5,0,0", 4, 3)[2]
    assert val.parse_request_inputs("p2", "1,0,0", 4, 3)[2] is None


def test_state_validation():
    bad = [r[:] for r in M["allocation"]]; bad[1][0] = 9
    assert val.validate_state(bad, M["maximum"], M["available"])["errors"]
    z = val.validate_state(M["allocation"], M["maximum"], [0, 0, 0])
    assert not z["errors"] and z["notes"]
    zn = sc.ZERO_NEED
    assert any("zero remaining Need" in n for n in val.validate_state(zn["allocation"], zn["maximum"], zn["available"])["notes"])


def test_detection_multi():
    d = sc.DET_DEADLOCK
    r = dt.detect_multi(d["allocation"], d["request"], d["available"])
    assert r["deadlocked"] == [0, 1, 2]


def test_cycle_in_graph_but_no_deadlock():
    d = sc.DET_CYCLE_NO_DEADLOCK
    assert dt.find_cycle(dt.rag_edges(d["allocation"], d["request"]))
    assert not dt.detect_multi(d["allocation"], d["request"], d["available"])["deadlock"]


def test_recovery_multi():
    d = sc.DET_DEADLOCK
    v = dt.choose_victim([0, 1, 2], d["allocation"])
    rec = dt.recover_multi(d["allocation"], d["request"], d["available"], v)
    assert v == 0 and rec["released"] == [1, 0, 1] and not rec["after"]["deadlock"]


def test_single_instance_cycle_and_recovery():
    s = sc.SINGLE_DEADLOCK
    r = dt.detect_single(s["holds"], s["waits"])
    assert r["deadlock"] and r["deadlocked"] == ["P1", "P2"]
    rec = dt.recover_single(s["holds"], s["waits"], "P1")
    assert not rec["after"]["deadlock"]


def test_prevention():
    procs, errs = pv.parse_processes(sc.PREVENTION_TEXT)
    assert not errs
    assert pv.simulate(procs, "none", sc.PREVENTION_ORDER)["deadlock"]
    assert not pv.simulate(procs, "ordering", sc.PREVENTION_ORDER)["deadlock"]
    assert not pv.simulate(procs, "upfront", sc.PREVENTION_ORDER)["deadlock"]


def test_all_test_cases_pass():
    assert all(r["Match"] == "PASS" for r in sc.run_all())
