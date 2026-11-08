"""Injectable judge layer -- objective / human / llm.

Priority is fixed: objective -> human -> llm. If an objective check exists it wins;
only when it is unavailable does the judge fall back to a human checklist, and only
then to model self-scoring. This module uses the standard library only so it can be
self-checked offline (test_judge.py) without importing anything from the repo.

Conventions:
- `checks` is a callable `check(artifact, run_return) -> (bool, float)`, i.e. (passed, score).
- `llm_scorer` is a callable `scorer(plan, artifact, run_return) -> (score, message, is_valid)`,
  bound by each module so the original get_score behaviour is preserved.
- Scoring returns the triple `(score, message, is_valid)`, compatible with the existing
  get_score call sites: `score=None` means "this attempt is not scored".
- `record` stores (mode, score, candidate) for every scoring call, used to compare the
  objective score against the LLM self-score (how much the judge inflates).
"""
import importlib.util

MODES = ("objective", "human", "llm")


def load_checks(path):
    """Load a checks file and return its `check` callable; None if missing or unusable."""
    if not path:
        return None
    spec = importlib.util.spec_from_file_location("user_checks", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"[judge] checks file failed to load (falling back): {e}")
        return None
    fn = getattr(module, "check", None)
    return fn if callable(fn) else None


class Judge:
    def __init__(self, mode="objective", checks=None, llm_scorer=None, checklist=None,
                 input_fn=None, record=None, checks_path=None):
        if mode not in MODES:
            mode = "llm"
        self.mode = mode
        self.checks = checks
        self.checks_path = checks_path
        self.llm_scorer = llm_scorer
        self.checklist = checklist if checklist is not None else []
        self.input_fn = input_fn if input_fn is not None else input
        self.record = record if record is not None else []

    def __getstate__(self):
        """A checks callable loaded by importlib cannot be pickled (its module name
        `user_checks` is not importable). Save the path instead; the check is reloaded
        on unpickle. Real error seen in a live run: `pickle.dump(self, f)` ->
        `_pickle.PicklingError: Can't pickle <function check ...>: import of module
        'user_checks' failed`, raised from ai_lab_repo.save_state."""
        state = dict(self.__dict__)
        state["checks"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        if self.checks is None and self.checks_path:
            self.checks = load_checks(self.checks_path)

    def bind_llm(self, scorer):
        """Bind the LLM self-scoring implementation; never overwrite an existing binding
        so a shared Judge instance keeps one record."""
        if self.llm_scorer is None:
            self.llm_scorer = scorer

    def _record(self, mode, score, candidate=None):
        self.record.append({"mode": mode, "score": score, "candidate": candidate})

    def _objective(self, artifact, run_return):
        try:
            ok, value = self.checks(artifact, run_return)
        except Exception as e:
            return None, f"objective check failed to run: {e}", False
        score = 0.0 if not ok else float(value)
        return score, f"objective: pass={bool(ok)} score={score:.3f}", True

    def _human(self, artifact, run_return):
        try:
            if self.checklist:
                print("[judge] checklist:")
                for item in self.checklist:
                    print(f"  - {item}")
            raw = self.input_fn("[judge] score 0-1 by checklist (y=1, n=0, empty=skip): ")
        except Exception as e:
            return None, f"human judge unavailable ({e}), falling back", False
        if raw is None:
            return None, "human judge got no input, falling back", False
        text = str(raw).strip().lower()
        if text == "":
            return None, "human judge got empty input, falling back", False
        if text in ("y", "yes"):
            return 1.0, "human: y -> 1.0", True
        if text in ("n", "no"):
            return 0.0, "human: n -> 0.0", True
        try:
            value = float(text)
        except ValueError:
            return None, f"human judge input not parseable: {text}", False
        value = max(0.0, min(1.0, value))
        return value, f"human: {value:.3f}", True

    def evaluate(self, plan, artifact, run_return="", compare=False):
        """Score in the order objective -> human -> llm. compare=True also runs the LLM
        self-score once and records the gap (skipped when the score already came from the LLM)."""
        candidate = str(artifact)[:60]
        source = None

        if self.checks is not None:
            score, message, is_valid = self._objective(artifact, run_return)
            source = "objective"
            # A check that cannot run is an invalid score, not a 0: the caller's repair loop
            # handles it, matching the old format-gate semantics. No fallback here.
        elif self.mode == "human":
            score, message, is_valid = self._human(artifact, run_return)
            source = "human"
            if not is_valid and self.llm_scorer is not None:
                score, message, is_valid = self.llm_scorer(plan, artifact, run_return)
                source = "llm"
        elif self.llm_scorer is not None:
            score, message, is_valid = self.llm_scorer(plan, artifact, run_return)
            source = "llm"
        else:
            score, message, is_valid = None, "no judge available", False

        if source is not None:
            self._record(source, score, candidate)
        if compare and score is not None and source != "llm" and self.llm_scorer is not None:
            llm_score, _, llm_ok = self.llm_scorer(plan, artifact, run_return)
            self._record("llm", llm_score, candidate)
            if llm_ok:
                message += f" | llm={llm_score:.3f} diff={score - llm_score:+.3f}"
        return score, message, is_valid

    def diff_report(self):
        """Pair the objective/human score with the LLM self-score per candidate, to show
        how much the judge inflates."""
        by_candidate = {}
        for item in self.record:
            by_candidate.setdefault(item.get("candidate", "unknown"), {})[item["mode"]] = item["score"]
        rows = []
        for candidate, modes in by_candidate.items():
            judge_score = modes.get("objective", modes.get("human"))
            llm_score = modes.get("llm")
            if judge_score is None or llm_score is None:
                continue
            rows.append((candidate, judge_score, llm_score, judge_score - llm_score))
        return rows
