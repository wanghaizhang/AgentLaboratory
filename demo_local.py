"""Zero-dependency smoke run against an OpenAI-compatible endpoint (stdlib only).

Run:
  $env:LOCAL_BASE_URL = "http://127.0.0.1:8081/v1"
  $env:LOCAL_MODEL    = "qwen3.8-flash-next-iq2_xs"
  $env:LOCAL_API_KEY  = "sk-strata-..."      # key must keep the sk-strata- prefix
  py -3 demo_local.py

It shows three things the repo actually depends on:
  1. the endpoint is reachable and the model name resolves;
  2. this endpoint returns content=null with only reasoning_content, which is exactly
     the case inference.py/_text() falls back on -- without that fallback every agent
     step would come back empty;
  3. the judge layer live: objective check vs the model's self-score, and the gap.
"""
import json
import os
import re
import urllib.error
import urllib.request

import judge

BASE = os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:8081/v1").rstrip("/")
MODEL = os.getenv("LOCAL_MODEL", "qwen3.8-flash-next-iq2_xs")
KEY = os.getenv("LOCAL_API_KEY") or os.getenv("OPENAI_API_KEY") or "not-needed"
TIMEOUT = int(os.getenv("DEMO_TIMEOUT", "120"))


def call(prompt, max_tokens=400):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    msg = data["choices"][0]["message"]
    raw_content = msg.get("content")
    # same rule as inference.py/_text(): some reasoning models return only reasoning_content
    text = (raw_content or msg.get("reasoning_content") or "").strip()
    return text, raw_content, data.get("usage", {})


def objective_check(artifact, run_return):
    rules = [
        ("uses the full test set", "len(test) == 8"),
        ("prints the promised metric", "accuracy"),
        ("does not hardcode the answer", "0.75"),
    ]
    missing = [name for name, needle in rules if needle not in artifact]
    passed = len(rules) - len(missing)
    score = passed / len(rules)
    return passed == len(rules), score


def llm_scorer(plan, artifact, run_return):
    prompt = (
        "Score this artifact 0.0-1.0 for whether it satisfies the plan. "
        "Reply with a single number.\n\nPLAN:\n" + plan + "\n\nARTIFACT:\n" + artifact
    )
    text, _, _ = call(prompt, max_tokens=200)
    match = re.search(r"0?\.\d+|^[01]$", text)
    if not match:
        return None, "model gave no parseable score: " + text[:80], False
    return float(match.group(0)), "llm self-score: " + match.group(0), True


def main():
    print("== 1. endpoint ==")
    req = urllib.request.Request(BASE + "/models", headers={"Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        models = [m.get("id") for m in json.loads(resp.read().decode("utf-8")).get("data", [])]
    print("  base_url :", BASE)
    print("  models   :", models)
    if MODEL not in models:
        print("  WARN: LOCAL_MODEL 不在端点模型列表里")

    print("\n== 2. content / reasoning_content ==")
    plan = "Write a 10-line Python script that computes accuracy over the full test set of 8 items and prints 'accuracy=0.75'."
    artifact, raw_content, usage = call(plan)
    print("  raw content      :", "null" if raw_content is None else repr(raw_content[:60]))
    print("  reasoning_content: present" if raw_content is None and artifact else "  n/a")
    print("  text used by repo:", repr(artifact[:120]))
    print("  tokens           :", usage.get("total_tokens"))

    print("\n== 3. judge: objective vs model self-score ==")
    j = judge.Judge(mode="objective", checks=objective_check, llm_scorer=llm_scorer, record=[])
    score, message, is_valid = j.evaluate(plan, artifact, "", compare=True)
    print("  judge [objective]:", message)
    print("  rules: full test set / promised metric / no hardcoded answer")
    print("  recorded modes:", [r["mode"] for r in j.record])

    print("\n== 4. same artifact through the human path (no tty -> falls back to llm) ==")
    j2 = judge.Judge(mode="human", input_fn=lambda p: (_ for _ in ()).throw(EOFError("no tty")),
                     llm_scorer=llm_scorer, record=[])
    score2, message2, ok2 = j2.evaluate(plan, artifact, "")
    print("  judge [human]:", message2, "(fallback recorded:", [r["mode"] for r in j2.record], ")")

    print("\n== 5. gap report ==")
    for row in j.diff_report():
        print(f"  {row[0][:40]!r} objective={row[1]:.3f} llm={row[2]:.3f} diff={row[3]:+.3f}")
    print("\nNothing was installed for this run: only the standard library plus judge.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
