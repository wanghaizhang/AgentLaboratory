import openai
import time, tiktoken
from openai import OpenAI
import os, anthropic, json, random
import google.generativeai as genai

TOKENS_IN = dict()
TOKENS_OUT = dict()

encoding = tiktoken.get_encoding("cl100k_base")

def curr_cost_est():
    costmap_in = {
        "gpt-4o": 2.50 / 1000000,
        "gpt-4o-mini": 0.150 / 1000000,
        "o1-preview": 15.00 / 1000000,
        "o1-mini": 3.00 / 1000000,
        "claude-3-5-sonnet": 3.00 / 1000000,
        "deepseek-chat": 1.00 / 1000000,
        "o1": 15.00 / 1000000,
        "o3-mini": 1.10 / 1000000,
    }
    costmap_out = {
        "gpt-4o": 10.00/ 1000000,
        "gpt-4o-mini": 0.6 / 1000000,
        "o1-preview": 60.00 / 1000000,
        "o1-mini": 12.00 / 1000000,
        "claude-3-5-sonnet": 12.00 / 1000000,
        "deepseek-chat": 5.00 / 1000000,
        "o1": 60.00 / 1000000,
        "o3-mini": 4.40 / 1000000,
    }
    return sum([costmap_in.get(_, 0.0)*TOKENS_IN[_] for _ in TOKENS_IN]) + sum([costmap_out.get(_, 0.0)*TOKENS_OUT[_] for _ in TOKENS_OUT])

