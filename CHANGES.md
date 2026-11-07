# 修改记录 (Change log)

约定：本分支（`feat/local-model-and-docs`）承载本地模型改造与文档；`main` 保持上游原样不动。后续改动走 `feat/judge-injection`。每项改动在此文件登记：日期 / 文件 / 内容 / 原因 / 验证方式。

## 2026-11-07 · 本地模型支持

| 文件 | 改动 | 原因 | 验证 |
|---|---|---|---|
| `inference.py` | `query_model` 末尾新增通用分支：未匹配硬编码模型名的任意模型名走 OpenAI 兼容端点（`LOCAL_BASE_URL`，回退 `OPENAI_BASE_URL`）；`content` 为空时回退 `reasoning_content`；未知模型成本按 `$0`、tokenizer 回退 `cl100k_base`；无 key 且无本地端点时才报 `No API key provided` | 原实现是硬编码 if/elif 链，只能用那 9 个字面量模型名 | `py -3 test_local_dispatch.py`（桩注入 `openai`/`tiktoken`，断言 base URL、模型名、temperature 透传） |
| `utils.py` | 新增 `query_local(prompt, system, api_key=None, attempt=0, temperature=0.0)` | 实验阶段生成的代码前会加 `from utils import *`，生成代码必须能调用本地端点；task-notes 需指示用 `query_local` 而非 `query_gpt4omini` | 同上自检脚本 |
| `experiment_configs/local_model_example.yaml` | 新增示例配置 | 给出可照抄的本地模型配置 | 解析层自检（见下） |
| `test_local_dispatch.py` | 新增离线自检，免 pip 安装 | 无网络/无依赖时也能验证分发逻辑 | 首次失败原因记录：桩模块必须补 `os`（`ai_lab_repo.py:16` 的 `os` 来自 `from common_imports import *`）；修正后 3 断言通过 |

## 2026-11-07 · 键名 bug 修复

- `ai_lab_repo.py` `parse_yaml`：`copilot-mode`/`copilot_mode`、`load-existing`/`load-previous` 现在互为别名。此前示例 yaml 用连字符、代码读下划线，两个开关的值被静默忽略（默认 `False`）。
- 选择"两种都认"而不是改 yaml：上游 18 个语言的 README 跑法示例与三个示例 yaml 都用连字符写法，别名方案不破坏任何现有配置。
- 验证：`py -3 test_yaml_keys.py` — 连字符 `True True`、下划线 `False true`、缺省 `False False`，全部 PASS。

## 2026-11-07 · 文档

- `README.md` 新增两节：`### ⚖️ Reward and penalty mechanism`（两条打分通路、权重表、5 类惩罚实现、top-K 淘汰、`min_gen_trials`）与 `### 🧭 Is this only for academic research?`（硬编码部分 vs 可复用骨架、需改的 4 处）。
- `readme/README-chinese.md` 同步同一两节。
- `README.md` 与中文版此前已新增 `### 🧩 Any model / local model` 节（环境变量表、行为说明、`requirements.txt` 缺 `flask`/`flask_sqlalchemy`/`sentence-transformers` 的提醒）。

## 2026-11-07 · 裁判层可注入（feat/judge-injection）

