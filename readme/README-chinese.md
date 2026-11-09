# Agent Laboratory: 使用大型语言模型代理作为研究助理

<p align="center">
  <img src="../media/AgentLabLogo.png" alt="Demonstration of the flow of AgentClinic" style="width: 99%;">
</p>

<p align="center">
    【<a href="../README.md">English</a>  | 中文 | <a href="../readme/README-japanese.md">日本語</a> | <a href="../readme/README-korean.md">한국어</a> | <a href="../readme/README-filipino.md">Filipino</a> | <a href="../readme/README-french.md">Français</a> | <a href="../readme/README-slovak.md">Slovenčina</a> | <a href="../readme/README-portugese.md">Português</a> | <a href="../readme/README-spanish.md">Español</a> | <a href="../readme/README-turkish.md">Türkçe</a> | <a href="../readme/README-hindi.md">हिंदी</a> | <a href="../readme/README-bengali.md">বাংলা</a> | <a href="../readme/README-vietnamese.md">Tiếng Việt</a> | <a href="../readme/README-russian.md">Русский</a> | <a href="../readme/README-arabic.md">العربية</a> | <a href="../readme/README-farsi.md">فارسی</a> | <a href="../readme/README-italian.md">Italiano</a>】
</p>

<p align="center">
    【🌐 <a href="https://agentlaboratory.github.io/">网站</a> | 💻 <a href="https://github.com/SamuelSchmidgall/AgentLaboratory">软件</a> | 🎥 <a href="https://agentlaboratory.github.io/#youtube-video">视频</a> |  📚 <a href="https://agentlaboratory.github.io/#examples-goto">示例论文</a> | 📰 <a href="https://agentlaboratory.github.io/#citation-ref">引用</a>】
</p>

## 📖 概述

- **Agent Laboratory** 是一个端到端的自主研究工作流程，旨在协助**您**作为人类研究人员**实现您的研究想法**。Agent Laboratory 由由大型语言模型驱动的专业代理组成，支持您完成整个研究工作流程——从进行文献综述和制定计划，到执行实验和撰写综合报告。
- 该系统并非旨在取代您的创造力，而是为了补充它，使您能够专注于创意和批判性思维，同时自动化重复且耗时的任务，如编码和文档编写。通过适应不同水平的计算资源和人类参与，Agent Laboratory 旨在加速科学发现并优化您的研究生产力。

<p align="center">
  <img src="../media/AgentLab.png" alt="Demonstration of the flow of AgentClinic" style="width: 99%;">
</p>

### 🔬 Agent Laboratory 如何工作？

- Agent Laboratory 包含三个主要阶段，系统地引导研究过程：（1）文献综述，（2）实验，（3）报告撰写。在每个阶段，由大型语言模型驱动的专业代理协作完成不同的目标，整合了如 arXiv、Hugging Face、Python 和 LaTeX 等外部工具以优化结果。这一结构化的工作流程始于独立收集和分析相关研究论文，经过协作计划和数据准备，最终实现自动化实验和综合报告生成。论文中讨论了具体代理角色及其在这些阶段的贡献。

<p align="center">
  <img src="../media/AgentLabWF.png" alt="Demonstration of the flow of AgentClinic" style="width: 99%;">
</p>

### 🧩 任意模型 / 本地模型（本次修改，2026-11-07）

模型不再局限于上面列出的那几个字面量名称：`inference.py` 的 `query_model` 末尾新增通用分支，**任意模型名**都会发往 OpenAI 兼容端点（本地 vLLM、Ollama、LM Studio 或自建网关），由环境变量决定：

| 变量 | 作用 |
|---|---|
| `LOCAL_BASE_URL` | 端点 base URL；未设置时回退 `OPENAI_BASE_URL` |
| `LOCAL_MODEL` | 发往端点的模型名；未设置时用 `llm-backend` 的值 |
| `LOCAL_API_KEY` | 端点密钥；本地服务通常不需要；回退 `OPENAI_API_KEY`，再回退 `not-needed` |

示例：

```bash
export LOCAL_BASE_URL="http://127.0.0.1:8000/v1"
export LOCAL_MODEL="qwen3:8b"
python ai_lab_repo.py --yaml-location "experiment_configs/local_model_example.yaml"
```

行为说明：

