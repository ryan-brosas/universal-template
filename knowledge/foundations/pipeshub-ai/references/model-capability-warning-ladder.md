<!-- capsule-v2 -->
|# Model-capability warning ladder — how do you fail fast on an embedding model that cannot accept images, without blocking a config that might?

## Constructor-time marker scan ⇒ one loud warning; the request still goes out and per-image results carry the provider's real answer
**Path/Symbol:** `backend/python/app/services/embeddings/multimodal/jina_provider.py` :25–51 (`_IMAGE_CAPABLE_MODEL_MARKERS` :25, `supports_image_input` :28–30, constructor warning :46–51); `gemini_provider.py` :29–54 (`_TEXT_ONLY_MODEL_MARKERS`, `supports_image_input` NEGATED :32–34, `_normalize_model_name` :56–59, warning :50–54); twin `cohere_provider.py::supports_inputs_image_batch` :34–37.
**Signature:** `def supports_image_input(model_name: str | None) -> bool`; warning fired only when `logger` is provided AND capability is negative.
**Data Shape:** Jina ALLOW-list substrings `("jina-clip", "jina-embeddings-v4", "jina-embeddings-v5")`; Gemini DENY-list `("gemini-embedding-001", "gemini-embedding-exp", "text-embedding-")`; Cohere `"v4" in name or "embed-4" in name`. All lower-case the name first; `None` model name ⇒ not capable.

### Decisive source
```python
# jina_provider.py — dispatch is on the MODEL NAME: text-only models reject
# {"image": ...} with a 422 rather than embedding it.
_IMAGE_CAPABLE_MODEL_MARKERS = ("jina-clip", "jina-embeddings-v4", "jina-embeddings-v5")
def supports_image_input(model_name): return any(m in (model_name or "").lower() for m in ...)

# gemini_provider.py — INVERTED: deny-list, default-capable.
_TEXT_ONLY_MODEL_MARKERS = ("gemini-embedding-001", "gemini-embedding-exp", "text-embedding-")
def supports_image_input(model_name):
    return not any(marker in name for marker in _TEXT_ONLY_MODEL_MARKERS)
...
self.model_name = self._normalize_model_name(model_name)  # "models/" prefix ADDED if absent
```

**Flow:** constructor checks the configured model against its marker list → logs ONE warning naming a usable alternative ("use gemini-embedding-2 for multimodal embedding" / "Use a jina-clip-* or jina-embeddings-v4/v5 model") → proceeds anyway. The request path never consults the predicate; the provider's real response decides success. Gemini additionally canonicalizes the SDK's required `models/` prefix at construction.
**Invariant:** the allow/deny POLARITY is provider-specific because each vendor fails differently (Jina: schema-dispatched 422; Gemini: every image fails with no obvious cause). A warn-and-proceed ladder must NOT become a hard gate here — configs drift ahead of code and the per-image result object already carries the failure.
**Probe:** `backend/python/tests/unit/services/embeddings/multimodal/test_jina_provider.py::TestJinaModelCapability::test_image_capability_by_model` (:203 parametrized incl. `None→False`) + `::test_text_only_model_warns_at_construction` (:208) + `::test_image_capable_model_does_not_warn` (:215).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "supports_image_input _TEXT_ONLY_MODEL_MARKERS supports_inputs_image_batch", limit: 10 });
```

## Verdict
Adopt warn-don't-gate constructor capability checks with per-vendor marker polarity (allow-list where vendors schema-dispatch, deny-list where they silently fail); adapt marker vocabularies as vendors ship new models; omit PipesHub-specific model names once your roster differs. Direct tests ship upstream for the Jina side (parametrized + both warning branches); Gemini/Cohere predicates are pinned by source inspection only (coverage caveat).
