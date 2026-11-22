"""LLM 流式客户端

支持多个 OpenAI 兼容端点（DeepSeek / 本地 llama.cpp）。
发请求前按模型上下文窗口裁剪历史：丢掉最老的消息，保留 system 和最新对话。
"""

import json
from typing import AsyncGenerator

import httpx

from backend.config import DEFAULT_MODEL, MODEL_PROFILES

# 给模型输出预留的 token，避免输入占满窗口导致回答被截断
OUTPUT_RESERVE = 8192

# 本地模型名探测缓存（llama.cpp 的 /v1/models）
_local_model_cache: dict[str, str] = {}


def model_profile(model_id: str) -> dict:
    """按 id 取模型档案；未知 id 回落到默认模型"""
    if model_id in MODEL_PROFILES:
        return dict(MODEL_PROFILES[model_id], id=model_id)
    return dict(MODEL_PROFILES[DEFAULT_MODEL], id=DEFAULT_MODEL)


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（UTF-8 字节 / 3）

    中文约 1 字 1 token（3 字节），英文约 4 字符 1 token。
    宁可高估，避免真的把上下文窗口撑爆。
    """
    return max(1, len(text.encode("utf-8")) // 3)


def trim_messages(messages: list[dict], context: int) -> list[dict]:
    """按上下文窗口裁剪历史：system 固定保留，从最新消息往前累加，超窗的老消息丢掉

    最新一条消息无论如何保留（用户刚发的输入不能丢）。
    """
    budget = max(1024, context - OUTPUT_RESERVE)
    if not messages:
        return messages

    system = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    used = sum(estimate_tokens(m.get("content") or "") + 4 for m in system)

    kept: list[dict] = []
    dropped = 0
    for m in reversed(rest):
        cost = estimate_tokens(m.get("content") or "") + 4
        if kept and used + cost > budget:
            dropped = len(rest) - len(kept)
            break
        kept.append(m)
        used += cost
    kept.reverse()

    if dropped:
        print(f"[context] 超出 {context} token 窗口，丢弃最早 {dropped} 条消息")
    return system + kept


async def _resolve_model(profile: dict) -> str:
    """本地端点：未配置模型名时从 /v1/models 取第一个"""
    if profile["model"]:
        return profile["model"]
    base = profile["base"].rstrip("/")
    if base in _local_model_cache:
        return _local_model_cache[base]
    headers = {}
    if profile["key"]:
        headers["Authorization"] = f"Bearer {profile['key']}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
        response = await client.get(f"{base}/models", headers=headers)
        response.raise_for_status()
        data = response.json()
    if not data.get("data"):
        raise RuntimeError(f"模型服务未返回可用模型列表：{base}")
    name = data["data"][0]["id"]
    _local_model_cache[base] = name
    return name


async def stream_chat(
    messages: list[dict], model_id: str = DEFAULT_MODEL
) -> AsyncGenerator[dict, None]:
    """流式调用 OpenAI 兼容端点，逐块返回文本

    调用前按该模型的上下文窗口裁剪历史（丢老留新）。
    """
    profile = model_profile(model_id)
    base = profile["base"].rstrip("/")
    payload = trim_messages(messages, profile["context"])

    headers = {"Content-Type": "application/json"}
    if profile["key"]:
        headers["Authorization"] = f"Bearer {profile['key']}"

    timeout = httpx.Timeout(profile["timeout"], connect=10.0)
    try:
        model_name = await _resolve_model(profile)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{base}/chat/completions",
                headers=headers,
                json={"model": model_name, "messages": payload, "stream": True},
            ) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", "replace")[:300]
                    raise RuntimeError(
                        f"模型服务返回 {response.status_code}：{body}"
                    )

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content") or ""
                        if content:
                            yield {"type": "content", "content": content}
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    except httpx.ConnectError as e:
        hint = "（本地模型是否已启动？）" if profile["id"] == "local" else ""
        raise RuntimeError(f"连接模型服务失败：{base}{hint}") from e
    except httpx.TimeoutException as e:
        raise RuntimeError(
            f"模型服务响应超时（{profile['timeout']} 秒）：{base}"
        ) from e