- 配置了本地端点时不再强制要求 API key；原来的 `No API key provided` 只在既没有 key 也没有本地端点配置时触发。
- 部分推理模型的 `content` 为空，代码会回退读取 `reasoning_content`。
- 成本打印：未知模型名按 `$0` 计，tokenizer 回退 `cl100k_base`，非 OpenAI 模型的成本只是近似值。
- 实验阶段生成的代码调用 `utils.query_local(...)`（`execute_code` 会在代码前加 `from utils import *`），所以 task-notes 里必须明确指示使用 `query_local`，不要再写 `query_gpt4omini`；见 [experiment_configs/local_model_example.yaml](../experiment_configs/local_model_example.yaml)。
- 免安装依赖的离线自检：`python test_local_dispatch.py`。
- yaml 中的 `copilot-mode`、`load-existing` 现在被接受为 `copilot_mode`、`load-previous` 的别名；此前示例配置里这两个开关的值是被静默忽略的。
- `requirements.txt` 仍缺 `flask`、`flask_sqlalchemy`、`sentence-transformers`（`ai_lab_repo.py` 会 `from app import *`），需要额外安装，否则 import 失败。奖励与命令解析依赖严格格式（```` ```SCORE ````、精确 JSON、```` ```EDIT N M ````），小模型会明显拖低搜索环节的表现，建议本地模型做主干、较强模型做 `lit-review-backend`/reward。

### ⚖️ 奖惩机制（打分到底怎么运作）

