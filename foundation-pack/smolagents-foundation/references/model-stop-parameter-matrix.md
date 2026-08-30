<!-- capsule-v2 -->
# Stop-parameter capability matrix — which model IDs silently ignore `stop`, and who trims the tail instead?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** How does the library decide between provider-side stop sequences and client-side post-trimming, and why do o3/o4/gpt-5/grok need special handling?

## Regex denylist + client-side fallback
**Path/Symbol:** `src/smolagents/models.py:supports_stop_parameter` (:418-438), `remove_content_after_stop_sequences` (:79-91), property `Model.supports_stop_parameter` (:498-500); call sites in every adapter `generate` (:534, :738, :847, :1296, :1578, :1782, :2049 — re-audited 2026-08-24; original pin listed phantom :1078, a real site for another guard).
**Signature:** `supports_stop_parameter(model_id: str) -> bool`; `remove_content_after_stop_sequences(content: str | None, stop_sequences) -> str | None`.
**Data Shape:** Denylist regex on the part AFTER any `/`: `(o3(?:$|[-.].*)|o4(?:$|[-.].*)|gpt-5.*)|grok-*` with explicit `o3-mini` allowlist carve-out and an optional org-prefix group for grok (`[A-Za-z][A-Za-z0-9_-]*\.`).

### Decisive source
```python
model_name = model_id.split("/")[-1]
if model_name == "o3-mini":        # mini DOES support stop
    return True
openai_model_pattern = r"(o3(?:$|[-.].*)|o4(?:$|[-.].*)|gpt-5.*)"
grok_model_pattern = r"([A-Za-z][A-Za-z0-9_-]*\.)?grok-[A-Za-z0-9][A-Za-z0-9_.-]*"
return not re.match(rf"^({openai_model_pattern}|{grok_model_pattern})$", model_name)
```

**Flow:** Every generate() passes `stop_sequences` into `_prepare_completion_kwargs`, which includes them as the API `stop` field only when supported. Unsupported models still get stop semantics because each adapter then runs `if stop_sequences is not None and not self.supports_stop_parameter: content = remove_content_after_stop_sequences(content, stop_sequences)` — split-on-first-occurrence per sequence, applied sequentially so content is cut at the EARLIEST of any stop string. Transformers additionally implements StopOnStrings streaming criteria; MLX scans accumulated text inline during stream_generate.
**Invariant:** The two mechanisms must be mutually exclusive per call — sending `stop` to a non-supporting reasoning model is either a 400 or (worse) silently ignored, so trimming must kick in; trimming when the provider DID honor stop is harmless but wasteful. The matrix is data, not architecture: extend the regex as new families ship.
**Probe:** `tests/test_models.py:911` `test_supports_stop_parameter` (parametrized table :884-910 over o3-mini=True / openai/o3=False / o3-2025-04-16=False / o4-mini=False / gpt-5*=False / grok*=False / gpt-4=True / claude=True / path-prefixed supported=True). EXECUTED LIVE 2026-08-24 at the pin via the real function (ambient import): all seven cited table classes PASS as-shipped; `remove_content_after_stop_sequences` verified earliest-of-cut semantics ('aXXbYYc',['YY','XX']→'a'; None/empty passthrough).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "supports_stop_parameter remove_content_after_stop_sequences", limit: 10, fields: ["signature","name","file"] });
// live-verified 2026-08-24: 6 hits, rank-1 supports_stop_parameter :418-438 line-exact
```

## Verdict
Adopt the denylist+carve-out shape and the universal trim-after pattern for adapters that can't trust server-side stops. Adapt the family list over time; keep `o3-mini`'s exception — it documents that versioned variants diverge from their prefix family.
