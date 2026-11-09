# Agent Laboratory: Using LLM Agents as Research Assistants


<p align="center">
  <img src="media/AgentLabLogo.png" alt="Demonstration of the flow of AgentClinic" style="width: 99%;">
</p>

<p align="center">
    【English | <a href="readme/README-chinese.md">中文</a> | <a href="readme/README-japanese.md">日本語</a> | <a href="readme/README-korean.md">한국어</a> | <a href="readme/README-filipino.md">Filipino</a> | <a href="readme/README-french.md">Français</a> | <a href="readme/README-slovak.md">Slovenčina</a> | <a href="readme/README-portugese.md">Português</a> | <a href="readme/README-spanish.md">Español</a> | <a href="readme/README-turkish.md">Türkçe</a> | <a href="readme/README-hindi.md">हिंदी</a> | <a href="readme/README-bengali.md">বাংলা</a> | <a href="readme/README-vietnamese.md">Tiếng Việt</a> | <a href="readme/README-russian.md">Русский</a> | <a href="readme/README-arabic.md">العربية</a> | <a href="readme/README-farsi.md">فارسی</a> | <a href="readme/README-italian.md">Italiano</a>】
</p>

<p align="center">
    【📝 <a href="https://arxiv.org/pdf/2501.04227">Paper</a> | 🌐 <a href="https://agentlaboratory.github.io/">Website</a> | 🌐 <a href="https://agentrxiv.github.io/">AgentRxiv Website</a> | 💻 <a href="https://github.com/SamuelSchmidgall/AgentLaboratory">Software</a> | 📰 <a href="https://agentlaboratory.github.io/#citation-ref">Citation</a>】
</p>

### News 
* [March/24/2025] 🎉 🎊 🎉 Now introducing **AgentRxiv**, a framework where autonomous research agents can upload, retrieve, and build on each other’s research. This allows agents to make cumulative progress on their research.

## 📖 Overview

- **Agent Laboratory** is an end-to-end autonomous research workflow meant to assist **you** as the human researcher toward **implementing your research ideas**. Agent Laboratory consists of specialized agents driven by large language models to support you through the entire research workflow—from conducting literature reviews and formulating plans to executing experiments and writing comprehensive reports. 
- This system is not designed to replace your creativity but to complement it, enabling you to focus on ideation and critical thinking while automating repetitive and time-intensive tasks like coding and documentation. By accommodating varying levels of computational resources and human involvement, Agent Laboratory aims to accelerate scientific discovery and optimize your research productivity.
<p align="center">
  <img src="media/AgentLab.png" alt="Demonstration of the flow of AgentClinic" style="width: 99%;">
</p>

- Agent Laboratory also supports **AgentRxiv**, a framework where autonomous research agents can upload, retrieve, and build on each other’s research. This allows agents to make cumulative progress on their research.

<p align="center">
  <img src="media/agentrxiv.png" alt="Demonstration of the flow of AgentClinic" style="width: 99%;">
</p>


### 🔬 How does Agent Laboratory work?

- Agent Laboratory consists of three primary phases that systematically guide the research process: (1) Literature Review, (2) Experimentation, and (3) Report Writing. During each phase, specialized agents driven by LLMs collaborate to accomplish distinct objectives, integrating external tools like arXiv, Hugging Face, Python, and LaTeX to optimize outcomes. This structured workflow begins with the independent collection and analysis of relevant research papers, progresses through collaborative planning and data preparation, and results in automated experimentation and comprehensive report generation. Details on specific agent roles and their contributions across these phases are discussed in the paper.

<p align="center">
  <img src="media/AgentLabWF.png" alt="Demonstration of the flow of AgentClinic" style="width: 99%;">
</p>


### 👾 Currently supported models

* **OpenAI**: o1, o1-preview, o1-mini, gpt-4o, o3-mini
* **DeepSeek**: deepseek-chat (deepseek-v3)

To select a specific llm set the flag `--llm-backend="llm_model"` for example `--llm-backend="gpt-4o"` or `--llm-backend="deepseek-chat"`. Please feel free to add a PR supporting new models according to your need!

