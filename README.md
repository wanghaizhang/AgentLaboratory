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
