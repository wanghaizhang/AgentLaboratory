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

## 2026-11-08 · 实跑跑通与 Windows 编码修复（feat/judge-injection）

| 文件 | 改动 | 原因 | 验证 |
|---|---|---|---|
| `ai_lab_repo.py` `parse_yaml` | 裸 `open()` → `encoding='utf-8'` | Windows 默认 GBK：含中文注释的 yaml 报 `UnicodeDecodeError: 'gbk' codec can't decode byte 0x9a`（实跑复现于 `yaml/reader.py:178`） | 实跑第一次因此失败，修后通过 |
| `ai_lab_repo.py` main | key 检查：配了 `LOCAL_BASE_URL` / `OPENAI_BASE_URL` / `LOCAL_MODEL` 时允许 key 为空并取 `LOCAL_API_KEY` | 原代码强制非空 key（`ValueError: API key must be provided…`），本地端点不需要真 key；与 `query_model` 里已有的同一条规则一致 | 实跑第二次因此失败，修后跑通 |
| `utils.py` | `save_to_file`、`compile_latex` 写文件加 `encoding='utf-8'` | Windows GBK 下写模型输出（含非 GBK 字符）会 `UnicodeEncodeError` | `py_compile` 通过；同一实跑路径 |
| `common_imports.py` | 非标准库导入全部改为可选（`_opt()` + try/except，缺失记入 `MISSING` 并绑定 `None`），仅 stdlib 与 `yaml` 强制 | 模块级 import torch/tensorflow/spacy/diffusers/plotly 使最小环境无法 import；agent 循环不需要 ML/可视化栈 | venv 内逐模块导入自检：`common_imports / judge / utils / tools / inference / agents / app / mlesolver / papersolver / ai_lab_repo` 全 OK |
| `app.py` | `sentence_transformers` 导入与 `SentenceTransformer('all-MiniLM-L6-v2')` 实例化改 guarded（`model=None` 时语义检索不可用） | `ai_lab_repo.py` 会 `from app import *`，最小安装必须能 import app；原写法在该包缺失时直接崩 | 同上自检 |
| `experiment_configs/local_model_example.yaml` | `api-key` 由 `"not-needed"` 改为 `""` | 空串在 `_openai_client()` 里是 falsy 才会继续找 `LOCAL_API_KEY`；占位串会盖掉环境变量真 key 导致 401 | 实跑确认 |

环境事实与安装：

- venv：`D:\demo\AgentLaboratory\.venv`（Python 3.11.7）。官方 PyPI 停滞 15 分钟无进展；改用 `http://mirrors.aliyun.com/pypi/simple/`（`--trusted-host mirrors.aliyun.com`）后正常。
- 已装最小可跑集：openai 3.46.0、tiktoken 0.14.0、anthropic 2.6.0、google-generativeai 0.8.6、huggingface_hub 2.4.0、PyYAML 6.0.3、pypdf 7.0.0、PyPDF2 3.0.1、datasets 5.1.0、numpy 2.4.6、pandas 3.1.1、matplotlib 3.11.2、scikit-learn 1.9.1、scipy 1.17.1、flask 3.1.3、flask_sqlalchemy 3.1.1、semanticscholar 0.12.0、psutil、requests、aiohttp、tqdm、pydantic。
- 版本漂移（实跑报错原文）：镜像装来的是 `arxiv 4.0.2`，`tools.py:266` 调用 `Result.download_pdf` → `AttributeError: 'Result' object has no attribute 'download_pdf'`；按 `requirements.txt` 钉的 `arxiv==2.1.3` 重装后该路径恢复。
- 跑法必须在仓库目录内（`checks` 与 `RESEARCH_DIR_PATH` 都是相对路径）：在 `D:\demo` 跑时 `checks_example.py` 找不到、research dir 建在 `D:\demo` 根。
- 自检（venv 内）：`test_judge.py` / `test_yaml_keys.py` / `test_local_dispatch.py` 全 PASS；真实调用经 `inference.query_model('local', …)` 返回 `'PONG'`，`content=null → reasoning_content` 回退仍生效。

## 2026-11-09 · 端到端跑通过程中的三个健壮性修复（feat/judge-injection）

| 文件 | 改动 | 原因 | 验证 |
|---|---|---|---|
| `inference.py` `query_model` | 本地/自定义端点的重试窗口由 5 次 × 5 s 改为 10 次 + 指数退避（基准 5 s、封顶 60 s、带抖动），可用 `LOCAL_TRIES` / `LOCAL_BACKOFF` / `LOCAL_BACKOFF_CAP` 调；最终异常带上最后一次错误 | 实跑报错原文：`Error code: 503 - this instance is draining; retry against the next instance` 后连续 `Connection error`，原窗口内端点没恢复，整轮 run 崩在 `Exception: Max retries: timeout`（`inference.py:248`） | `py_compile` 通过；退避序列实测 5.0 / 10.9 / 20.3 s；端点探活 3 次全 `PONG` |
| `tools.py` `HFDataSearch.__init__` | `load_dataset("nkasmanoff/huggingface-datasets")` 加 try/except：不可达时置空索引并 return（`retrieve_ds` 已能处理空 ds） | 实跑报错原文：`ConnectionError: Couldn't reach 'nkasmanoff/huggingface-datasets' on the Hub (LocalEntryNotFoundError)`，底层 `WinError 10060`；该异常在 data preparation 阶段模型开口之前抛出，整轮直接崩 | 修后实跑进入 data preparation 并产出 `src/load_data.py`（执行成功） |
| `judge.py` | `Judge` 记录 `checks_path`，`__getstate__` 丢弃函数、`__setstate__` 重新加载 | 实跑 `pickle.dump(self, f)` → `_pickle.PicklingError: Can't pickle <function check>: import of module 'user_checks' failed`（importlib 动态加载的函数不能按引用 pickle） | `test_judge.py` 新增用例 11（pickle round-trip 后 check 仍可用、score 0.6）PASS；实跑 `state_saves/Paper0.pkl` 正常写出 |
| `experiment_configs/local_model_quick_demo.yaml` | 1 篇文献 / 2 步实验 / 1 篇报告；data-preparation notes 改为"不要用 datasets/HF 下载，把 10 道题直接写进代码" | 本机 HF 不可达（`hf-mirror.com` 证书过期）；压小规模以便快速看到端到端产物 | 实跑产出 `load_data.py`，模型按约定内嵌 10 题（证据：`D:\demo\run-1108-partial\research_dir_0_lab_1\src\load_data.py`） |
| `.gitignore` | 补 `.venv/`、`data-gym-cache/`、`downloaded-paper.pdf`、`agent_times_*.txt`、`MATH_research_dir/` | 原 `venv*` 不匹配 `.venv`；运行产物会被 git 当未跟踪文件 | `git status` 干净 |

