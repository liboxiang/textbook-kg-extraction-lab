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
        self.timeout_seconds = float(timeout_seconds or os.getenv("LLM_TIMEOUT_SECONDS", "300"))

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.0, reasoning_effort: str | None = None) -> str:
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
        }
        if reasoning_effort and reasoning_effort != "none":
            payload["reasoning_effort"] = reasoning_effort
        else:
            payload["temperature"] = temperature
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        # The configured OpenAI-compatible endpoint is reachable directly.
        # Ignore stale HTTP(S)_PROXY/ALL_PROXY environment variables such as
        # localhost:9, which otherwise make the request fail before reaching
        # the API server.
        with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]

    def validate_configuration(self) -> str:
        """Validate credentials and endpoint without creating a completion."""
        if not self.api_key:
            raise RuntimeError("未配置 API Key")
        if not self.model:
            raise RuntimeError("未配置 Model")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                resp = client.get(f"{self.base_url}/models", headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500].strip()
            raise RuntimeError(f"接口返回 HTTP {exc.response.status_code}: {detail or '无错误详情'}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"无法连接 Base URL：{exc}") from exc
        except ValueError as exc:
            raise RuntimeError("接口返回的不是合法 JSON") from exc

        models = data.get("data") if isinstance(data, dict) else None
        if isinstance(models, list):
            model_ids = {item.get("id") for item in models if isinstance(item, dict)}
            if model_ids and self.model not in model_ids:
                raise RuntimeError(f"鉴权成功，但 Model 不在服务端模型列表中：{self.model}")
        return f"连接成功，当前模型：{self.model}"
