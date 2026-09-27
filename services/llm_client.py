from __future__ import annotations

import os
import httpx
from dotenv import load_dotenv

load_dotenv()


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "")
        self.timeout_seconds = float(timeout_seconds or os.getenv("LLM_TIMEOUT_SECONDS", "120"))

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        if not self.api_key:
            raise RuntimeError("未配置 LLM_API_KEY")
        if not self.model:
            raise RuntimeError("未配置 LLM_MODEL")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]