## 2026-11-09 · 离线守卫测试（不依赖外部服务响应）

- 新增 `test_guards.py`（不联网，用假对象模拟故障），三条守卫全 PASS：
  1. `HFDataSearch`：Hub 不可达 → 空索引、不抛异常；`retrieve_ds` 对空索引返回 `[]`。
  2. `ArxivSearch.retrieve_full_paper_text`：HTTP 429 → 返回可读失败字符串，而不是抛异常中断整轮。
  3. `query_model`：模拟前两次 503、第三次成功 → 在窗口内恢复（去抖动后退避序列 `[0.01, 0.02]`）；窗口耗尽后最终异常写明 `Max retries (3)` 与最后一次错误，且退避封顶 `LOCAL_BACKOFF_CAP` 生效。
- `requirements.txt` 补 `flask`、`flask_sqlalchemy`、`sentence-transformers`（此前缺失，`from app import *` 会失败）。
- 实跑边界（属外部服务与模型输出质量，不是仓库代码缺陷）：端点会 `503 this instance is draining` / `Request timed out`；模型把散文写进代码块导致 `SyntaxError: unterminated string literal (detected at line 29)`。端到端已跑通到 data preparation（产出 `src/load_data.py` 且执行成功），后续阶段受端点抖动影响。

## 2026-11-09 · HF 检索目录改为可开关（不再是硬编码必需）

- `tools.HFDataSearch`：新增 `catalog` 参数与 `HF_CATALOG` 环境变量。给本地 JSON 目录（元素含 `id`/`description`/`likes`/`downloads`）时**完全不访问 Hub**；只有两者都没有才去下载检索目录。
  - `self.ds = self.ds.select(filtered_indices)` 改为列表推导（本地目录是普通 `list`，没有 `.select`）；字段访问改 `.get`，阈值与打分逻辑不变。
- `ai_lab_repo.py`：`allow-hf-search`（默认 True）与 `hf-catalog` 进 `parse_yaml`；data preparation 里 `hf_engine` 可为 `None`，`SEARCH_HF` 分支给出明确反馈（"用 notes 里描述的数据，别发 SEARCH_HF"）而不是崩溃。
- `test_guards.py` 新增 guard 4：本地目录 + 打桩 `load_dataset`/`load_dataset_builder` ⇒ 断言不会碰 Hub，排名与 `results_str` 正常。
- `local_model_quick_demo.yaml` 显式设 `allow-hf-search: False`（该配置数据内嵌），并写明两种用法。
- 验证：`test_guards.py`（4 条）+ `test_judge.py` + `test_yaml_keys.py` + `test_local_dispatch.py` 全 PASS；`parse_yaml` 对 quick demo 读到 `False`、对 `local_model_example.yaml` 读到 `True`。commit `d6b5fbf`。

## 2026-11-09 · README 增加"科研之外的应用场景"一节

- `README.md`（License 之前）新增一节：定位（生成 → 真执行 → 按写死的验收条件判分；无奖励信号，只决定算不算完成并记录声称值/计算值差值）、场景表（分类评测 / 参数扫描 / 网络层网关验证 / 巡检合规 / 文档抽取，各含输入·门禁写法·产出）、网络层网关能验与不能验的边界、什么情况下不值得用它。
- 纯文档，无代码改动；与 `checks_example.py` 的接口描述一致（`check(artifact, run_return) -> (passed, score)`）。

## 2026-11-09 · execute_code 超时改为可配（EXECUTE_TIMEOUT）

- `ai_lab_repo.py` 新增 `exec_timeout(default)`：`EXECUTE_TIMEOUT` 环境变量覆盖单次执行超时；无效值或非正数回退默认，不抛异常。两处调用点改为 `exec_timeout(60)`（data preparation）与 `exec_timeout(120)`（running experiments）。
- 原因：原值是硬编码，慢端点下全量 500 题必超时（10 次调用 × 15–30 s 已超 120 s），只会得到 `[CODE EXECUTION ERROR]` 后进修复循环。默认值保持不变，行为默认不变。
- 验证：`test_guards.py` guard 5 —— 默认 120 保持、`900` 生效、`"abc"` 回退、`"0"` 回退。

## 未做（登记为待办）


- ~~`requirements.txt` 未补 `flask`、`flask_sqlalchemy`、`sentence-transformers`~~ 已补（2026-11-09）。
- ~~真正的端点连通性未验证~~ 已验证（2026-11-07 起端点可达，2026-11-08 起主流程可跑；剩余问题是端点会 503/超时，属运行环境）。
- 奖励层可注入化（objective/human/llm judge）在 `feat/judge-injection` 分支进行。
