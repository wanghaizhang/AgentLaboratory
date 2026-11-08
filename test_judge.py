"""Offline self-check for the judge layer (no pip install; judge.py uses stdlib only).

Run: py -3 test_judge.py
"""
import sys

import judge


def fake_llm(plan, artifact, run_return):
    return 1.0, "llm self-score (deliberately 1.0, to test priority and the gap)", True


def check_pass(artifact, run_return):
    return True, 0.8

def check_fail(artifact, run_return):
    return False, 0.0

def check_raise(artifact, run_return):
    raise RuntimeError("check blew up inside")


def main():
    # 1. objective pass
    j = judge.Judge(mode="objective", checks=check_pass, llm_scorer=fake_llm)
    score, msg, ok = j.evaluate("plan", "artifact", "return")
    assert ok and abs(score - 0.8) < 1e-9, f"objective pass should score 0.8, got {score}"

    # 2. objective fail -> 0.0 and still a valid score (this is the penalty semantics:
    #    a 0-scoring attempt never enters the top-K archive)
    j = judge.Judge(mode="objective", checks=check_fail, llm_scorer=fake_llm)
    score, msg, ok = j.evaluate("plan", "artifact", "return")
    assert ok and score == 0.0, f"objective fail should be 0.0/valid, got {score}/{ok}"

    # 3. priority: an objective check must not be overridden by the LLM self-score
    assert "objective" in msg, f"priority wrong: {msg}"

    # 4. human mapping: y / n / numeric
    for raw, expected in (("y", 1.0), ("n", 0.0), ("0.7", 0.7)):
        j = judge.Judge(mode="human", input_fn=lambda r, v=raw: v, llm_scorer=fake_llm)
        score, msg, ok = j.evaluate("plan", "artifact", "return")
        assert ok and abs(score - expected) < 1e-9, f"human input {raw} should map to {expected}, got {score}"

    # 5. human unavailable (non-interactive) must fall back to llm, not raise
    def boom(prompt):
        raise EOFError("no tty")
    j = judge.Judge(mode="human", input_fn=boom, llm_scorer=fake_llm)
    score, msg, ok = j.evaluate("plan", "artifact", "return")
    assert ok and score == 1.0, f"human unavailable should fall back to llm, got {score}/{msg}"
    modes = [item["mode"] for item in j.record]
    assert modes == ["llm"], f"fallback should record only llm, got {modes}"
    _, fb_msg, fb_ok = j._human("artifact", "return")
    assert (not fb_ok) and "falling back" in fb_msg, f"human fallback message wrong: {fb_msg}"

    # 6. check raises inside -> is_valid False (equivalent to the old format-gate failure),
    #    score None, and no fallback: the caller's repair loop owns that case
    j = judge.Judge(mode="objective", checks=check_raise, llm_scorer=fake_llm)
    score, msg, ok = j.evaluate("plan", "artifact", "return")
    assert not ok, f"check exception should be an invalid score, got {ok}"
    assert score is None, f"invalid score must be None, not 0, got {score}"
    assert [i["mode"] for i in j.record] == ["objective"], f"no fallback expected, got {[i['mode'] for i in j.record]}"

    # 7. no checks and no llm_scorer -> score=None (matches the old behaviour: not archived)
    j = judge.Judge(mode="llm")
    score, msg, ok = j.evaluate("plan", "artifact", "return")
    assert score is None and not ok, f"no judge should give None/invalid, got {score}/{ok}"

    # 8. compare records the gap and does not change the returned score
    j = judge.Judge(mode="objective", checks=check_pass, llm_scorer=fake_llm)
    score, msg, ok = j.evaluate("plan", "artifact", "return", compare=True)
    assert abs(score - 0.8) < 1e-9, f"compare must not change the returned score, got {score}"
    rows = j.diff_report()
    assert rows and abs(rows[0][3] - (-0.2)) < 1e-9, f"gap should be -0.2, got {rows}"

    # 9. bind_llm never overwrites an existing binding (precondition for a shared Judge)
    j = judge.Judge(mode="llm", llm_scorer=fake_llm)
    j.bind_llm(lambda plan, art, ret: (0.5, "other implementation", True))
    score, msg, ok = j.evaluate("plan", "artifact", "return")
    assert score == 1.0, f"bind_llm must not overwrite, got {score}"

    # 10. objective wins even when mode == human: a valid objective score must not be
    #     overwritten by the human checklist
    j = judge.Judge(mode="human", checks=check_pass, llm_scorer=fake_llm,
                    input_fn=lambda p: "0.3")
    score, msg, ok = j.evaluate("plan", "artifact", "return")
    assert ok and abs(score - 0.8) < 1e-9, f"objective must win over human, got {score}"
    assert [i["mode"] for i in j.record] == ["objective"], f"record should be objective only, got {[i['mode'] for i in j.record]}"

    # 11. a checks callable loaded from a file must survive pickling (the state_saves path
    #     in ai_lab_repo.save_state): Judge keeps the path and reloads the check on unpickle.
    import pickle, tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write("def check(artifact, run_return):\n    return True, 0.6\n")
        checks_file = f.name
    loaded = judge.load_checks(checks_file)
    j = judge.Judge(mode="objective", checks=loaded, checks_path=checks_file)
    restored = pickle.loads(pickle.dumps(j))
    assert restored.checks is not None, "checks must be reloaded after unpickle"
    score, msg, ok = restored.evaluate("plan", "artifact", "return")
    assert ok and abs(score - 0.6) < 1e-9, f"restored judge should score 0.6, got {score}"
    os.remove(checks_file)

    print("PASS: judge priority objective>human>llm, fail -> 0, unavailable -> fallback, compare records gap")
    print(f"  objective pass -> 0.8 | objective fail -> 0.0 | human y/n/0.7 -> 1.0/0.0/0.7")
    print(f"  compare gap sample: {rows[0][3]:+.3f}")
    print(f"  pickle round-trip: checks reloaded from path, restored score 0.6")
    return 0


if __name__ == "__main__":
    sys.exit(main())
