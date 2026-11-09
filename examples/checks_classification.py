"""Worked example 1 (offline, stdlib only): ticket / log classification acceptance check.

Run:  py -3 examples/checks_classification.py
The same file is what a yaml `checks:` entry points at: `check()` is the interface,
`main()` is only the offline demo.

It shows what the objective gate actually does on a real-shaped task:
  - the agent claims accuracy 0.91, but its predictions file has 198 rows against 200 gold
    labels (it sampled 2 rows) -> the round is not scored at all;
  - the second run covers all 200 rows -> it passes on the number computed from the file,
    not on the number the model printed;
  - judge-compare records both scores so the gap is visible.

Data is fabricated in-process with a fixed seed; nothing is downloaded, nothing is installed.
"""
import csv
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import judge  # repo module, stdlib only

CLASSES = ("billing", "network", "account", "other")
SEED = 20261109
GOLD = []
RNG = random.Random(SEED)
for i in range(200):
    gold = RNG.choice(CLASSES)
    # 82% of rows are predicted correctly by the rule-based classifier, remaining rows flip
    pred = gold if RNG.random() < 0.82 else RNG.choice([c for c in CLASSES if c != gold])
    GOLD.append((i, gold, pred))

# case A: predictions file missing 2 rows (sampling) -> the count gate should reject it
PRED_PATH_A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pred_198.csv")
PRED_PATH_B = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pred_200.csv")
CLAIM_A = "pipeline finished, accuracy=0.91 on the test set"   # claimed higher than computed
CLAIM_B = "pipeline finished, accuracy=0.82 on the test set"   # honest claim


def write_pred(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "pred"])
        for i, _g, p in rows:
            w.writerow([i, p])


def check(artifact, run_return):
    """artifact = predictions CSV path; run_return = what the agent claimed."""
    if not os.path.isfile(artifact):
        return False, 0.0

    rows = list(csv.DictReader(open(artifact, encoding="utf-8")))
    # gate 1: coverage — sampling is not completion
    if len(rows) != len(GOLD):
        return False, 0.0

    correct = sum(1 for r in rows if r["pred"] == GOLD[int(r["id"])][1])
    accuracy = correct / len(rows)

    # gate 2: the class that matters must not be silently bad
    billing = [r for r in rows if GOLD[int(r["id"])][1] == "billing"]
    recall = sum(1 for r in billing if r["pred"] == "billing") / max(1, len(billing))
    if recall < 0.80:
        return False, 0.0

    # gate 3: the claimed number must match the computed one
    claimed = 0.0
    for token in str(run_return).replace(",", " ").split():
        if "=" in token:
            try:
                claimed = float(token.split("=")[1])
            except ValueError:
                pass
    if claimed > accuracy + 0.02:
        return False, 0.0

    return True, accuracy


def fake_llm_scorer(plan, artifact, run_return):
    # stand-in for the LLM judge: it grades the text, not the file
    return 0.93, "llm self-score: 0.93", True


def run(label, path, j, claim):
    score, message, is_valid = j.evaluate("classify all 200 tickets and report accuracy", path, claim, compare=True)
    print(f"[{label}] rows={len(list(csv.DictReader(open(path, encoding='utf-8'))))} -> {message} valid={is_valid}")
    return score


def main():
    write_pred(PRED_PATH_A, GOLD[:198])
    write_pred(PRED_PATH_B, GOLD)

    j = judge.Judge(mode="objective", checks=check, llm_scorer=fake_llm_scorer, record=[])
    run("A: 198 rows", PRED_PATH_A, j, CLAIM_A)
    run("B: 200 rows", PRED_PATH_B, j, CLAIM_B)

    print("\ngap report (objective vs LLM self-score):")
    for row in j.diff_report():
        print(f"  {row[0]!r} objective={row[1]:.3f} llm={row[2]:.3f} diff={row[3]:+.3f}")

    for p in (PRED_PATH_A, PRED_PATH_B):
        if os.path.isfile(p):
            os.remove(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
