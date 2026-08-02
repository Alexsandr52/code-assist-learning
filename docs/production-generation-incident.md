# Production Lesson Generation Incident

## Context

Production URL: `http://code-learning.angel-save-me.ru:3000`

The application runs as a Docker Compose deployment on Timeweb Cloud. The frontend talks to the backend through the Next.js proxy route under `/api/...`.

## Symptoms

1. Clicking `Начать практику` sent the lesson creation request, but the frontend did not open the generated lesson.
2. On production HTTP, browser console showed:

   ```text
   Unhandled Promise Rejection: TypeError: crypto.randomUUID is not a function
   ```

3. After the frontend crash was fixed, selecting advanced pandas topics such as `Оконные функции` still returned simple fallback lessons.
4. API responses contained:

   ```json
   "source": "fallback"
   ```

   instead of:

   ```json
   "source": "generated"
   ```

## Root Causes

### 1. Browser UUID API Was Not Available On HTTP

`crypto.randomUUID()` is available only in secure browser contexts such as HTTPS or localhost. Production was served over plain HTTP, so anonymous session id creation failed before the UI could process the backend response.

Fix:

- Add a safe anonymous id generator fallback using `crypto.getRandomValues`.
- Add a final timestamp plus `Math.random` fallback.
- Avoid crashing when `localStorage` is unavailable.

### 2. Generic Backend Fallback Ignored Topic And Difficulty

When model generation failed or timed out, backend returned generic fallback content by library. For pandas this was a basic DataFrame lesson, so advanced topics could show beginner-level material.

Fix:

- Make pandas fallback topic-aware.
- Do not cache generic fallback responses in Redis.
- Bump `prompt_version` to avoid reading stale cache entries.

### 3. Backend Had A Hidden 12-Second Generation Budget

YandexGPT requests often need more than 12 seconds. Backend had a hard response budget that forced fallback before the model could return usable content.

Fix:

- Replace the hard-coded 12-second budget with `GENERATION_RESPONSE_BUDGET_SECONDS`.
- Default generation response budget: `45`.
- Increase frontend request timeout to `70` seconds.

### 4. Yandex Responses API Returned Reasoning-Heavy Or Incomplete Responses

The configured model `qwen3.6-35b-a3b` uses reasoning mode by default. Some responses used output tokens for reasoning and returned no message text or incomplete JSON.

Fix:

- Use Responses API JSON mode:

  ```json
  "text": {
    "format": { "type": "json_object" },
    "verbosity": "low"
  }
  ```

- Lower reasoning effort:

  ```json
  "reasoning": { "effort": "low" }
  ```

- Increase `max_output_tokens` to `8000`.
- Lower temperature to `0.2`.
- Add explicit diagnostics for incomplete and textless responses.

## Current Expected Behavior

For a generated lesson request:

```bash
curl -s -X POST 'http://code-learning.angel-save-me.ru:3000/api/practice-sessions' \
  -H 'Content-Type: application/json' \
  -d '{"language":"python","library":"pandas","topic":"rolling-window","difficulty":"advanced","anonymousSessionId":"debug"}'
```

Expected successful markers:

```json
"source": "generated"
```

Repeated requests can also return `"source": "cache"` or `"source": "database"` after generated content has been saved. The marker that still needs investigation is `"source": "fallback"`.

Fallback can still happen if YandexGPT is unavailable, returns invalid content several times, or exceeds the configured timeout. In that case, fallback content should still match the selected library/topic/difficulty closely enough for the user to continue.

## Deployment Checklist

Rebuild the changed services:

```bash
docker compose up -d --build backend frontend
```

Check backend environment:

```bash
docker compose exec backend printenv | grep -E 'YANDEX_GPT|GENERATION_RESPONSE|PROMPT_VERSION'
```

Expected values:

```text
YANDEX_GPT_ENDPOINT=https://ai.api.cloud.yandex.net/v1
YANDEX_GPT_TIMEOUT_SECONDS=45
GENERATION_RESPONSE_BUDGET_SECONDS=45
```

`PROMPT_VERSION` may be absent. If it is present, it should match the current code value:

```text
PROMPT_VERSION=python-library-practice-v5
```

Watch backend logs during a test request:

```bash
docker compose logs -f backend
```

Success log marker:

```text
Generated content accepted
```

Fallback log markers to investigate:

```text
Generation timed out
Generation attempt failed
Content generic fallback used
```

## Verification Performed

- Backend tests: `.venv313/bin/python -m pytest`
- Frontend tests: `npm test`
- Frontend production build: `npm run build`
- Real local YandexGPT end-to-end check returned `source: generated` for `pandas / rolling-window / advanced`.
