"""离线自检：yaml 键名别名（copilot-mode / load-existing 现在与 copilot_mode / load-previous 等效）。

跑法: py -3 test_yaml_keys.py
成功判据: 三种写法都能被 parse_yaml 正确取值。
"""
import sys, types, os

HERE = os.path.dirname(os.path.abspath(__file__))

def stub(name, attrs=None):
    m = types.ModuleType(name)
    for k, v in (attrs or {}).items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

captured = {}
stub("yaml", {"safe_load": lambda f: captured["data"]})
stub("PyPDF2")
stub("app")
stub("agents")
# 真实代码靠 `from common_imports import *` 拿到 os，桩必须补上
stub("common_imports", {"os": os, "sys": sys})
stub("mlesolver", {"MLESolver": object})

sys.path.insert(0, HERE)
import ai_lab_repo

def run(data):
    captured["data"] = data
    tmp = os.path.join(HERE, "_tmp_yaml_keys.yaml")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("placeholder")   # 桩 yaml 忽略文件内容，只回传 captured["data"]
    p = ai_lab_repo.parse_yaml(tmp)
    os.remove(tmp)
    return p

p1 = run({"copilot-mode": True, "load-existing": True})
assert p1.copilot_mode is True and p1.load_previous is True, "连字符写法仍未被读取"

p2 = run({"copilot_mode": False, "load-previous": "true"})
assert p2.copilot_mode is False and p2.load_previous == "true", "下划线写法回归失败"

p3 = run({})
assert p3.copilot_mode is False and p3.load_previous is False, "缺省值不对"

print("PASS: parse_yaml 现在两种写法都认 (copilot-mode/copilot_mode, load-existing/load-previous)")
print("  hyphen form ->", p1.copilot_mode, p1.load_previous)
print("  underscore  ->", p2.copilot_mode, p2.load_previous)
print("  default     ->", p3.copilot_mode, p3.load_previous)
