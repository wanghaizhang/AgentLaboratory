"""离线守卫测试（2026-11-09）：不联网，验证三个"外部服务不可用时整轮 run 不该崩"的修复。

Run: .venv\Scripts\python.exe test_guards.py
（也可用 py -3，只要 tools/inference 的依赖已装）
"""
import json
import os
import random
import tempfile
import types

import tools
import inference


def test_hf_index_guard():
    """tools.HFDataSearch: Hub 不可达时置空索引并返回，不抛异常。"""
    orig = tools.load_dataset

    def boom(*a, **k):
        raise ConnectionError(
            "Couldn't reach 'nkasmanoff/huggingface-datasets' on the Hub (LocalEntryNotFoundError)")

    tools.load_dataset = boom
    try:
        eng = tools.HFDataSearch()
        assert eng.ds == [], f"ds should be an empty index, got {type(eng.ds)}"
        assert eng.description_vectors is None, "vectors must be None when the index is unavailable"
        assert eng.retrieve_ds("math", N=3) == [], "retrieve_ds must tolerate an empty index, not crash"
    finally:
        tools.load_dataset = orig
    print("PASS guard 1 (HFDataSearch): unreachable Hub -> empty index, no exception")


def test_arxiv_guard():
    """tools.ArxivSearch.retrieve_full_paper_text: 限流时返回可读失败说明，不抛异常。"""
    class FakeClient:
        def results(self, search):
            raise Exception("Page request resulted in HTTP 429")

    orig = tools.arxiv.Client
    tools.arxiv.Client = FakeClient
    try:
        out = tools.ArxivSearch().retrieve_full_paper_text("2201.11903")
        assert isinstance(out, str) and "ARXIV UNAVAILABLE" in out, f"expected a readable fallback, got {out!r}"
    finally:
        tools.arxiv.Client = orig
    print("PASS guard 2 (ArxivSearch): rate-limited arXiv -> readable fallback string, no exception")


def test_local_retry_backoff():
    """inference.query_model: 瞬时 503 应在重试窗口内恢复；耗尽窗口后最终异常要写明窗口与最后一次错误。"""
    os.environ["LOCAL_BASE_URL"] = "http://127.0.0.1:8081/v1"
    os.environ["LOCAL_TRIES"] = "3"
    os.environ["LOCAL_BACKOFF"] = "0.01"
    os.environ["LOCAL_BACKOFF_CAP"] = "0.02"

    sleeps = []
    state = {"fail": 2, "n": 0}
    orig_sleep = inference.time.sleep
    orig_client = inference._openai_client
    orig_uniform = random.uniform
    inference.time.sleep = lambda s: sleeps.append(s)
    random.uniform = lambda a, b: 0.0  # 去抖动，断言只看确定性退避部分

    class FakeMsg:
        content = "PONG"

    def create(**kw):
        state["n"] += 1
        if state["n"] <= state["fail"]:
            raise Exception("Error code: 503 - this instance is draining; retry against the next instance")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=FakeMsg)])

    fake = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))
    inference._openai_client = lambda key=None: fake
    try:
        # 1) 前两次 503、第三次成功 -> 应当恢复而不是崩
        ans = inference.query_model("local", "hi", "", print_cost=False)
        assert ans == "PONG", f"should recover after 2 transient 503s, got {ans!r}"
        assert sleeps == [0.01, 0.02], f"backoff must grow by powers of 2, got {sleeps}"

        # 2) 窗口耗尽 -> 最终异常要带上窗口大小与最后一次错误（原来只有 'Max retries: timeout'）
        state["fail"] = 99
        state["n"] = 0
        sleeps.clear()
        msg = ""
        try:
            inference.query_model("local", "hi", "", print_cost=False)
        except Exception as e:
            msg = str(e)
        assert "Max retries (3)" in msg and "503" in msg, f"final error should name the window and last error, got {msg!r}"
        assert sleeps == [0.01, 0.02, 0.02], f"backoff must hit the cap (LOCAL_BACKOFF_CAP), got {sleeps}"
    finally:
        inference._openai_client = orig_client
        inference.time.sleep = orig_sleep
        random.uniform = orig_uniform
    print("PASS guard 3 (query_model): recovers inside the window; final error names LOCAL_TRIES and the last error")


