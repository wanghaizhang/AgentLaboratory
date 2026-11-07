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

## 未做（登记为待办）

- `requirements.txt` 未补 `flask`、`flask_sqlalchemy`、`sentence-transformers`（`ai_lab_repo.py` 会 `from app import *`）。
- 真正的端点连通性未验证（需先确认出站 TLS 与依赖安装）。
- 奖励层可注入化（objective/human/llm judge）在 `feat/judge-injection` 分支进行。