这里**没有 RL 意义上的奖励函数，也没有训练信号**——不微调、分数不跨轮累积。两处 `# todo: have a reward function here`（[agents.py:40](../agents.py#L40)、[mlesolver.py:145](../mlesolver.py#L145)）就是实情：所谓"奖励模型"只是一段裁判 prompt。机制由三部分组成——**LLM 裁判 + 格式/执行门禁 + top-K 归档淘汰**。

两条打分通路：

1. **代码阶段** — [mlesolver.py:141-163](../mlesolver.py#L141-L163) 的 `get_score`：教授角色裁判读「计划 + 代码 + 运行输出」，给 **0~1** 的浮点数。必须严格输出 ```` ```SCORE\n<float>\n``` ````，`temp=0.6`，最多重试 3 次；一旦异常返回 `None`，这一轮不记分。
2. **报告阶段** — [agents.py:36-181](../agents.py#L36-L181) 的 `get_score`：NeurIPS 风格评审表，要求精确 JSON，各项归一后加权：

| 维度 | 量表 | 权重 |
|---|---|---|
| Overall | 1–10 | **1.0** |
| Contribution | 1–4 | **0.4** |
| Presentation | 1–4 | **0.2** |
| Clarity / Quality / Soundness / Significance / Originality | 1–4 | 各 0.1 |
| Confidence | 1–5 | 0.1 |

`performance = 加权和 / 2.2 × 10`，即 **0~10**。Confidence 也计分，所以这个分数部分反映的是裁判的自信，而不只是作品质量。三个评审人格（[agents.py:192-199](../agents.py#L192-L199))各自打分一次，属于定性压力，不进公式。分数只在阶段结束时打印（[ai_lab_repo.py:263](../ai_lab_repo.py#L263)、[ai_lab_repo.py:329](../ai_lab_repo.py#L329)）。

惩罚从来不是数值扣分，而是"**这一轮不算数**"：

1. 缺 abstract/introduction/methods/results/discussion 任一节必须减分（[agents.py:135](../agents.py#L135)）；`Ethical Concerns: true` 会单独触发伦理审查。
2. **格式门禁**：`EDIT`/`REPLACE` 解析失败、scaffold 占位符缺失、正文里混入 `documentclass`/`usepackage`、JSON 无法解析 ⇒ `is_valid=False`、`score=None`，**改动被回滚**，错误信息写回 history（[papersolver.py:440](../papersolver.py#L440)、[papersolver.py:461](../papersolver.py#L461)）。
3. **执行门禁**：出现 `[CODE EXECUTION ERROR]` 或没有 `submission.csv` ⇒ 不记分，只有反思提示（[mlesolver.py:472-487](../mlesolver.py#L472-L487)）；准确率不得为 0%（[mlesolver.py:445](../mlesolver.py#L445)）。
4. **归档淘汰——真正的惩罚**：`best_codes`（`max_codes`，默认 1）与 `best_report`（`max_papers`）是按分数降序的候选池；新候选只有 `top_score > best[-1]` 才有资格进池，池满则 **弹出最低分**（[mlesolver.py:309-316](../mlesolver.py#L309-L316)、[papersolver.py:297-303](../papersolver.py#L297-L303)）。下一轮的底本用 `random.choice(best_codes)` 抽取（[mlesolver.py:291](../mlesolver.py#L291)）——低分方案失去"被选为父本"的资格。`min_gen_trials`（代码 1、报告 2）强制最少尝试次数，一次侥幸不能定案。

对本地模型的直接含义：较弱的裁判会自我打分偏宽松，reward 变成虚高噪声，且上述严格格式失败率更高 ⇒ 很多轮 `score=None`。建议裁判（以及 `lit-review-backend`）保留强模型，或把裁判换成客观校验。

### 🧭 这东西只能做学术研究吗

**开箱即用是的**——它产出的是 LaTeX 论文，因为研究形态是硬编码的：

- 阶段表就是研究流程（[ai_lab_repo.py:60-65](../ai_lab_repo.py#L60-L65)）：文献综述 → 计划制定 → 实验 → 结果解释 → 报告撰写/打磨。
- 工具是研究工具：arXiv 检索与全文（[tools.py:200-264](../tools.py#L200-L264)）、`pdflatex` 编译（[utils.py:155-188](../utils.py#L155-L188)）、按 arXiv ID 引用。
- 成功条件也是研究的成功条件：能编译、含八节、产出 `submission.csv`、准确率非 0，奖励是会议评审表。
- 角色是研究角色（PhD 学生、博后、教授、MLE），奖励表是 NeurIPS 评审表。

**但骨架本身与领域无关**，这才是可复用的部分：`BaseAgent`（对话 + 笔记）+ `Command` 注册表 + solver 的「执行 → 裁判 → 保留 top-K」循环。要改向别的领域（代码任务、运维手册、数据管线、评测基准），只需改这四件事：

1. 阶段表与 prompt — [ai_lab_repo.py:60-65](../ai_lab_repo.py#L60-L65)、[agents.py](../agents.py) 里各阶段的 prompt。
2. 工具注册表 — [papersolver.py](../papersolver.py) / [tools.py](../tools.py) 的 `Command` 类：把 arXiv/LaTeX 换成你自己的可执行动作。
3. 奖励 — 把主观评审表换成**客观验收测试**（pytest、schema 校验、指标阈值）。不换的话，你只剩一个自我打分的裁判。
4. 产物 — `report.txt`/PDF 换成该任务里"完成"的定义。

如果目标不是论文，就不要保留评审表：`copilot-mode` + `task-notes` 是更省事的路线——人来做裁判，top-K 归档仍作为幸存者选择机制起作用。

10 个具体场景例子（按「输入 → 断言 → 产出 → 失败长什么样」写）与跑法见 `README.md`「🧭 科研之外的应用场景」一节；可直接跑的 checks 示例在 [examples/checks_classification.py](../examples/checks_classification.py)。

## 🖥️ 安装


### Python 虚拟环境选项

1. **克隆 GitHub 仓库**：首先使用以下命令克隆仓库：
    ```bash
    git clone git@github.com:SamuelSchmidgall/AgentLaboratory.git
    ```

2. **设置并激活 Python 环境**
    ```bash
    python -m venv venv_agent_lab
    ```
    - 现在激活此环境：
    ```bash
    source venv_agent_lab/bin/activate
    ```

3. **安装所需库**
    ```bash
    pip install -r requirements.txt
    ```

4. **安装 pdflatex [可选]**
    ```bash
    sudo apt install pdflatex
    ```
    - 这使得代理能够编译 latex 源代码。
    - **[重要]** 如果由于没有 sudo 权限而无法运行此步骤，可以通过将 `--compile_latex` 标志设置为 false 来关闭 pdf 编译：`--compile_latex=False`

5. **现在运行 Agent Laboratory！**
    
    `python ai_lab_repo.py --api-key "API_KEY_HERE" --llm-backend "o1-mini" --research-topic "YOUR RESEARCH IDEA"`
    
    或者，如果您没有安装 pdflatex
    
    `python ai_lab_repo.py --api-key "API_KEY_HERE" --llm-backend "o1-mini" --research-topic "YOUR RESEARCH IDEA" --compile_latex=False`

-----

## 提高研究成果的技巧

#### [技巧 #1] 📝 确保写下详尽的笔记！ 📝

**写下详尽的笔记非常重要**，帮助您的代理理解您在项目中希望实现的目标，以及任何风格偏好。笔记可以包括您希望代理执行的任何实验、提供 API 密钥、希望包含的特定图表或图形，或任何您希望代理在进行研究时了解的内容。

这也是您让代理知道**它可以访问的计算资源**的机会，例如 GPU（数量、类型、内存大小）、CPU（核心数量、类型）、存储限制和硬件规格。

为了添加笔记，您必须修改 `ai_lab_repo.py` 中的 `task_notes_LLM` 结构。以下是我们的一些实验中使用的笔记示例。

```
task_notes_LLM = [
    {"phases": ["plan formulation"],
     "note": f"You should come up with a plan for TWO experiments."},

    {"phases": ["plan formulation", "data preparation",  "running experiments"],
     "note": "Please use gpt-4o-mini for your experiments."},

    {"phases": ["running experiments"],
     "note": f"Use the following code to inference gpt-4o-mini: \nfrom openai import OpenAI\nos.environ["OPENAI_API_KEY"] = "{api_key}"\nclient = OpenAI()\ncompletion = client.chat.completions.create(\nmodel="gpt-4o-mini-2024-07-18", messages=messages)\nanswer = completion.choices[0].message.content\n"},

    {"phases": ["running experiments"],
     "note": f"You have access to only gpt-4o-mini using the OpenAI API, please use the following key {api_key} but do not use too many inferences. Do not use openai.ChatCompletion.create or any openai==0.28 commands. Instead use the provided inference code."},

    {"phases": ["running experiments"],
     "note": "I would recommend using a small dataset (approximately only 100 data points) to run experiments in order to save time. Do not use much more than this unless you have to or are running the final tests."},

    {"phases": ["data preparation", "running experiments"],
     "note": "You are running on a MacBook laptop. You can use 'mps' with PyTorch"},

    {"phases": ["data preparation", "running experiments"],
     "note": "Generate figures with very colorful and artistic design."},
    ]
```

--------

#### [技巧 #2] 🚀 使用更强大的模型通常会带来更好的研究 🚀

在进行研究时，**模型的选择会显著影响结果的质量**。更强大的模型往往具有更高的准确性、更好的推理能力和更优秀的报告生成能力。如果计算资源允许，优先使用先进的模型，如 o1-(mini/preview) 或类似的最先进大型语言模型。

然而，**在性能和成本效益之间取得平衡也很重要**。虽然强大的模型可能会产生更好的结果，但它们通常更昂贵且运行时间更长。考虑选择性地使用它们，例如用于关键实验或最终分析，同时在迭代任务或初步原型设计中依赖较小、更高效的模型。

当资源有限时，**通过在您的特定数据集上微调较小的模型或将预训练模型与特定任务的提示相结合来优化，以实现性能与计算效率之间的理想平衡**。

-----

#### [技巧 #3] ✅ 您可以从检查点加载之前的保存 ✅

**如果您丢失了进度、互联网连接中断或子任务失败，您始终可以从先前的状态加载。** 您的所有进度默认保存在 `state_saves` 变量中，该变量存储每个单独的检查点。只需在运行 `ai_lab_repo.py` 时传递以下参数

`python ai_lab_repo.py --api-key "API_KEY_HERE" --research-topic "YOUR RESEARCH IDEA" --llm-backend "o1-mini" --load-existing True --load-existing-path "save_states/LOAD_PATH"`

-----

#### [技巧 #4] 🈯 如果您使用非英语语言运行 🈲

如果您使用非英语语言运行 Agent Laboratory，没问题，只需确保向代理提供一个语言标志，以便用您喜欢的语言进行研究。请注意，我们尚未广泛研究使用其他语言运行 Agent Laboratory，因此请务必报告您遇到的任何问题。

例如，如果您使用中文运行：

`python ai_lab_repo.py --api-key "API_KEY_HERE" --research-topic "YOUR RESEARCH IDEA (in your language)" --llm-backend "o1-mini" --language "中文"`

----

#### [技巧 #5] 🌟 还有很大的改进空间 🌟

这个代码库还有很大的改进空间，因此如果您进行了更改并希望帮助社区，请随时分享您所做的更改！我们希望这个工具对您有帮助！

## 参考文献 / Bibtex

```bibtex
@preprint{schmidgall2025AgentLaboratory,
  title={Agent Laboratory: Using LLM Agents as Research Assistants},
  author={Schmidgall, Samuel and Su, Yusheng and Wang, Ze and Sun, Ximeng and Wu, Jialian and Yu, Xiadong and Liu, Jiang, Liu, Zicheng and Barsoum, Emad},
  year={2025}
}
```