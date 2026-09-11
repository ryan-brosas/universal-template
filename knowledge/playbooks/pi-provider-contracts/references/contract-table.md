# Pi Provider Runtime Contract Table

Verified against `@earendil-works/pi-ai` + `@earendil-works/pi-coding-agent` 0.84.x source and live wire captures (session 2026-09-03, pi-omniroute PRs #25-#28).

## Auth resolution (pi-ai/dist/auth/resolve.js)

| Question | Answer |
| --- | --- |
| Stored `/login` credential vs configured `apiKey`? | The stored credential **owns** the provider; the config key (literal, `$ENV`, `${ENV}`, `!command`) resolves only when nothing is stored. |
| `apiKey: "$ENV_VAR"` with the env var unset? | `check()` reports unconfigured (models hidden). If it was set at registration and disappears, request-time resolution throws. |
| `apiKey: "literal"` with no credential? | Always resolves; the provider is "configured" with the literal. This is how keyless providers stay visible. |
| Credential shape | `{ type: "api_key", key?: string, env?: ... }` — `key` is optional. |

## Header assembly (provider-composer.js + OpenAI client buildHeaders)

| Question | Answer |
| --- | --- |
| When does `before_provider_headers` run relative to the SDK's auth? | **Before.** pi assembles a header map from `auth.headers` + options headers; the OpenAI SDK adds `Authorization` from the resolved `apiKey` later, during `buildHeaders`. |
| Does the hook see the provider's Authorization? | Only if something put it there: `authHeader: true`, provider `headers`, or model headers. A plain `apiKey` config contributes nothing to the hook's map. |
| How to delete a header the SDK adds? | A `null` value in `defaultHeaders` (merge order `[idempotency, base, authHeaders, defaultHeaders, bodyHeaders, options.headers]`), case-insensitive by name. |
| Keyless placeholder pattern | Register `apiKey: "<placeholder>"` + `authHeader: true`, then null `authorization` in `before_provider_headers` when the resolved key equals the placeholder. The null in `defaultHeaders` deletes the SDK's Bearer. |
| Hook cadence | Once per provider request; retries reuse the headers without re-firing. |

## Catalog lifecycle (models.js / provider-composer.js / agent-session-services.js)

| Question | Answer |
| --- | --- |
| Who swaps the model list after `refreshModels`? | The composed wrapper publishes `update()` which stores the returned list; the extension does not need to re-register (and re-registering loops: registration fires an offline refresh). |
| When is refresh online? | Only interactive sessions (session start, `/model` picker). Session bootstrap, registration, and headless `-p` are `allowNetwork: false`. `pi update --models` uses a bare runtime **without extension registration**, so extension providers never refresh there. |
| Snapshot persistence | `publish({persist})` lands in `~/.pi/agent/models-store.json` (FileModelsStore) verbatim via `structuredClone` + `JSON.stringify`: extra scoping fields (`url`, `scope`, `cut`) survive. Type-cast is out-of-band; if pi sanitizes entries later, mismatches must degrade safely. |
| Offline phases | `allowNetwork: false` serves the stored snapshot or the static fallback; never fetches. |

## Request payload (pi-ai/dist/api/openai-completions.js)

| Question | Answer |
| --- | --- |
| When is `reasoning_effort` sent? | `model.reasoning && compat.supportsReasoningEffort && thinking != off`. With thinking off and no `thinkingLevelMap.off`, nothing is sent. |
| System prompt role | Sent as `developer` (OpenAI-style); gateways must translate for non-OpenAI backends. |
| `max_tokens` | Not sent by pi (model.maxTokens is local budgeting only). |
| Vision | Driven by `model.input`; over-claiming sends images to text-only upstreams. |

## Wire-verification recipe

1. Controlled loopback HTTP server with synthetic credentials only: record method, path, presence or synthetic-sentinel equality for every configured credential channel (Authorization, custom headers, and provider-defined fields), and only required payload fields. Never retain live credential values or unrelated prompt bodies; answer `/v1/models` with a catalog, `/v1/chat/completions` with a minimal SSE stream (`delta.content` chunk, finish chunk with usage, `data: [DONE]`).
2. Clean environment: `PI_CODING_AGENT_DIR=<tmp>` with a settings file listing only the package under test. Use `--no-session --no-tools -p '<prompt>'` for request verification. For online catalog behavior, separately run the real interactive session and `/model` refresh; verify `/v1/models` and catalog updates. Headless requests and `pi update --models` do not prove extension online refresh.
3. Scenarios: keyless (expect no `Authorization`), keyed (expect the synthetic sentinel), reasoning model with `--thinking high` (expect `reasoning_effort`), unknown provider/model fallback. Live credentials require an authorized HTTPS endpoint with certificate verification and redacted evidence. Test redirects using synthetic sentinels: reject redirects or permit only approved destinations, inspect each hop, and verify no credential channel reaches an unapproved destination. Do not probe unapproved destinations with live credentials.
4. Read the log after each run; before/after captures are the review evidence.

## Traps that cost us time

- A fake-pi probe injected an `authorization` header into the hook event that the real pipeline never puts there, so the probe passed while the wire leaked. Fake harnesses prove extension logic, never transport ordering.
- `pi update --models` looks like a catalog refresh but runs without extensions: extension providers do not refresh there.
- `ModelsStoreEntry` is an open struct: extra fields persist, but they are undocumented; version them (`cut`) and reject mismatches so upgrades cannot leak old cuts.
- Array `.filter(fn)` passes the element, not a property: `live.filter(isRouteId)` crashes when `isRouteId` expects an id string.
- `mergeCatalogs` does not union the curated list; it merges fields for live ids and guarantees only the injected router id.