### 🧩 Any model / local model (this change, 2026-11-07)

Model selection is no longer limited to the literal names above. `query_model` in `inference.py` now ends with a generic branch: **any model name** is sent to an OpenAI-compatible endpoint (local vLLM, Ollama, LM Studio, or a self-hosted gateway) through environment variables. The known names above still keep their original branches.

| Variable | Purpose |
|---|---|
| `LOCAL_BASE_URL` | endpoint base URL; falls back to `OPENAI_BASE_URL` |
| `LOCAL_MODEL` | model name sent to the endpoint; falls back to the `llm-backend` value |
| `LOCAL_API_KEY` | key for the endpoint; local servers usually need none; falls back to `OPENAI_API_KEY`, then `not-needed` |

Example:

```bash
export LOCAL_BASE_URL="http://127.0.0.1:8000/v1"
export LOCAL_MODEL="qwen3:8b"
python ai_lab_repo.py --yaml-location "experiment_configs/local_model_example.yaml"
```

Behaviour notes:

- An API key is no longer required when a local endpoint is configured; the old `No API key provided` check only fires when neither a key nor a local endpoint is set.
- Some reasoning servers return an empty `content`; the code falls back to `reasoning_content`.
- Cost printing: unknown model names cost `$0` and the tokenizer falls back to `cl100k_base`, so the printed cost is only approximate for non-OpenAI models.
- The experiment phase calls `utils.query_local(prompt, system, api_key=None, attempt=0, temperature=0.0)`, because generated code always gets `from utils import *`. Task-notes must therefore tell the agent to use `query_local` instead of `query_gpt4omini` — see [experiment_configs/local_model_example.yaml](experiment_configs/local_model_example.yaml).
- Offline self-check that needs no pip install: `python test_local_dispatch.py` (stub-injects `openai`/`tiktoken` and asserts base URL, model name and temperature passthrough).
- `copilot-mode` and `load-existing` in the yaml are now accepted as aliases of `copilot_mode` and `load-previous`; before this fix the example configs' values for both flags were silently ignored.
- Still missing from `requirements.txt` although `ai_lab_repo.py` imports `app.py` (Flask + SQLAlchemy + sentence-transformers): install `flask`, `flask_sqlalchemy`, `sentence-transformers` or the import fails. Reward/reviewer quality depends on strict output formats (```` ```SCORE ````, exact review JSON, ```` ```EDIT N M ````), so a small local model degrades the search loop; a mixed setup (local backbone, stronger model for `lit-review-backend`/reward) is recommended.

### ⚖️ Reward and penalty mechanism (how scoring actually works)

