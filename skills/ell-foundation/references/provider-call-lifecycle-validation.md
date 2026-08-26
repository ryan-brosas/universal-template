<!-- capsule-v2 -->
# provider call lifecycle validation — where is the single choke point every provider call passes through?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I let third parties add vendor providers while guaranteeing they cannot silently break provenance or the param contract?

## Provider.call template method
**Path/Symbol:** `src/ell/provider.py:Provider.call` (:107-134), validators `_validate_provider_call_params` (:143-164) and `_validate_messages_are_tracked` (:166-179), `disallowed_api_params` (:73-77).
**Signature:** `call(self, ell_call: EllCallParams, origin_id: Optional[str] = None, logger: Optional[Any] = None) -> Tuple[List[Message], Dict[str, Any], Metadata]`.
**Data Shape:** abstract surface is four methods: `provider_call_function` (client → callable), `translate_to_provider`, `translate_from_provider`, plus overridable `disallowed_api_params` defaulting to `frozenset({"messages", "tools", "model", "stream", "stream_options"})`.

### Decisive source
```python
# provider.py:115-134
assert (
    not set(ell_call.api_params.keys()).intersection(self.disallowed_api_params())
), f"Disallowed api parameters: {ell_call.api_params}"

final_api_call_params = self.translate_to_provider(ell_call)

call = self.provider_call_function(ell_call.client, final_api_call_params)
assert self.dangerous_disable_validation or _validate_provider_call_params(final_api_call_params, call)

provider_resp = call(**final_api_call_params)

messages, metadata = self.translate_from_provider(
    provider_resp, ell_call, final_api_call_params, origin_id, logger
)
assert "choices" not in metadata, "choices should be in the metadata."
assert self.dangerous_disable_validation or _validate_messages_are_tracked(messages, origin_id)
```

```python
# provider.py:172-178 — the provenance tripwire
for message in messages:
    assert isinstance(
        message.text, _lstr
    ), f"Provider implementation error: Message text should be an instance of _lstr, got {type(message.text)}"
    assert (
        origin_id in message.text.__origin_trace__
    ), f"Provider implementation error: Message origin_id {message.text.__origin_trace__} does not match the provided origin_id {origin_id}"
```

**Flow:** param veto → translate out → resolve endpoint callable → (unless disabled) structural check that translated params exactly cover the callable's signature → execute → translate back → metadata hygiene ("choices" must be excluded so it never collides with message content) → provenance check. `_validate_messages_are_tracked` returns early when `origin_id is None` (untracked calls skip).
**Invariant:** a provider cannot return untracked text without tripping an assert at call time — this is why every built-in translator wraps content in `_lstr(..., origin_trace=origin_id)`. The escape hatch `dangerous_disable_validation` is per-class and explicit: openai/anthropic/bedrock/groq set True; google keeps False.
**Probe:** `tests/test_openai_provider.py:test_provider_call_function_with_response_format` (:66-83) pins the endpoint-selection seam (`beta.chat.completions.parse` vs `chat.completions.create`) inside this lifecycle.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "tracked messages provider origin", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.provider._validate_messages_are_tracked @ src/ell/provider.py:166-179
```

## Verdict
Adopt the template-method choke point with assert-based implementer guardrails — it converts provider bugs into immediate, named failures instead of silent data loss. Adapt which params are vendor-vetoed to your API. Omit the lru_cache on signature inspection only if your client objects are not stable across calls.
