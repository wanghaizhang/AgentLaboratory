"""离线自检：验证 query_model 的通用分支能接任意模型名（不需要装 openai/tiktoken）。

跑法: py -3 test_local_dispatch.py
成功判据: 打印 calls 里 base_url=http://127.0.0.1:11434/v1、model=qwen3:8b，且 answer 非空。
"""
import sys, types, os

def stub(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

openai_stub = stub("openai")
tiktoken_stub = stub("tiktoken")
stub("anthropic")
google_stub = stub("google")
genai_stub = stub("google.generativeai")
google_stub.generativeai = genai_stub
hf_stub = stub("huggingface_hub")
hf_stub.InferenceClient = object
ds_stub = stub("datasets")
ds_stub.Dataset = object

calls = []

class FakeEnc:
    def encode(self, s):
        return list(range(len(s)))

class FakeMsg:
    def __init__(self, content):
        self.content = content
        self.reasoning_content = None

class FakeCompletion:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": FakeMsg(content)})]

class FakeClient:
    def __init__(self, api_key=None, base_url=None):
        self.base_url = base_url
        self.chat = type("Chat", (), {"completions": type("Comp", (), {"create": self._create})})()
    def _create(self, model=None, messages=None, temperature=None, stream=False):
        calls.append({"model": model, "base_url": self.base_url, "temp": temperature})
        return FakeCompletion("```PLAN\nfake plan from local model\n```")

openai_stub.OpenAI = lambda api_key=None, base_url=None: FakeClient(api_key, base_url)

def enc_for_model(name):
    if name == "cl100k_base":
        return FakeEnc()
    raise KeyError(f"no tiktoken mapping for {name}")

tiktoken_stub.encoding_for_model = enc_for_model
tiktoken_stub.get_encoding = lambda name: FakeEnc()

os.environ["LOCAL_BASE_URL"] = "http://127.0.0.1:11434/v1"
os.environ["LOCAL_MODEL"] = "qwen3:8b"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inference

ans = inference.query_model(model_str="some-local-model-name", prompt="hi", system_prompt="sys",
                            tries=1, timeout=0.1, print_cost=True)
print("ANSWER:", ans)
print("CALLS:", calls)
assert calls and calls[0]["base_url"] == "http://127.0.0.1:11434/v1", "通用分支没有走 base_url"
assert calls[0]["model"] == "qwen3:8b", "LOCAL_MODEL 没有生效"
assert "fake plan" in ans, "answer 为空（原 bug 现场）"

import utils
ans2 = utils.query_local("solve 1+1", "you are a mathematician", temperature=0.3)
print("UTILS CALLS:", calls[-1])
print("UTILS ANSWER:", ans2)
assert calls[-1]["temp"] == 0.3

print("PASS: 任意模型名 + LOCAL_BASE_URL/LOCAL_MODEL 生效，tiktoken 缺失映射时回退 cl100k_base")