def _openai_client(api_key=None):
    """OpenAI 兼容端点客户端：LOCAL_BASE_URL / OPENAI_BASE_URL 决定目标（本地 vLLM、Ollama、LM Studio 或自定义网关）。
    未设置 base_url 时退回官方 OpenAI。"""
    base_url = os.getenv("LOCAL_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    key = api_key or os.getenv("LOCAL_API_KEY") or os.getenv("OPENAI_API_KEY") or "not-needed"
    return OpenAI(api_key=key, base_url=base_url) if base_url else OpenAI()

def _extract_content(msg):
    """兼容部分推理模型 content 为空、只有 reasoning_content 的情况。"""
    content = getattr(msg, "content", None)
    if content:
        return content
    return getattr(msg, "reasoning_content", None) or ""

def query_model(model_str, prompt, system_prompt, openai_api_key=None, gemini_api_key=None,  anthropic_api_key=None, tries=5, timeout=5.0, temp=None, print_cost=True, version="1.5"):
    preloaded_api = os.getenv('OPENAI_API_KEY')
    if openai_api_key is None and preloaded_api is not None:
        openai_api_key = preloaded_api
    if openai_api_key is None and anthropic_api_key is None:
        # 本地 OpenAI 兼容端点不需要真 key；只有完全没有 key 也没有本地端点配置时才报错
        if not (os.getenv("LOCAL_BASE_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("LOCAL_MODEL")):
            raise Exception("No API key provided in query_model function")
    if openai_api_key is not None:
        openai.api_key = openai_api_key
        os.environ["OPENAI_API_KEY"] = openai_api_key
    if anthropic_api_key is not None:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
    if gemini_api_key is not None:
        os.environ["GEMINI_API_KEY"] = gemini_api_key
    # 本地/自定义网关端点会瞬时抖动（实跑报错原文: "Error code: 503 - this instance is draining;
    # retry against the next instance"，随后连续 Connection error）。原来的 5 次 × 5s 窗口太短，
    # 一次抖动就让整轮 run 崩在 "Max retries: timeout"。本地端点用更长的窗口 + 指数退避（带抖动），
    # 环境变量可调：LOCAL_TRIES / LOCAL_BACKOFF / LOCAL_BACKOFF_CAP。
    is_local_endpoint = bool(os.getenv("LOCAL_BASE_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("LOCAL_MODEL"))
    max_tries = int(os.getenv("LOCAL_TRIES", "10")) if is_local_endpoint else tries
    backoff_base = float(os.getenv("LOCAL_BACKOFF", "5.0")) if is_local_endpoint else timeout
    backoff_cap = float(os.getenv("LOCAL_BACKOFF_CAP", "60.0"))
    last_error = None
    for _ in range(max_tries):
        try:
            if model_str == "gpt-4o-mini" or model_str == "gpt4omini" or model_str == "gpt-4omini" or model_str == "gpt4o-mini":
                model_str = "gpt-4o-mini"
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}]
                if version == "0.28":
                    if temp is None:
                        completion = openai.ChatCompletion.create(
                            model=f"{model_str}",  # engine = "deployment_name".
                            messages=messages
                        )
                    else:
                        completion = openai.ChatCompletion.create(
                            model=f"{model_str}",  # engine = "deployment_name".
                            messages=messages, temperature=temp
                        )
                else:
                    client = OpenAI()
                    if temp is None:
                        completion = client.chat.completions.create(
                            model="gpt-4o-mini-2024-07-18", messages=messages, )
                    else:
                        completion = client.chat.completions.create(
                            model="gpt-4o-mini-2024-07-18", messages=messages, temperature=temp)
                answer = completion.choices[0].message.content

            elif model_str == "gemini-2.0-pro":
                genai.configure(api_key=gemini_api_key)
                model = genai.GenerativeModel(model_name="gemini-2.0-pro-exp-02-05", system_instruction=system_prompt)
                answer = model.generate_content(prompt).text
            elif model_str == "gemini-1.5-pro":
                genai.configure(api_key=gemini_api_key)
                model = genai.GenerativeModel(model_name="gemini-1.5-pro", system_instruction=system_prompt)
                answer = model.generate_content(prompt).text
            elif model_str == "o3-mini":
                model_str = "o3-mini"
                messages = [
                    {"role": "user", "content": system_prompt + prompt}]
                if version == "0.28":
                    completion = openai.ChatCompletion.create(
                        model=f"{model_str}",  messages=messages)
                else:
                    client = OpenAI()
                    completion = client.chat.completions.create(
                        model="o3-mini-2025-01-31", messages=messages)
                answer = completion.choices[0].message.content

            elif model_str == "claude-3.5-sonnet":
                client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
                message = client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}])
                answer = json.loads(message.to_json())["content"][0]["text"]
            elif model_str == "gpt4o" or model_str == "gpt-4o":
                model_str = "gpt-4o"
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}]
                if version == "0.28":
                    if temp is None:
                        completion = openai.ChatCompletion.create(
                            model=f"{model_str}",  # engine = "deployment_name".
                            messages=messages
                        )
                    else:
                        completion = openai.ChatCompletion.create(
                            model=f"{model_str}",  # engine = "deployment_name".
                            messages=messages, temperature=temp)
                else:
                    client = OpenAI()
                    if temp is None:
                        completion = client.chat.completions.create(
                            model="gpt-4o-2024-08-06", messages=messages, )
                    else:
                        completion = client.chat.completions.create(
                            model="gpt-4o-2024-08-06", messages=messages, temperature=temp)
                answer = completion.choices[0].message.content
            elif model_str == "deepseek-chat":
                model_str = "deepseek-chat"
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}]
                if version == "0.28":
                    raise Exception("Please upgrade your OpenAI version to use DeepSeek client")
                else:
                    deepseek_client = OpenAI(
                        api_key=os.getenv('DEEPSEEK_API_KEY'),
                        base_url="https://api.deepseek.com/v1"
                    )
                    if temp is None:
                        completion = deepseek_client.chat.completions.create(
                            model="deepseek-chat",
                            messages=messages)
                    else:
                        completion = deepseek_client.chat.completions.create(
                            model="deepseek-chat",
                            messages=messages,
                            temperature=temp)
                answer = completion.choices[0].message.content
            elif model_str == "o1-mini":
                model_str = "o1-mini"
                messages = [
                    {"role": "user", "content": system_prompt + prompt}]
                if version == "0.28":
                    completion = openai.ChatCompletion.create(
                        model=f"{model_str}",  # engine = "deployment_name".
                        messages=messages)
                else:
                    client = OpenAI()
                    completion = client.chat.completions.create(
                        model="o1-mini-2024-09-12", messages=messages)
                answer = completion.choices[0].message.content
            elif model_str == "o1":
                model_str = "o1"
                messages = [
                    {"role": "user", "content": system_prompt + prompt}]
                if version == "0.28":
                    completion = openai.ChatCompletion.create(
                        model="o1-2024-12-17",  # engine = "deployment_name".
                        messages=messages)
                else:
                    client = OpenAI()
                    completion = client.chat.completions.create(
                        model="o1-2024-12-17", messages=messages)
                answer = completion.choices[0].message.content
            elif model_str == "o1-preview":
                model_str = "o1-preview"
                messages = [
                    {"role": "user", "content": system_prompt + prompt}]
                if version == "0.28":
                    completion = openai.ChatCompletion.create(
                        model=f"{model_str}",  # engine = "deployment_name".
                        messages=messages)
                else:
                    client = OpenAI()
                    completion = client.chat.completions.create(
                        model="o1-preview", messages=messages)
                answer = completion.choices[0].message.content

            else:
                # 通用分支：任意模型名都可用（本地 vLLM / Ollama / LM Studio / 自定义 OpenAI 兼容网关）。
                # 模型名取 LOCAL_MODEL，未设置则直接用传入的 model_str。
                client = _openai_client(openai_api_key)
                model_name = os.getenv("LOCAL_MODEL") or model_str
                if system_prompt:
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}]
                else:
                    messages = [{"role": "user", "content": prompt}]
                # 可选关闭思考（只作用于本通用分支，即本地/OpenAI 兼容端点；硬编码模型分支不受影响）。
                # LOCAL_REASONING_EFFORT=none|minimal|low  -> reasoning_effort
                # LOCAL_ENABLE_THINKING=0|false|no|off     -> chat_template_kwargs.enable_thinking（vLLM/Qwen 模板开关）
                # 实测（2026-11-09）：关掉后单步从 ~6 s 降到 1–3.5 s，且 content 不再为空——
                # 开思考时 token 预算可能全被 reasoning 吃掉，answer 就变成 reasoning 的转述，门禁与报告都会受影响。
                # 两个键都不设时行为与上游一致。
                extra_kwargs = {}
                if is_local_endpoint:
                    effort = os.getenv("LOCAL_REASONING_EFFORT")
                    if effort:
                        extra_kwargs["reasoning_effort"] = effort
                    if os.getenv("LOCAL_ENABLE_THINKING", "").strip().lower() in ("0", "false", "no", "off"):
                        extra_kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
                if temp is None:
                    completion = client.chat.completions.create(model=model_name, messages=messages, **extra_kwargs)
                else:
                    completion = client.chat.completions.create(model=model_name, messages=messages, temperature=temp, **extra_kwargs)
                answer = _extract_content(completion.choices[0].message)

            try:
                if model_str in ["o1-preview", "o1-mini", "claude-3.5-sonnet", "o1", "o3-mini"]:
                    encoding = tiktoken.encoding_for_model("gpt-4o")
                elif model_str in ["deepseek-chat"]:
                    encoding = tiktoken.encoding_for_model("cl100k_base")
                else:
                    try:
                        encoding = tiktoken.encoding_for_model(model_str)
                    except Exception:
                        # 本地/第三方模型没有 tiktoken 映射，退回 cl100k_base（只用于成本估算，非精确）
                        encoding = tiktoken.get_encoding("cl100k_base")
                if model_str not in TOKENS_IN:
                    TOKENS_IN[model_str] = 0
                    TOKENS_OUT[model_str] = 0
                TOKENS_IN[model_str] += len(encoding.encode(system_prompt + prompt))
                TOKENS_OUT[model_str] += len(encoding.encode(answer))
                if print_cost:
                    print(f"Current experiment cost = ${curr_cost_est()}, ** Approximate values, may not reflect true cost")
            except Exception as e:
                if print_cost: print(f"Cost approximation has an error? {e}")
            return answer
        except Exception as e:
            print("Inference Exception:", e)
            last_error = e
            if is_local_endpoint:
                time.sleep(min(backoff_cap, backoff_base * (2 ** _)) + random.uniform(0, 1))
            else:
                time.sleep(timeout)
            continue
    raise Exception(f"Max retries ({max_tries}) exceeded, last error: {last_error}")


#print(query_model(model_str="o1-mini", prompt="hi", system_prompt="hey"))