---
title: local-gateway-providers
summary: "Use when adding or verifying a local OpenAI-compatible gateway (OmniRoute, LiteLLM, LM Studio) as an OpenCode provider: probe the endpoint and every model before pinning it, then verify end to end."
kind: playbook
---

# Local gateway providers

A gateway's advertised inventory is not the same as its working routes. An id in
`/v1/models`, and even a registry entry, can be stale, retired, or hang upstream.
Probe before configuring and pin only what answers.

## Probe the gateway

1. Confirm the endpoint and inventory without credentials when possible:
   `curl -s http://127.0.0.1:<port>/v1/models`.
2. Send a one-line chat completion for every model you intend to pin. Keep
   `max_tokens` small and capture status and latency:
   `-w '\nHTTP %{http_code} in %{time_total}s\n'`. If a non-streaming call
   hangs, retest with `"stream": true`; keepalive-only chunks are still broken.
3. Treat 120 s zero-byte responses as broken routes no matter what the inventory
   claims. Check the gateway's provider health endpoint (for OmniRoute,
   `/api/providers`) to separate an inactive account from a dead model route.
4. Prefer ids the gateway routes itself (`antigravity/gemini-3.8-flash-tiered`)
   over aliases (`agy/gemini-3.6-flash-low`): aliases can outlive the models
   they point at.

## Configure OpenCode

```jsonc
{
  "providers": {
    "gateway": {
      "name": "Gateway",
      "package": "aisdk:@ai-sdk/openai-compatible",
      "settings": {
        "baseURL": "http://127.0.0.1:<port>/v1",
        "apiKey": "local-placeholder"
      },
      "models": {
        "<model-id>": { "name": "Display Name" }
      }
    }
  }
}
```

Only configured `models` keys become selectable. Keep the list short and
verified; add more only when a task needs them. When the gateway ignores auth,
a placeholder `apiKey` avoids missing-key errors in the runtime package.

## Verify end to end

Pin a throwaway subagent to `gateway/<model-id>` and run one real task, then
delete it; parsing a valid config is not proof the route works. Keep judgment
work on a stable provider while a new gateway's routes are being trusted, and
move lanes over after they pass.
