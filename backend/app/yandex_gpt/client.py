import json
from typing import Any
import httpx
from app.core.config import Settings


OPENAI_COMPATIBLE_MAX_OUTPUT_TOKENS = 8000


class YandexGPTUnavailable(RuntimeError):
    pass


class YandexGPTClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate_learning_content(self, params: dict) -> dict:
        if not self.settings.yandex_gpt_endpoint or not self.settings.yandex_gpt_api_key:
            raise YandexGPTUnavailable("YandexGPT endpoint or API key is not configured")

        system_prompt, user_prompt = self._build_prompts(params)
        endpoint = self.settings.yandex_gpt_endpoint.rstrip("/")
        if endpoint.endswith("/v1"):
            return await self._generate_openai_compatible(endpoint, system_prompt, user_prompt)
        return await self._generate_foundation_models(endpoint, system_prompt, user_prompt)

    def _build_prompts(self, params: dict) -> tuple[str, dict[str, Any]]:
        system_prompt = (
            "You generate safe Python typing practice content. "
            "Write block titles, explanations, exercise descriptions, hints, and surrounding educational text in Russian. "
            "Keep Python code, package names, identifiers, strings, and URLs technically correct. "
            "Python code fields must be ASCII-only: no Cyrillic identifiers, comments, or string literals inside code, starterCode, or solution. "
            "Use English-only sample string values inside Python code, for example 'sales', 'region', 'error', or ISO dates. "
            "Each code block must be short, valid Python syntax, and no longer than 12 lines or 600 characters. "
            "For the same topic, use the provided variantSeed to create a distinct lesson: choose different variable names, data examples, API parameters, and exercise framing. "
            "Do not reuse the most obvious import/request/print-only sequence unless the topic requires it. "
            "Return only strict JSON matching the requested schema. Do not include markdown. "
            "Do not include destructive filesystem, shell, credential, eval, exec, or package installation examples."
        )
        user_prompt: dict[str, Any] = {
            "task": "Generate Python library typing practice material.",
            "language": params["language"],
            "library": params["library"],
            "topic": params["topic"],
            "difficulty": params["difficulty"],
            "numberOfBlocks": params.get("numberOfBlocks", 5),
            "variant": params.get("variant"),
            "variantSeed": params.get("variantSeed"),
            "diversityRules": [
                "Keep the selected topic unchanged, but make this variant noticeably different from a default tutorial example.",
                "Use short realistic code snippets suitable for manual typing.",
                "Prefer one coherent mini-scenario across all blocks instead of unrelated fragments.",
            ],
            "validationRules": [
                "Return exactly the requested language, library, topic, and difficulty values.",
                "Use ASCII-only Python code in blocks.code, exercise.starterCode, and exercise.solution.",
                "Do not put Russian words inside Python comments, variable names, or string literals.",
                "Use English sample data inside Python strings.",
                "Keep every code snippet syntactically valid when parsed on its own.",
            ],
            "schema": {
                "language": "python",
                "library": "string",
                "topic": "string",
                "difficulty": "beginner|intermediate|advanced",
                "blocks": [{"title": "string", "code": "string", "explanation": "string"}],
                "exercise": {"description": "string", "starterCode": "string", "hint": "string", "solution": "string"},
            },
        }
        return system_prompt, user_prompt

    async def _generate_openai_compatible(
        self,
        endpoint: str,
        system_prompt: str,
        user_prompt: dict[str, Any],
    ) -> dict:
        project = self._project_from_model_uri()
        headers = {
            "Authorization": f"Bearer {self.settings.yandex_gpt_api_key}",
            "Content-Type": "application/json",
        }
        if project:
            headers["OpenAI-Project"] = project
        payload = self._build_openai_compatible_payload(system_prompt, user_prompt)

        async with httpx.AsyncClient(timeout=self.settings.yandex_gpt_timeout_seconds) as client:
            response = await client.post(f"{endpoint}/responses", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        if data.get("status") == "incomplete":
            reason = data.get("incomplete_details", {}).get("reason", "unknown")
            raise YandexGPTUnavailable(f"OpenAI-compatible response is incomplete: {reason}")

        text = data.get("output_text") or self._extract_responses_output_text(data)
        if not text:
            output_types = [item.get("type") for item in data.get("output", [])]
            raise YandexGPTUnavailable(f"OpenAI-compatible response did not contain generated text; output_types={output_types}")
        return self._parse_json_text(text)

    def _build_openai_compatible_payload(self, system_prompt: str, user_prompt: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self.settings.yandex_gpt_model,
            "temperature": 0.2,
            "instructions": system_prompt,
            "input": json.dumps(user_prompt, ensure_ascii=False),
            "max_output_tokens": OPENAI_COMPATIBLE_MAX_OUTPUT_TOKENS,
            "reasoning": {"effort": "low"},
            "text": {
                "format": {"type": "json_object"},
                "verbosity": "low",
            },
            "store": False,
        }

    async def _generate_foundation_models(
        self,
        endpoint: str,
        system_prompt: str,
        user_prompt: dict[str, Any],
    ) -> dict:
        url = endpoint if endpoint.endswith("/completion") else f"{endpoint}/completion"

        headers = {
            "Authorization": f"Api-Key {self.settings.yandex_gpt_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "modelUri": self.settings.yandex_gpt_model,
            "completionOptions": {
                "stream": False,
                "temperature": 0.65,
                "maxTokens": "2000",
            },
            "messages": [
                {"role": "system", "text": system_prompt},
                {"role": "user", "text": json.dumps(user_prompt, ensure_ascii=False)},
            ],
        }

        async with httpx.AsyncClient(timeout=self.settings.yandex_gpt_timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        text = data.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text")
        if not text:
            raise YandexGPTUnavailable("YandexGPT response did not contain generated text")
        return self._parse_json_text(text)

    def _parse_json_text(self, text: str) -> dict:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            cleaned = cleaned.removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise
            return json.loads(cleaned[start : end + 1])

    def _project_from_model_uri(self) -> str | None:
        model = self.settings.yandex_gpt_model or ""
        if not model.startswith("gpt://"):
            return None
        parts = model.removeprefix("gpt://").split("/")
        return parts[0] if parts else None

    def _extract_responses_output_text(self, data: dict) -> str | None:
        chunks: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    chunks.append(text)
        return "\n".join(chunks) if chunks else None
