<!-- capsule-v2 -->
# Model context-size resolution — how do you get the real context window when provider profiles lie and model ids come in every casing/prefix?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you resolve a model's context window for summarization/completion budgeting when the model name may be prefixed, differently-cased, unknown, or capped by deployment?

## Longest-prefix lookup + profile write-back
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/token_counter.py:30-354` (`MODEL_CONTEXT_SIZES`, `_SORTED_MODEL_CONTEXT_KEYS`, `lookup_model_context_size`, `resolve_model_identifier`, `ensure_model_context_profile`), default `DEFAULT_CONTEXT_SIZE = 131072` (:19).
**Signature:** `lookup_model_context_size(model_name: Optional[str]) -> Optional[int]`; `ensure_model_context_profile(model=None, model_name=None) -> int`; `resolve_model_identifier(model, fallback_name="") -> str`.
**Data Shape:** table maps BOTH bare (`gpt-4o`) and prefixed (`openai/gpt-4o`, `rits/openai/gpt-oss-120b`) ids to window sizes; prefix index pre-sorted by key length DESC so the longest matching prefix wins.

### Decisive source
```python
normalized_name = model_name.strip()
if "/" in normalized_name:
    normalized_name = normalized_name.split("/", 1)[1]   # strip ONE provider prefix
# Case-insensitive exact + longest-prefix match (model ids vary in casing).
if normalized_lower in MODEL_CONTEXT_SIZES:
    return MODEL_CONTEXT_SIZES[normalized_lower]
for key in _SORTED_MODEL_CONTEXT_KEYS:                    # longest-first
    if normalized_lower.startswith(key.lower()):
        return MODEL_CONTEXT_SIZES[key]
```
Deployment-cap comment on the gemma entry (:204-208):
```python
# Deployment cap, not the 262,144 native window: the RITS vLLM deployment serves
# max_model_len=131072 (probed via GET .../v1/models, 2026-07-28). Registering the
# native window put the 70% summarization trigger (~183k) beyond the deployment's
# 131k cliff, so summarization could never engage on Gemma (issue #563).
"gemma-4-31B-it": 131072,
```

**Flow:** resolve id (ChatWatsonx → `model_id` attr; else first of `model_id`/`model_name`/`model`) → strip one provider prefix → case-insensitive exact → longest-prefix → None → caller defaults to 131072. `ensure_model_context_profile` then MERGES `max_input_tokens` into `model.profile` (preserving other profile keys) so LangChain's SummarizationMiddleware reads the same number.
**Invariant:** register DEPLOYMENT caps, not native windows — a too-large window silently disables percentage-based summarization triggers forever; known-name mappings deliberately take precedence over provider profiles because "some integrations (e.g. ChatWatsonx) ship with generic 8K profiles that do not match large-context models" (:637-639); unknown models warn loudly with instructions to extend the table.
**Probe:** no direct unit test for this module (coverage caveat — deterministic check: `_SORTED_MODEL_CONTEXT_KEYS` is built once at import sorted by length desc; `lookup_model_context_size("rits/openai/gpt-oss-120b")` must return 131072 via exact-after-prefix-strip). Downstream consumers (`ContextSummarizer`, watsonx clamp) are behavior-tested.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "lookup_model_context_size MODEL_CONTEXT_SITES ensure_model_context_profile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the longest-prefix case-insensitive lookup + single-prefix-strip + explicit deployment-cap policy + profile merge write-back as a unit — porting only half (e.g. trusting provider profiles) reproduces issue #563 class bugs where summarization never fires; adapt the table contents to your model fleet; omit ChatWatsonx special-casing if you don't serve watsonx. Coverage caveat: no direct test file; verified by whole-source read and by consumers' tests.
