<!-- capsule-v2 -->
# bedrock converse provider dual — how does one provider class serve both streaming and non-streaming vendor endpoints?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** When an API exposes two distinct callables per feature mode, where should the switch live?

## callable swap inside provider_call_function
**Path/Symbol:** `src/ell/providers/bedrock.py:BedrockProvider` (:20-160; swap :23-29; translation :30-64).
**Signature:** `provider_call_function(self, client: Any, api_call_params: Optional[Dict[str, Any]] = None) -> Callable[..., Any]`.
**Data Shape:** system param is a LIST of typed parts `[{'text': ...}]`; tools nest `toolSpec` inside `toolConfig={'tools': [...]}`; tool results recurse through the same block formatter.

### Decisive source
```python
# bedrock.py:23-29
def provider_call_function(self, client : Any, api_call_params : Optional[Dict[str, Any]] = None) -> Callable[..., Any]:
    if api_call_params and api_call_params.get("stream", False):
        api_call_params.pop('stream')
        return client.converse_stream
    else:
        return client.converse
```

**Flow:** the lifecycle resolves the endpoint callable *after* translation (see provider-call-lifecycle-validation), so consuming/removing the `stream` key here is safe — it never reaches the vendor payload. Translation then maps ell messages to Converse format: leading system message wrapped as `[{'text': text}]`, model id into `modelId`, tools under `toolConfig.toolSpec` with `inputSchema={'json': schema}`. Response parsing splits streamed (`content_block`-ish events) vs `converse` output dicts (`output.message.content[]` with `text` / `toolUse` entries), both wrapping emitted ids/text in `_lstr(..., origin_trace=origin_id)`.
**Invariant:** exactly one place decides streaming; translators stay mode-agnostic. Image blocks are downloaded-from-URL-or-inline then PNG-encoded into raw bytes (`source.bytes`) at this boundary.
**Probe:** no direct bedrock test at pin (module ImportError-guarded like anthropic — coverage caveat recorded). Deterministic anchors from repo root: `grep -n "client.converse" src/ell/providers/bedrock.py` → lines 27 and 29 (`converse_stream` before `converse`), and `grep -c 'toolSpec' src/ell/providers/bedrock.py` == 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "disallowed api params", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.provider.Provider.disallowed_api_params @ src/ell/provider.py:73-77 — the contract this provider inherits
```

## Verdict
Adopt the resolve-time callable swap for dual-endpoint vendors. Adapt part-typing (`[{'text': ...}]`) to your vendor's union shapes. Omit URL-fetching image serialization in your port if your transport forbids SSRF-prone fetches — pin allowed hosts first.
