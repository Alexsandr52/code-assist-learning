from app.core.config import Settings
from app.yandex_gpt.client import OPENAI_COMPATIBLE_MAX_OUTPUT_TOKENS, YandexGPTClient


def test_openai_compatible_payload_requests_json_with_low_reasoning():
    client = YandexGPTClient(
        Settings(
            yandex_gpt_endpoint="https://ai.api.cloud.yandex.net/v1",
            yandex_gpt_api_key="test-key",
            yandex_gpt_model="gpt://folder/qwen3.6-35b-a3b/latest",
        )
    )
    payload = client._build_openai_compatible_payload("system", {"task": "test"})

    assert payload["temperature"] == 0.2
    assert payload["max_output_tokens"] == OPENAI_COMPATIBLE_MAX_OUTPUT_TOKENS
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["text"]["format"] == {"type": "json_object"}
    assert payload["text"]["verbosity"] == "low"