def test_local_catalog():
    """HFDataSearch(catalog=...): 本地 JSON 目录，全程不访问 Hub。"""
    path = os.path.join(tempfile.gettempdir(), "dsh_hf_catalog_test.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump([
            {"id": "myorg/tickets", "description": "customer support tickets for classification", "likes": 12, "downloads": 80},
            {"id": "someone/noise", "description": "unrelated corpus", "likes": 1, "downloads": 2},
        ], f)

    orig_load = tools.load_dataset
    orig_builder = tools.load_dataset_builder
    tools.load_dataset = lambda *a, **k: (_ for _ in ()).throw(AssertionError("local catalog must not hit the Hub"))
    tools.load_dataset_builder = lambda *a, **k: (_ for _ in ()).throw(ConnectionError("offline"))
    try:
        eng = tools.HFDataSearch(catalog=path)
        assert len(eng.ds) == 1, f"only rows above the thresholds should survive, got {len(eng.ds)}"
        top = eng.retrieve_ds("ticket classification", N=2)
        assert len(top) == 1 and top[0]["id"] == "myorg/tickets", f"local catalog ranking should return the ticket row, got {top}"
        assert eng.results_str(top), "results_str must still produce text for a local catalog"
    finally:
        tools.load_dataset = orig_load
        tools.load_dataset_builder = orig_builder
        os.remove(path)
    print("PASS guard 4 (HFDataSearch catalog): local JSON catalog works with no Hub access")


def test_exec_timeout_override():
    """exec_timeout: EXECUTE_TIMEOUT 可覆盖，无效值/非正数回退默认，不抛异常。"""
    import ai_lab_repo as lab

    os.environ.pop("EXECUTE_TIMEOUT", None)
    assert lab.exec_timeout(120) == 120, "default must be preserved when the env var is unset"
    os.environ["EXECUTE_TIMEOUT"] = "900"
    assert lab.exec_timeout(120) == 900, "valid override must apply"
    os.environ["EXECUTE_TIMEOUT"] = "abc"
    assert lab.exec_timeout(60) == 60, "invalid value must fall back to the default"
    os.environ["EXECUTE_TIMEOUT"] = "0"
    assert lab.exec_timeout(60) == 60, "non-positive value must fall back to the default"
    os.environ.pop("EXECUTE_TIMEOUT", None)
    print("PASS guard 5 (exec_timeout): EXECUTE_TIMEOUT overrides per-phase defaults; invalid/0 falls back")


def test_reasoning_switch():
    """query_model 通用分支: 默认不注入任何额外参数；设了环境变量才关思考。"""
    os.environ["LOCAL_BASE_URL"] = "http://127.0.0.1:8081/v1"
    captured = []

    def create(**kw):
        captured.append(kw)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="PONG", reasoning_content=None))])

    fake = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))
    orig_client = inference._openai_client
    inference._openai_client = lambda key=None: fake
    saved = {k: os.environ.get(k) for k in ("LOCAL_REASONING_EFFORT", "LOCAL_ENABLE_THINKING")}
    try:
        # 1) 默认：行为与上游一致，不能注入参数
        os.environ.pop("LOCAL_REASONING_EFFORT", None)
        os.environ.pop("LOCAL_ENABLE_THINKING", None)
        captured.clear()
        assert inference.query_model("local", "hi", "", print_cost=False) == "PONG"
        assert "reasoning_effort" not in captured[0] and "extra_body" not in captured[0], \
            f"defaults must not inject params, got {captured[0]}"

        # 2) reasoning_effort 直通（实测最快：单步 1.1–3.5 s）
        os.environ["LOCAL_REASONING_EFFORT"] = "none"
        captured.clear()
        inference.query_model("local", "hi", "", print_cost=False)
        assert captured[0].get("reasoning_effort") == "none", \
            f"reasoning_effort must be passed through, got {captured[0]}"

        # 3) 模板开关走 extra_body（SDK 里 chat_template_kwargs 不是 create 的正式参数）
        os.environ.pop("LOCAL_REASONING_EFFORT", None)
        os.environ["LOCAL_ENABLE_THINKING"] = "0"
        captured.clear()
        inference.query_model("local", "hi", "", print_cost=False)
        assert captured[0].get("extra_body") == {"chat_template_kwargs": {"enable_thinking": False}}, \
            f"template switch must be sent via extra_body, got {captured[0]}"
    finally:
        inference._openai_client = orig_client
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    print("PASS guard 6 (reasoning switch): no extra params by default; LOCAL_REASONING_EFFORT / LOCAL_ENABLE_THINKING inject them")


if __name__ == "__main__":
    test_hf_index_guard()
    test_arxiv_guard()
    test_local_retry_backoff()
    test_local_catalog()
    test_exec_timeout_override()
    test_reasoning_switch()
    print("ALL GUARD TESTS PASS (offline, no network)")