There is **no reward function in the RL sense and no training signal** — nothing is fine-tuned and no score accumulates across runs. The two `# todo: have a reward function here` comments ([agents.py:40](agents.py#L40), [mlesolver.py:145](mlesolver.py#L145)) are the honest state of things: the "reward model" is a judge prompt. The mechanism is three parts — **LLM judge + format/execution gates + top-K archive pruning**.

Two scoring paths:

1. **Code phase** — `get_score` in [mlesolver.py:141-163](mlesolver.py#L141-L163): a "professor" judge reads plan + code + run output and returns a float **0–1**. It must emit exactly ```` ```SCORE\n<float>\n``` ```, at `temp=0.6`, 3 attempts; on any exception it returns `None`, so that attempt is not scored.
2. **Report phase** — `get_score` in [agents.py:36-181](agents.py#L36-L181): a NeurIPS-style review as strict JSON, each rating normalised then weighted:

| Dimension | Scale | Weight |
|---|---|---|
| Overall | 1–10 | **1.0** |
| Contribution | 1–4 | **0.4** |
| Presentation | 1–4 | **0.2** |
| Clarity / Quality / Soundness / Significance / Originality | 1–4 | 0.1 each |
| Confidence | 1–5 | 0.1 |

`performance = weighted_sum / 2.2 × 10`, i.e. **0–10**. Confidence counts, so the number partly measures how sure the judge is, not only work quality. Three reviewer personas ([agents.py:192-199](agents.py#L192-L199)) score separately and are qualitative pressure only. The score is printed at the end of each phase ([ai_lab_repo.py:263](ai_lab_repo.py#L263), [ai_lab_repo.py:329](ai_lab_repo.py#L329)).

Penalties are never numeric deductions — they are "**this round does not count**":

1. Missing sections (abstract/introduction/methods/results/discussion) must reduce the review score ([agents.py:135](agents.py#L135)); `Ethical Concerns: true` flags an ethics review.
2. **Format gate**: an `EDIT`/`REPLACE` that fails to parse, a missing scaffold placeholder, `documentclass`/`usepackage` inside section text, or unparsable JSON ⇒ `is_valid=False`, `score=None`, and the edit is **reverted**; the error text goes back into the agent's history ([papersolver.py:440](papersolver.py#L440), [papersolver.py:461](papersolver.py#L461)).
3. **Execution gate**: `[CODE EXECUTION ERROR]` or no `submission.csv` ⇒ no score, only a reflection prompt ([mlesolver.py:472-487](mlesolver.py#L472-L487)); accuracy must not be 0% ([mlesolver.py:445](mlesolver.py#L445)).
4. **Archive pruning — the real punishment**: `best_codes` (`max_codes`, default 1) and `best_report` (`max_papers`) are score-descending pools. A new candidate enters only if `top_score > best[-1]`; when full, the **lowest** is popped ([mlesolver.py:309-316](mlesolver.py#L309-L316), [papersolver.py:297-303](papersolver.py#L297-L303)). The next round's base is drawn with `random.choice(best_codes)` ([mlesolver.py:291](mlesolver.py#L291)) — a low-scoring solution loses the right to be the parent. `min_gen_trials` (1 for code, 2 for paper) forces a minimum number of attempts before a score is accepted, so one lucky run cannot decide the outcome.

Practical consequence for a local model: a weaker judge grades itself leniently, so the reward becomes inflated noise, and the strict formats above fail more often ⇒ many rounds produce `score=None`. Keep the judge (and `lit-review-backend`) on a strong model, or replace it with an objective check.

### 🧭 Is this only for academic research?

**Out of the box, yes** — it produces a LaTeX paper, because the research shape is hardcoded:

- The phase list is a research workflow ([ai_lab_repo.py:60-65](ai_lab_repo.py#L60-L65)): literature review → plan formulation → experimentation → results interpretation → report writing/refinement.
- The tools are research tools: arXiv search/full text ([tools.py:200-264](tools.py#L200-L264)), `pdflatex` compilation ([utils.py:155-188](utils.py#L155-L188)), citation by arXiv ID.
- The success condition is a research success condition: a compiling paper with eight sections, `submission.csv`, non-zero accuracy, and a conference-style review as the reward.
- Agent personas are research personas (PhD student, postdoc, professor, MLE) and the reward rubric is a NeurIPS form.

**The skeleton itself is domain-agnostic**, and that is what is worth reusing: `BaseAgent` (dialogue + notes) + a `Command` registry + a solver loop of *act → judge → keep top-K*. To point it at something else (a code task, an ops runbook, a data pipeline, an evaluation harness) four things must change, and only those four:

1. Phase list and prompts — [ai_lab_repo.py:60-65](ai_lab_repo.py#L60-L65), phase prompts in [agents.py](agents.py).
2. Tool registry — the `Command` classes in [papersolver.py](papersolver.py) / [tools.py](tools.py): replace arXiv/LaTeX with your own executable actions.
3. Reward — replace the subjective rubric with an **objective acceptance test** (pytest, schema check, metric threshold). Without this, a judge grading itself is all you have.
4. Output artifact — `report.txt`/PDF becomes whatever "done" means for your task.

If the target is not a paper, do not keep the reviewer rubric: `copilot-mode` + `task-notes` is the cheaper path — the human becomes the judge, and the top-K archive still works as a survivor-selection mechanism.

## 🖥️ Installation

### Python venv option

* We recommend using python 3.12

1. **Clone the GitHub Repository**: Begin by cloning the repository using the command:
```bash
git clone git@github.com:SamuelSchmidgall/AgentLaboratory.git
```

2. **Set up and Activate Python Environment**
```bash
python -m venv venv_agent_lab
```
- Now activate this environment:
```bash
source venv_agent_lab/bin/activate
```

3. **Install required libraries**
```bash
pip install -r requirements.txt
```

4. **Install pdflatex [OPTIONAL]**
```bash
sudo apt install pdflatex
```
- This enables latex source to be compiled by the agents.
- **[IMPORTANT]** If this step cannot be run due to not having sudo access, pdf compiling can be turned off via running Agent Laboratory via setting the `--compile-latex` flag to false: `--compile-latex "false"`



5. **Now run Agent Laboratory!**

`python ai_lab_repo.py --yaml-location "experiment_configs/MATH_agentlab.yaml"`


### Co-Pilot mode

To run Agent Laboratory in copilot mode, simply set the copilot-mode flag in your yaml config to `"true"`

-----
## Tips for better research outcomes


#### [Tip #1] 📝 Make sure to write extensive notes! 📝

**Writing extensive notes is important** for helping your agent understand what you're looking to accomplish in your project, as well as any style preferences. Notes can include any experiments you want the agents to perform, providing API keys, certain plots or figures you want included, or anything you want the agent to know when performing research.

This is also your opportunity to let the agent know **what compute resources it has access to**, e.g. GPUs (how many, what type of GPU, how many GBs), CPUs (how many cores, what type of CPUs), storage limitations, and hardware specs.

In order to add notes, you must modify the task_notes_LLM structure inside of `ai_lab_repo.py`. Provided below is an example set of notes used for some of our experiments. 


```
task-notes:
  plan-formulation:
    - 'You should come up with a plan for only ONE experiment aimed at maximizing performance on the test set of MATH using prompting techniques.'
    - 'Please use gpt-4o-mini for your experiments'
    - 'You must evaluate on the entire 500 test questions of MATH'
  data-preparation:
    - 'Please use gpt-4o-mini for your experiments'
    - 'You must evaluate on the entire 500 test questions of MATH'
    - 'Here is a sample code you can use to load MATH\nfrom datasets import load_dataset\nMATH_test_set = load_dataset("HuggingFaceH4/MATH-500")["test"]'
...
```

--------

#### [Tip #2] 🚀 Using more powerful models generally leads to better research 🚀

When conducting research, **the choice of model can significantly impact the quality of results**. More powerful models tend to have higher accuracy, better reasoning capabilities, and better report generation. If computational resources allow, prioritize the use of advanced models such as o1-(mini/preview) or similar state-of-the-art large language models.

However, **it’s important to balance performance and cost-effectiveness**. While powerful models may yield better results, they are often more expensive and time-consuming to run. Consider using them selectively—for instance, for key experiments or final analyses—while relying on smaller, more efficient models for iterative tasks or initial prototyping.

When resources are limited, **optimize by fine-tuning smaller models** on your specific dataset or combining pre-trained models with task-specific prompts to achieve the desired balance between performance and computational efficiency.

-----

#### [Tip #3] ✅ You can load previous saves from checkpoints ✅

**If you lose progress, internet connection, or if a subtask fails, you can always load from a previous state.** All of your progress is saved by default in the `state_saves` variable, which stores each individual checkpoint. 

-----


#### [Tip #4] 🈯 If you are running in a language other than English 🈲

If you are running Agent Laboratory in a language other than English, no problem, just make sure to provide a language flag to the agents to perform research in your preferred language. Note that we have not extensively studied running Agent Laboratory in other languages, so be sure to report any problems you encounter.

For example, if you are running in Chinese set the language in the yaml:

`language:  "中文"`

----


#### [Tip #5] 🌟 There is a lot of room for improvement 🌟

There is a lot of room to improve this codebase, so if you end up making changes and want to help the community, please feel free to share the changes you've made! We hope this tool helps you!


## 🧭 科研之外的应用场景（本分支补充，2026-11-09）

一句话定位：它本质是 **生成 → 真执行 → 按你写死的验收条件判分** 的循环。价值全部落在"验收条件可程序化"这一条上。它不训练模型，也不产生奖励信号；验证结果只决定两件事——这次算不算完成，以及把"程序算出的分"和"模型自己给的分"并排记下来（`judge-compare: True`）。

输入只有两样：**topic + checks 文件**（`check(artifact, run_return) -> (passed, score)`，优先级 objective > human > llm）。

| 场景 | 输入 | 门禁怎么写 | 产出 |
|---|---|---|---|
| 分类评测（工单、日志、标签） | 200 行 CSV + gold label | 预测文件行数必须 == 输入行数（防抽样）；accuracy 由文件算出；阈值 | 可复用评测脚本 + 逐条预测 + 声称值/计算值差值 |
| 参数扫描 | 20 个样本 × 参数网格 | 网格必须全跑完；两个指标（如 p99 时间、输出体积）；与基准哈希一致 | 扫描脚本 + 结果表 |
| 网络层网关 / 链路验证 | 路由清单 + 期望状态码表 + 注入的故障点 | 全部 N 条路由都要打到；实际状态码与期望表一致；注入 503 的那两条要看到重试次数与退避递增；DNS、证书链校验通过 | `gateway_report.json` + 断言脚本 |
| 巡检与合规 | 100 项清单 + 历史报告 | 脚本覆盖全部 100 项；字段与历史报告一致；抽样人工核对通过 | 巡检脚本 + 覆盖率 |
| 文档 / 合同抽取 | 一批文件 + 必抽字段 | 字段齐全 + 格式校验 + 抽样核对 | 抽取脚本 + 异常清单 |

### 具体例子（每个都写成：输入 → 断言 → 产出 → 失败长什么样）

#### 例 1 · 工单/日志分类评测（最典型，且这个例子在仓库里可直接跑）

- **输入**：`tickets.csv` 200 行，每行有文本和 gold label（4 类：billing / network / account / other）。
- **断言**（checks 文件里写死）：① 预测文件行数必须 == 200（抽样不算完成）；② accuracy 由文件逐行算出，不采信模型打印的数字；③ `billing` 类 recall ≥ 0.80（关键类别不能悄悄差）；④ 声称值与计算值差 ≤ 0.02。
- **产出**：`predictions.csv` + 可复用的评测脚本 + 声称值/计算值差值记录。
- **实跑结果**（`py -3 examples/checks_classification.py`，离线打桩，无需 pip）：

```
[A: 198 rows] objective: pass=False score=0.000 | llm=0.930 diff=-0.930
[B: 200 rows] objective: pass=True  score=0.820 | llm=0.930 diff=-0.110
```

读法：A 那轮模型自评 0.93，但文件只有 198 行 ⇒ `score=0` 且这一轮不进 top-K 池（门禁把整轮作废，不是扣分）。B 通过后仍然比自评低 0.11 —— 这个差值就是 `judge-compare: True` 记录下来的东西。这个项目的实际价值不在"它会写代码"，在"它不能靠嘴说完成"。

#### 例 2 · 网络层网关 / 链路验证

- **输入**：`routes.yaml`（12 条路由）+ `expected_status.csv`（逐条期望状态码）+ 故障注入清单（其中 2 条必须回 503）。
- **断言**：12 条路由全部有记录（coverage == 12，不许抽样）；实际状态码逐条与期望表一致；注入 503 的那两条必须看到 `retry_count >= 3` 且退避序列单调递增（`[1, 2, 4]`）；裸 key 必须 401、带前缀才 200（鉴权分支单独验）；DNS 解析与证书链校验通过。

```python
def check(artifact, run_return):          # artifact = gateway_report.json
    rep = json.load(open(artifact, encoding="utf-8"))
    if len(rep["routes"]) != 12:
        return False, 0.0                  # 漏一条 = 这一轮不算
    mism = [r for r in rep["routes"] if r["status"] != EXPECTED[r["route"]]]
    injected = [r for r in rep["routes"] if r["route"] in INJECTED_503]
    if mism or not all(r["retry_count"] >= 3 for r in injected):
        return False, 0.0
    backoff = [r["backoff"] for r in injected]
    if any(seq != sorted(seq) for seq in backoff):
        return False, 0.0
    return True, (12 - len(mism)) / 12
```

- **产出**：`gateway_report.json`（逐条：路由、实际状态码、重试次数、退避序列、延迟）+ 断言脚本。
- **失败长什么样**：报告只有 11 条（漏跑 `/metrics`）⇒ 整轮作废；或 503 那两条 `retry_count = 1`（根本没重试）⇒ 整轮作废。这类失败恰恰是它最有用的地方：人眼看报告看不出漏了一条。

#### 例 3 · 数据清洗 / ETL 脚本

- **输入**：`raw_orders.csv` 5000 行 + 清洗规则（去重、类型、单位换算）。
- **断言**：去重率落在给定区间（例 4.2%–5.0%，跑偏即失败）；输出列 dtype 与契约一致；**幂等**——连跑两次输出哈希必须相同；未知枚举值必须进 `exceptions.csv` 而不是被静默丢弃（丢了多少行要能算出来）。
- **产出**：清洗脚本 + `exceptions.csv` + 行数守恒报告。

#### 例 4 · 参数扫描

- **输入**：20 个样本 × 网格（3 个 prompt 版本 × 2 个温度 = 60 次运行）。
- **断言**：结果表必须 60 行（网格全跑）；p99 延迟与输出体积由逐条记录算出；与基线 run 的 3 个固定样本输出逐字符一致（回归保护）。
- **产出**：`sweep.csv` + 汇总脚本。失败示例：表只有 51 行（超时被跳过）⇒ 门禁要求跳过的样本必须列在 `skipped.json`，否则不通过。

#### 例 5 · 巡检与合规

- **输入**：100 项清单 + 上月报告。
- **断言**：脚本覆盖全部 100 项（覆盖率由脚本自己算，不接受"已完成"）；字段命名与历史报告一致（列名集合相等）；上月 3 个已知异常项本次必须仍被报出（防退化）；每项都要有证据（命令输出或截图路径）。
- **产出**：巡检脚本 + 覆盖率 + 异常清单。

#### 例 6 · 文档 / 合同抽取

- **输入**：40 份文件 + 必抽字段（甲方、金额、期限、违约条款）。
- **断言**：40 份全部有输出；金额字段必须可解析为数字且与原文出现的数字一致（幻觉直接判负）；缺失字段必须写 `null` 而不是省略；抽样 10 份人工核对（这部分走 human judge，是 checklist 路径，不是 objective）。
- **产出**：`extract.jsonl` + 异常清单 + 抽检记录。

#### 例 7 · 补测试 / 修 bug

- **输入**：一个失败的 pytest 用例 + 源码。
- **断言**：pytest 全绿；覆盖率 ≥ 80%；**测试文件本身未被改动**（哈希与基线一致——防"改测试让绿灯"这类作弊）；断言值必须来自 fixture，不许硬编码在代码里。
- **产出**：patch + 测试报告。

#### 例 8 · API 客户端封装

- **输入**：可控的 mock server（逐条打状态码）+ 错误分类表。
- **断言**：429 → 重试且退避是 `[1, 2, 4]`；401 → 不重试且立即返回错误类型；超时率 < 5%；连接复用（同一 session 计数，不能每次新建）；SSE 分块按序到达。
- **产出**：`client.py` + mock 跑出的 `calls.jsonl`。

#### 例 9 · 配置 / 契约校验器

- **输入**：30 份配置，其中 8 份是已知坏的（黄金样本）。
- **断言**：8 份必须全部报错（漏报 = 0）；22 份好配置误报 = 0；每条错误带字段路径，能定位到行。
- **产出**：`validator.py` + `errors.jsonl`。

#### 例 10 · 作业 / 任务自动批改

- **输入**：20 份提交 + 标准输入输出对。
- **断言**：在隔离目录跑通且输出逐条比对；超时（`EXECUTE_TIMEOUT`）视为不通过而不是报错；越界写盘或访问网络视为不通过。
- **产出**：`grades.csv`（每份：通过/失败 + 失败原因）。

**这 10 个例子满足的三个条件**（决定值不值得用它）：产物可枚举、断言可程序化、失败可归因。三者缺任何一个，就退回普通 chat。

### 跑法（非科研任务，键名以 `parse_yaml` 为准）

命令行只有 `--yaml-location`，其余全部在 yaml 里：

```yaml
research-topic: "对 tickets.csv 做四分类并输出逐条预测"
judge: objective                      # objective > human > llm
checks: "examples/checks_classification.py"   # 该文件须定义 check(artifact, run_return)
judge-compare: True                   # 把程序分与模型自评并排记录（差值写进 record）
judge-checklist: ["抽 10 份核对金额字段"]      # 仅当 objective 不可用时才走到 human
allow-hf-search: false                # 不碰 HuggingFace；数据走 notes 或本地 JSON 目录
compile-latex: false
copilot-mode: "false"
task-notes:
  running experiments:
    - 'Write predictions.csv with columns id,pred; do not sample.'
    - 'Print accuracy=<value> computed from the file, not estimated.'
```

`python ai_lab_repo.py --yaml-location "experiment_configs/xxx.yaml"`

一个容易踩的点：`judge: objective` 但 checks 文件加载失败时不会退出，会打印 `[judge] objective 模式但没有可执行的 checks 文件，实际会回退到 LLM 自评`（[ai_lab_repo.py:819-820](ai_lab_repo.py#L819-L820)）——这时跑的还是自评，分数好看但没有门禁。

### 网络层网关验证：能验什么

只有能写成脚本断言的部分：

- 状态码与错误形状（裸 key 必须 401、带前缀才 200；503 的响应体字段形状）
- 重试次数、退避序列、超时率、p99 延迟、连接复用
- 覆盖率（必须打到全部 N 条路由，不能抽样）、SSE 分块到达顺序
- 路由表 / VLAN / ACL 与期望表一致（读配置 → 跑命令 → 断言结果）
- DNS 解析一致性、证书链、MTU 与分片行为

不能验的：策略是否"合理"、某条 ACL 该不该存在——那是人的判断，写成 checks 之前它在系统里不存在。另外没有网络时只能验到打桩那一层（本分支 `test_guards.py` 的四条守卫就是打桩版，离线全 PASS）。

### 什么情况下不值得用它

单轮问答、一次性小任务、没有可程序化的验收条件——普通 chat 更快。如果 checks 只是"找报告里有没有几个章节名词"，它只防"没写"，防不了"写了但假的"；要防后者得写指标、覆盖率、哈希这类断言。

## 📜 License

Source Code Licensing: Our project's source code is licensed under the MIT License. This license permits the use, modification, and distribution of the code, subject to certain conditions outlined in the MIT License.

## 📬 Contact

If you would like to get in touch, feel free to reach out to [sschmi46@jhu.edu](mailto:sschmi46@jhu.edu)

## Reference / Bibtex


### Agent Laboratory
```bibtex
@misc{schmidgall2025agentlaboratoryusingllm,
      title={Agent Laboratory: Using LLM Agents as Research Assistants}, 
      author={Samuel Schmidgall and Yusheng Su and Ze Wang and Ximeng Sun and Jialian Wu and Xiaodong Yu and Jiang Liu and Michael Moor and Zicheng Liu and Emad Barsoum},
      year={2025},
      eprint={2501.04227},
      archivePrefix={arXiv},
      primaryClass={cs.HC},
      url={https://arxiv.org/abs/2501.04227}, 
}
```

### AgentRxiv
```bibtex
@misc{schmidgall2025agentrxiv,
      title={AgentRxiv: Towards Collaborative Autonomous Research}, 
      author={Samuel Schmidgall and Michael Moor},
      year={2025},
      eprint={2503.18102},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2503.18102}, 
}
```
