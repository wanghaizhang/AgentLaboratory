"""Objective acceptance check example (the `checks` file for the objective judge).

Interface: check(artifact, run_return) -> (bool, float), i.e. (passed, score).
"Done" is written as a program-verifiable condition instead of a model opinion -- this is
the cheapest and cleanest part of the reward layer. To point it at another domain, replace
REQUIRED_SECTIONS with your own acceptance items (pytest pass, schema check, file exists,
metric threshold).
"""
import re

REQUIRED_SECTIONS = ("abstract", "introduction", "methods", "results", "discussion")
ACCURACY_THRESHOLD = 0.0  # 0 means "non-zero passes"; set e.g. 0.6 to be stricter


def check(artifact, run_return):
    text = str(artifact).lower()
    missing = [section for section in REQUIRED_SECTIONS if section not in text]
    if missing:
        return False, 0.0

    match = re.search(r"accuracy[^0-9]*([0-9.]+)", str(run_return).lower())
    if match:
        accuracy = float(match.group(1))
        if accuracy <= ACCURACY_THRESHOLD:
            return False, 0.0
        return True, min(1.0, accuracy)

    # No objective metric available: pass the format check but score 0,
    # so the caller decides whether to fall back to another judge.
    return True, 0.0
