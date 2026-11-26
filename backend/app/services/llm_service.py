import json
import re
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import settings


class LLMError(Exception):
    """The LLM call failed or returned unusable output."""


class LLMNotConfigured(LLMError):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def complete_json(self, system: str, user: str) -> dict:
        """Return one parsed JSON object."""


def parse_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise LLMError("The model did not return valid JSON.")
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            raise LLMError("The model did not return valid JSON.")
    if not isinstance(data, dict):
        raise LLMError("The model returned JSON that is not an object.")
    return data


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        from groq import Groq
        self.client = Groq(api_key=api_key, timeout=45.0, max_retries=1)
        self.model = model

    def complete_json(self, system: str, user: str) -> dict:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:
            raise LLMError(f"LLM request failed: {type(e).__name__}: {str(e)[:200]}") from e
        return parse_json(resp.choices[0].message.content)


@lru_cache(maxsize=1)
def get_llm() -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "groq":
        if not settings.groq_api_key or not settings.llm_model:
            raise LLMNotConfigured("LLM is not configured. Set GROQ_API_KEY and LLM_MODEL in backend/.env.")
        return GroqProvider(settings.groq_api_key, settings.llm_model)
    raise LLMNotConfigured(f"Unknown LLM provider: {provider}")