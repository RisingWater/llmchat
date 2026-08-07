"""LLM 流式客户端 — 纯文本对话"""

import json
from typing import AsyncGenerator

import httpx

from backend.config import API_KEY, API_BASE, MODEL_NAME


async def stream_chat(messages: list[dict]) -> AsyncGenerator[dict, None]:
    """流式调用 DeepSeek API，逐块返回文本。"""
    async with httpx.AsyncClient(timeout=httpx.Timeout(120)) as client:
        async with client.stream(
            "POST",
            f"{API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield {"type": "content", "content": content}
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