| 文件 | 改动 | 原因 | 验证 |
|---|---|---|---|
| `judge.py`（新增） | `Judge` 三模式 objective / human / llm，优先级固定 objective → human → llm；`load_checks(path)` 动态加载 checks 文件；`record` 记录每次打分的 (mode, score, candidate)，`diff_report()` 对比客观分与 LLM 自评差值 | 原 `get_score` 只有 LLM 自评，裁判无法换成程序校验或人工 | `py -3 test_judge.py` 10 组断言 PASS（纯标准库，离线可跑） |
| `test_judge.py`（新增） | 离线自检：objective pass/fail、优先级不被覆盖、human y/n/0.7 映射、human 不可用时兜底、check 抛异常视为 invalid、无裁判时 score=None、compare 记录差值不改返回值、`bind_llm` 不覆盖已有绑定 | 无网络无依赖也能验证裁判层 | 同上，全部 PASS |
| `agents.py` / `papersolver.py` / `mlesolver.py` | `get_score` 调用点改为 `self.judge.evaluate(...)`，`bind_llm` 保留原 LLM 自评实现；调用点仍用 `is_valid` 决定是否进入修复循环 | 保持原行为兼容：invalid 分由调用方的 `GLOBAL_REPAIR_ATTEMPTS` 修复循环处理 | `py -3 -m py_compile` 全文件通过；调用点逐处核对（mlesolver.py:362/389/481、papersolver.py:437/459、agents.py:197） |
| `ai_lab_repo.py` | `parse_yaml` 新增 `judge` / `checks` / `judge-checklist` / `judge-compare`；main 中构造 `Judge`，objective 模式但 checks 不可用时打印提示并实际回退 llm | 让裁判模式可由 yaml 配置 | `py -3 test_yaml_keys.py` PASS；`test_local_dispatch.py` PASS |
| `experiment_configs/local_model_example.yaml` | 新增 `judge: "objective"`、`checks`、`judge-compare`、`judge-checklist` 示例 | 给出可照抄的裁判配置 | 解析层自检（test_yaml_keys.py） |
| `checks_example.py`（新增） | checks 文件示例：`check(artifact, run_return) -> (bool, float)` | 说明客观校验的接口契约 | 与 test_judge.py 同一契约 |

### 失败与弯路（已修）

- `evaluate` 的 objective 分支写成提前 `return`，导致 `compare=True` 不再记录 LLM 自评：`test_judge.py` 用例 8 报 `AssertionError: gap should be -0.2, got []`。改为 `if/elif` 单链 + `source` 标记后通过。
- 同一写法还有第二个隐患：objective 有效时若 `mode == "human"`，人类打分会覆盖客观分（优先级被破坏）。`if/elif` 单链修掉了它，新增用例 10 覆盖（objective 有效 + mode=human → 仍取 0.8，record 只有 objective）。
- 用例 6 语义明确化：check 抛异常时 `score` 必须是 `None` 而非 `0.0`（对应旧的格式门禁失败），且不做兜底；record 只含 objective。

## 2026-11-07 · 端点实测与零依赖冒烟脚本

- 端点 `http://127.0.0.1:8081/v1`（OpenAI 兼容）实测可达：`/v1/models` 返回 `qwen3.8-flash-next-iq2_xs`；chat 正常返回但 **`content` 为 null、正文在 `reasoning_content`** ⇒ `inference.py/_text()` 的空 content 回退是必需的（实测确认）。key 必须保留 `sk-strata-` 前缀，裸 hash 报 401。
- `experiment_configs/local_model_example.yaml` 头部注释改为该端点与该模型名（key 只走环境变量，不写进仓库文件）。
- 新增 `demo_local.py`：只用标准库（urllib + judge.py），打印端点连通性、content/reasoning_content 回退、objective 与 LLM 自评的差值、human 不可用时的兜底。
- 环境事实：本机 Python 3.11.7、pip 23.2.1，但**依赖一个都没装**（openai/tiktoken/yaml/torch 等全部 ModuleNotFoundError），且 PyPI 从当前环境不可达（"基础连接已经关闭"）⇒ 主流程（`ai_lab_repo.py`）目前无法运行，只有纯标准库的自检与 `demo_local.py` 可跑。
- 验证：`py -3 demo_local.py` 实跑输出 objective/llm 双列与差值；`py -3 -c "import agents"` 在 `utils.py:4` 报 `No module named 'tiktoken'`，`import ai_lab_repo` 在 `ai_lab_repo.py:1` 报 `No module named 'PyPDF2'`。

## 未做（登记为待办）


- `requirements.txt` 未补 `flask`、`flask_sqlalchemy`、`sentence-transformers`（`ai_lab_repo.py` 会 `from app import *`）。
- 真正的端点连通性未验证（需先确认出站 TLS 与依赖安装）。
- 奖励层可注入化（objective/human/llm judge）在 `feat/judge-injection` 分支进行。
