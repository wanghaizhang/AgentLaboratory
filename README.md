# AgentLaboratory — 本分支的实际状态（不沿用上游 README）

上游是 [SamuelSchmidgall/AgentLaboratory](https://github.com/SamuelSchmidgall/AgentLaboratory)（MIT，论文 [arXiv:2501.04227](https://arxiv.org/abs/2501.04227)）。这份 README 不复述上游原文，只写这个 fork 在 `feat/judge-injection` 分支上**实际改了什么、怎么配、怎么跑、哪些数字是实测过的、哪些事不能指望它做**。上游原文与 18 个语言版本（含 `readme/README-chinese.md`，那是上游译文，保持原样）仍在上游仓库。

## 一句话

**生成 → 真执行 → 按写死的验收条件判分**。价值全在"验收条件可程序化"这一条上；它不训练模型、没有奖励信号，验证只决定两件事：这一轮算不算完成，以及把"程序算出的分"与"模型自己给的分"并排记下来。

## 改了什么（对照表）

| 上游行为 | 本分支 | 验证方式 |
|---|---|---|
| `query_model` 是硬编码 if/elif，只认 9 个字面量模型名 | 末尾加通用分支：任意模型名走 OpenAI 兼容端点（`LOCAL_BASE_URL`，回退 `OPENAI_BASE_URL`）；`content` 为空时回退 `reasoning_content`；未知模型成本按 `$0`、tokenizer 回退 `cl100k_base` | `test_local_dispatch.py`（桩注入，断言 base URL / 模型名 / temperature 透传） |
| 无思考开关 | 通用分支新增 `LOCAL_REASONING_EFFORT`（直通 `reasoning_effort`）与 `LOCAL_ENABLE_THINKING=0`（经 `extra_body` 传 `chat_template_kwargs.enable_thinking`）；不设时不注入任何参数 | `test_guards.py` guard 6 + 同一代码路径实跑（见下数字） |
| 重试窗口 5 次 × 5 s | 本地端点 10 次 + 指数退避（基准 5 s、封顶 60 s、带抖动），`LOCAL_TRIES` / `LOCAL_BACKOFF` / `LOCAL_BACKOFF_CAP` 可调；最终异常写明窗口与最后一次错误 | guard 3：模拟两次 503 后恢复（退避 `[0.01, 0.02]`），耗尽后错误含 `Max retries (3)` 与 503 原文 |
| HuggingFace 检索目录是硬编码必需 | 可开关：`catalog` 参数 + `HF_CATALOG` 环境变量给本地 JSON 目录时完全不碰 Hub；不可达时置空索引并继续 | guard 1（Hub 不可达 → 空索引不抛异常）、guard 4（本地目录 + 打桩断言不碰 Hub） |
| arXiv 限流会抛出异常中断整轮 | 返回可读失败字符串（`ARXIV UNAVAILABLE`），不抛异常 | guard 2（HTTP 429 → 可读回退） |
| `execute_code` 超时硬编码 | `exec_timeout(default)`：`EXECUTE_TIMEOUT` 可覆盖（data preparation 60 s、running experiments 120 s），无效值或非正数回退默认 | guard 5（默认保持 / 900 生效 / `"abc"` 回退 / `"0"` 回退） |
| 打分只有 LLM 自评 | 新增 `judge.py`：objective / human / llm 三模式，优先级固定 objective → human → llm；`load_checks(path)` 动态加载 checks 文件；`record` 记录每次 (mode, score, candidate)，`diff_report()` 给出客观分与自评差值 | `test_judge.py` 11 组断言（纯标准库、离线）；含 pickle round-trip（checks 函数不可按引用 pickle，`__getstate__` 丢弃、`__setstate__` 重载） |
| `get_score` 直接调 LLM | `agents.py` / `papersolver.py` / `mlesolver.py` 调用点改 `self.judge.evaluate(...)`；`bind_llm` 保留原实现，无裁判时 `score=None` | `py_compile` 全文件 + 调用点逐处核对 |
| yaml 连字符键被静默忽略 | `parse_yaml` 认 `copilot-mode`/`copilot_mode`、`load-existing`/`load-previous` 互为别名；新增 `judge` / `checks` / `judge-checklist` / `judge-compare` / `allow-hf-search` / `hf-catalog` | `test_yaml_keys.py`（连字符、下划线、缺省三种情形） |
| 裸 `open()` 用系统默认编码 | `parse_yaml` 与 `utils.save_to_file` / `compile_latex` 加 `encoding='utf-8'`（Windows 默认 GBK，含中文注释的 yaml 会 `UnicodeDecodeError`，模型输出含非 GBK 字符会 `UnicodeEncodeError`） | 实跑复现并修正 |
| 模块级 import torch/tensorflow/spacy/… | `common_imports.py` 非标准库导入全部改可选（缺失记入 `MISSING` 并绑 `None`）；`app.py` 的 `SentenceTransformer` 改 guarded | venv 内逐模块导入自检：`common_imports / judge / utils / tools / inference / agents / app / mlesolver / papersolver / ai_lab_repo` 全 OK |
| `requirements.txt` 缺 `flask` / `flask_sqlalchemy` / `sentence-transformers` | 已补（`from app import *` 会失败） | 安装与导入自检 |

## 配置

命令行只有一个参数：`--yaml-location`，其余全在 yaml 里。

```bash
# 依赖装进仓库内的 venv，缓存指到工作区
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt --no-cache-dir

# 端点只走环境变量，key 不写进仓库文件
$env:LOCAL_BASE_URL = 'http://127.0.0.1:8081/v1'
$env:LOCAL_MODEL    = 'qwen3.8-flash-next-iq2_xs'
$env:LOCAL_API_KEY  = 'sk-…'
$env:EXECUTE_TIMEOUT = '900'          # 可选，默认 60/120
$env:LOCAL_REASONING_EFFORT = 'none'  # 可选，跑批建议开
$env:HF_CATALOG     = 'hf_catalog.json'  # 可选，给本地目录就不碰 Hub

.venv\Scripts\python.exe ai_lab_repo.py --yaml-location "experiment_configs/local_model_quick_demo.yaml"
```

**必须在仓库目录内跑**：`checks` 与 `RESEARCH_DIR_PATH` 都是相对路径，在上一级目录跑会找不到 checks 文件、research dir 建在错误位置。

yaml 里裁判相关键：

```yaml
research-topic: "对 tickets.csv 做四分类并输出逐条预测"
judge: objective                       # objective > human > llm
checks: "examples/checks_classification.py"   # 须定义 check(artifact, run_return) -> (bool, float)
judge-compare: True                    # 把程序分与自评并排记录（差值写进 record）
judge-checklist: ["抽 10 份核对金额字段"]      # 仅当 objective 不可用时才走 human
allow-hf-search: false
compile-latex: false
copilot-mode: "false"
task-notes:
  running experiments:
    - 'Write predictions.csv with columns id,pred; do not sample.'
    - 'Print accuracy=<value> computed from the file, not estimated.'
```

## 已验证的数字（带日期）

- **离线守卫全 PASS（2026-11-09）**：`test_guards.py` 6 条 + `test_judge.py` 11 组 + `test_yaml_keys.py` + `test_local_dispatch.py`，不联网、用假对象模拟故障。
- **单步延迟（2026-11-09，端点 `http://127.0.0.1:8081/v1`、`temperature=0`）**：开思考 mean 7.2 s、约 26 tok/s（40 tokens 3.3/1.8/1.5 s、400 tokens 6.4 s、600 tokens 22.7 s）。关闭思考后同一 prompt：2.5 s → `reasoning_effort=none` 0.8 s → `enable_thinking=0` 0.6 s；常规单步由 3–9 s 降到 1–3.5 s。**只有这两种参数有效**：`reasoning_effort=none|minimal`、顶层 `chat_template_kwargs.enable_thinking=false`（走 SDK 必须用 `extra_body`）；`thinking={"type":"disabled"}` 与 prompt 前缀 `/no_think` 被端点忽略。质量抽样未见退化。
- **门禁耗时**：objective 单次判定 0.00 ms、`load_checks` 7 ms；有 checks 时 objective 路径不产生 LLM 调用（`judge.py:115-128`）。只有 `judge-compare: True` 会每候选多一次调用（按 26 tok/s 约 +10–25 s）。
- **实跑输出**（`py -3 examples/checks_classification.py`，离线打桩、无需 pip）：

  ```
  [A: 198 rows] objective: pass=False score=0.000 | llm=0.930 diff=-0.930
  [B: 200 rows] objective: pass=True  score=0.820 | llm=0.930 diff=-0.110
  ```

  A 那轮模型自评 0.93，但文件只有 198 行 ⇒ 整轮作废（不是扣分）。这就是这个项目的实际价值：它不能靠嘴说完成。
- **耗时估算**：最小配置（1 篇文献 / 2 步实验 / 1 篇报告，15–25 次调用）开思考 3–8 分钟 + 执行 60–120 s；关闭思考后按单步 1–3.5 s 估算。全量 500 题开思考约 1–2 小时，关闭后约 30–60 分钟量级；两档都必须把 `EXECUTE_TIMEOUT` 抬到 900，否则 120 s 直接判执行失败。真数字看 `agent_times_{lab_index}.txt`（`ai_lab_repo.py:878-881`）。
- **401 的第一嫌疑是 key 大小写**（不是过期）：记忆里的 key 曾被存成小写副本，原样大小写即通过。key 必须保留 `sk-` 前缀，裸 hash 报 401。

## 场景（非科研任务的用法）

十个可照抄的例子，每个按 **输入 → 断言 → 产出 → 失败长什么样** 写：

| 场景 | 输入 | 断言（写在 checks 里） | 产出 |
|---|---|---|---|
| 分类评测 | 200 行 CSV + gold label | 预测行数必须 == 输入行数（防抽样）；accuracy 由文件算出；关键类别 recall ≥ 0.80；声称值与计算值差 ≤ 0.02 | `predictions.csv` + 评测脚本 + 差值记录 |
| 参数扫描 | 20 样本 × 60 组网格 | 结果表必须 60 行；p99 与输出体积逐条算；与基线 3 个样本输出逐字符一致；跳过的样本必须列在 `skipped.json` | `sweep.csv` + 汇总脚本 |
| 网络层网关 | 12 条路由 + 期望状态码表 + 故障注入 | 全部 12 条都有记录；状态码逐条一致；注入 503 的两条 `retry_count >= 3` 且退避单调递增；裸 key 必须 401、带前缀才 200；DNS 与证书链通过 | `gateway_report.json` + 断言脚本 |
| 巡检与合规 | 100 项清单 + 上月报告 | 覆盖全部 100 项（覆盖率由脚本算，不接受"已完成"）；列名集合与历史报告一致；上月 3 个已知异常本次必须仍被报出 | 巡检脚本 + 覆盖率 + 异常清单 |
| 文档抽取 | 40 份文件 + 必抽字段 | 40 份都有输出；金额可解析为数字且与原文一致（幻觉判负）；缺失字段写 `null` 不能省略；抽样 10 份走 human judge | `extract.jsonl` + 异常清单 |
| 补测试 / 修 bug | 一个失败用例 + 源码 | pytest 全绿；覆盖率 ≥ 80%；**测试文件哈希与基线一致**（防"改测试让绿灯"）；断言值来自 fixture 不硬编码 | patch + 测试报告 |
| API 客户端 | mock server 逐条打状态码 + 错误分类表 | 429 → 重试且退避 `[1,2,4]`；401 → 不重试立刻返回错误类型；超时率 < 5%；连接复用（同一 session）；SSE 按序到达 | `client.py` + `calls.jsonl` |
| 配置校验器 | 30 份配置（8 份已知坏） | 8 份必须全报错（漏报 0）；22 份好配置误报 0；每条错误带字段路径 | `validator.py` + `errors.jsonl` |
| 作业批改 | 20 份提交 + 标准输入输出 | 隔离目录跑通且逐条比对；超时视为不通过而不是报错；越界写盘或访问网络视为不通过 | `grades.csv` |

这十个例子满足的三个共同条件决定值不值得用它：**产物可枚举、断言可程序化、失败可归因**。缺任何一个就退回普通 chat。

## 已知边界

- **没有奖励函数，也没有训练信号**。所谓"奖惩"是 LLM 裁判 + 格式/执行门禁 + top-K 池淘汰（`max_codes`、`max_papers`、`min_gen_trials`）。分数不跨 run 累积。
- 弱模型做裁判会**自评偏松**，且严格格式（```` ```SCORE ``` ``、评审 JSON、```` ```EDIT N M ````）失败率更高 ⇒ 很多轮 `score=None`。裁判最好留在强模型，或换成 objective checks。
- `judge: objective` 但 checks 文件加载失败时**不会退出**，会打印提示并回退 LLM 自评（`ai_lab_repo.py:819-820`）——这时跑的还是自评，分数好看但没有门禁。
- 网络层只能验"能写成脚本断言的部分"（状态码、重试、退避、覆盖率、哈希、SSE 顺序）；"策略是否合理""某条 ACL 该不该存在"不在系统里。无网络时只能验到打桩那一层（guard 就是打桩版）。
- 端点会 `503 this instance is draining` / 请求超时；模型会把散文写进代码块导致 `SyntaxError: unterminated string literal`。这属运行环境与输出质量，不是代码缺陷。
- 模型输出可能只有 `reasoning_content`（`content` 为空）——回退逻辑存在的原因；把思考关掉可避免 token 预算被 reasoning 吃满。
- `pdflatex` 可选（没有 sudo 就 `compile-latex: false`）；本机无 `make`；依赖必须装进仓库内 venv，不装全局。

## 自检脚本（离线、不联网）

```bash
.venv\Scripts\python.exe test_guards.py          # 6 条守卫
.venv\Scripts\python.exe test_judge.py           # 11 组断言
.venv\Scripts\python.exe test_yaml_keys.py
.venv\Scripts\python.exe test_local_dispatch.py  # 免 pip（桩注入）
py -3 examples/checks_classification.py           # 离线演示两个 case
```

## License 与引用

MIT。上游引用 bibtex：`schmidgall2025agentlaboratory`（[arXiv:2501.04227](https://arxiv.org/abs/2501.04227)）、`schmidgall2025agentrxiv`（[arXiv:2503.18102](https://arxiv.org/abs/2503.18102)）。改动记录见 [CHANGES.md](CHANGES.md)。
