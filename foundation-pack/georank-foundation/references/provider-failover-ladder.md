<!-- capsule-v2 -->
# Multi-provider LLM failover — one call, three provider tiers, which order and what counts as failure?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** How should an app fan a chat completion across admin-configured providers, a primary model, and a fallback model — and when does streaming still fall back?

## Tiered target ladder with signature-cached clients
**Path/Symbol:** `backend/app/services/ai_client.py` (`_build_provider_targets` :196–221, `_build_chat_targets` :182–193, `_complete_with_fallback` :223–302, `_stream_complete_with_fallback` :304–401, signature-cached client getters :48–111).
**Signature:** `_complete_with_fallback(messages: list[dict], *, temperature: float, model: str | None = None, max_tokens: int | None = None, provider_override=None) -> str`.
**Data Shape:** Runtime config (15s-cached): `llm_providers[{id,name,base_url,model,api_key,priority}]`, strategy `failover|round_robin`, primary `llm_model`, fallback `llm_fallback_model`/`codex_*`. Clients cached per (api_key, base_url) SIGNATURE so admin edits swap clients without restart.

### Decisive source
```python
providers.sort(key=lambda item: (int(item.get("priority") or 999), item.get("id") or ""))
if config.get("llm_provider_strategy") == "round_robin" and len(providers) > 1:
    start = self._provider_cursor % len(providers)
    self._provider_cursor += 1
    providers = providers[start:] + providers[:start]     # rotate, keep relative order
```
Blank output IS a failure (drives fallback):
```python
content = response.choices[0].message.content or ""
if self._is_blank_text(content):
    raise ValueError(f"{target_model} 返回空内容")
...
except Exception as exc:
    errors.append(exc)          # last error re-raised after ALL tiers exhaust
```
Streaming buffers then yields ONCE:
```python
# The upstream stream has already completed and is buffered.
# Yield the merged reply once so a downstream SSE disconnect
# cannot leave accounting with only the first buffered chunk.
yield merged; return
```

**Flow:** explicit BYOK override ⇒ single raw-HTTP call, no tiers. Else tier 1 = enabled providers sorted by priority (round-robin rotates the cursor); tier 2 = primary model on main client; tier 3 = fallback model via codex client. Any exception OR blank content advances the ladder; after exhaustion the LAST error is re-raised. Explicit `model:` argument pins tier-2/1 to that model only. Same ladder exists for streaming, except each provider attempt consumes its whole stream before deciding.
**Invariant:** Errors accumulate across tiers and the final raise carries the most recent cause. A provider with missing api_key/base_url/model is filtered out at target-build time, never half-attempted. Streaming falls back per PROVIDER (whole buffered response), not per token.
**Probe:** `backend/tests/test_ai_client.py::AIClientFallbackTests` (5 tests: transport pinning, private-target rejection pre-client-creation, blank-text fallback ordering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "_complete_with_fallback", limit: 5 });
// verified line-exact: ai_client.py :223–302
```

## Verdict
Adopt the three-tier ladder + blank-as-failure rule for any multi-vendor LLM setup; adapt config keys and cursor storage; omit the raw-HTTP codex branch if you have no legacy endpoint. Direct tests green under real runner.
