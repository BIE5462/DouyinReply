"""Chat Completions 兼容客户端。"""

import asyncio

import requests

from ..models.entities import GlobalAIConfig


class BaseLLMClient:
    async def generate(self, config, messages):
        raise NotImplementedError


class ChatCompletionClient(BaseLLMClient):
    async def generate(self, config: GlobalAIConfig, messages):
        if not config.is_complete:
            raise RuntimeError("AI 配置不完整，请先设置 Base URL、API Key 和模型。")

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        def _request():
            endpoint = config.base_url.rstrip("/") + "/chat/completions"
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=config.timeout_seconds,
            )
            response.raise_for_status()
            return response.json()

        data = await asyncio.to_thread(_request)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("AI 返回结果为空。")

        content = (
            choices[0].get("message", {}).get("content", "")
            if isinstance(choices[0], dict)
            else ""
        )
        if not content or not str(content).strip():
            raise RuntimeError("AI 返回了空文本。")
        return str(content).strip()

    async def test_connection(self, config: GlobalAIConfig, prompt_text: str):
        return await self.generate(
            config,
            [
                {"role": "system", "content": "你是一个测试助手，请简短回复。"},
                {"role": "user", "content": prompt_text},
            ],
        )
