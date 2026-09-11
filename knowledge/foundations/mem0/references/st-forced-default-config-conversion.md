<!-- capsule-v2 -->
# SentenceTransformer reranker forced-default config conversion — a base config is silently rebuilt with hardcoded runtime knobs

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** what happens when the factory hands this reranker a generic `BaseRerankerConfig` instead of its own config class?

## Connected graph-selected seam
**Path/Symbol:** `mem0/reranker/sentence_transformer_reranker.py`: `SentenceTransformerReranker.__init__` (:24-50).
**Signature:** `__init__(self, config: Union[BaseRerankerConfig, SentenceTransformerRerankerConfig, Dict])`.
**Data Shape:** accepts dict → kwargs-constructs own config; base-class instance → REBUILT as own class; own class → used as-is.

### Decisive source
```python
if isinstance(config, dict):
    config = SentenceTransformerRerankerConfig(**config)
elif isinstance(config, BaseRerankerConfig) and not isinstance(config, SentenceTransformerRerankerConfig):
    # Convert BaseRerankerConfig to SentenceTransformerRerankerConfig with defaults
    config = SentenceTransformerRerankerConfig(
        provider=getattr(config, 'provider', 'sentence_transformer'),
        model=getattr(config, 'model', 'cross-encoder/ms-marco-MiniLM-L-6-v2'),
        api_key=getattr(config, 'api_key', None),
        top_k=getattr(config, 'top_k', None),
        device=None,  # Will auto-detect
        batch_size=32,  # Default
        show_progress_bar=False,  # Default
    )
```

**Flow:** dict → direct construction (typos become TypeError) → foreign base config → rebuild carrying over the four shared fields and FORCING `device=None` (auto-detect), `batch_size=32`, `show_progress_bar=False` — any values a caller set on those three knobs on the base object are DISCARDED, not copied.
**Invariant:** the conversion is total-replace, not field-merge: after this branch the object's runtime knobs are exactly the literals above. A "polite" port that copies unknown attrs through (`device=..., batch_size=...`) changes behavior for every base-config caller. The default model `cross-encoder/ms-marco-MiniLM-L-6-v2` lives in THIS branch only — an own-class config with `model=None` reaches `CrossEncoder(None)` and fails at model load.
**Probe:** `grep -cF 'batch_size=32,  # Default' mem0/reranker/sentence_transformer_reranker.py` (=1); `grep -cF 'device=None,  # Will auto-detect' mem0/reranker/sentence_transformer_reranker.py` (=1); `grep -cF "'cross-encoder/ms-marco-MiniLM-L-6-v2'" mem0/reranker/sentence_transformer_reranker.py` (=1).
**Coverage caveat (scoped):** the LLM reranker's config-conversion twin IS tested (`tests/rerankers/test_llm_reranker_config.py::test_init_converts_base_reranker_config` :48), but the SentenceTransformer conversion branch itself carries no dedicated test at this pin — the forced-default literals above are source-pinned only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "SentenceTransformerReranker BaseRerankerConfig convert defaults", limit: 10 });
```

## Verdict
Adopt the three-shape init contract with forced-default conversion for base configs; adapt the knob defaults (batch size, device policy) to your runtime; omit any attempt to preserve non-contract attributes across the conversion — that path is deliberately lossy.
