<!-- capsule-v2 -->
# Chunking tokenizer dispatch — one dispatcher, two caps: why safe_max ≠ recommended, and why every HF chunk gets a −16 margin?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Given any embedding provider+model string, what tokenizer counts chunks — and what two numbers come out of it that callers must not conflate?

## Single dispatcher + hard-ceiling vs retrieval-quality default
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:4462-4583` (`get_chunking_tokenizer`), frozen dataclass `ChunkingTokenizer` `:1436-1460`, `_hf_tokenizer_seq_limit` `:1400-1417`, `_HF_TOKEN_SAFETY_MARGIN = 16` `:1397` (smoking-gun comment `:1372-1396`), `_recommended_chunk_tokens` `:1511-1529`, `_TIKTOKEN_SAFE_MAX = 8191-16 = 8175` `:1477-1484`, oversized-chunk warning `lru_cache`'d at `:1491-1509`; consumers `_build_text_splitter`/`_build_docling_chunker`.
**Signature:** `get_chunking_tokenizer(self) -> ChunkingTokenizer(kind ∈ {hf,tiktoken,fastembed,approximate}, encoder, name, safe_max_tokens, recommended_chunk_tokens)`; `_hf_tokenizer_seq_limit(tok) -> max(1, raw - 16)`.
**Data Shape:** Dispatch (first match wins): (1) fastembed → its own Rust ONNX tokenizer; (2) huggingface → embedder's `_tokenizer`; (3a) openai-native or `openai/`·`azure/` inner route after stripping ONE outer prefix (`litellm/` or `openrouter/`) → tiktoken `cl100k_base`; (3b) any other slash-containing model → HF Hub AutoTokenizer via `_hf_repo_id_candidate` aliases (Hub is source of truth, no curated allow-list); (4) else → `approximate` char-based cap 8192.

### Decisive source
```python
# engine.py:1372-1385 — the bug the 16-token margin fixes
#       (b) e5-family "query: " / "passage: " prefix that hosted
#       providers (notably watsonx) auto-prepend before embed — 3-4
#       XLM-RoBERTa tokens the chunker never sees.
#
# User-reported smoking gun on PR #383 manual QA:
# chunker capped at 512, watsonx still rejected with
#   This model's maximum context length is 512 tokens. However, you
#   requested 518 tokens
# — a +6 overhead consistent with prefix + BOS. 16 is generous enough
# for any current provider's wrapping.
```
The TWO caps and their evidence: `safe_max_tokens` is the HARD CEILING (embedder truncates/rejects above it; already margined for HF kinds). `recommended_chunk_tokens = min(safe_max, 512) if safe_max >= 2048 else safe_max` — for ≥2K-context embedders chunks should stay ≤512 REGARDLESS of window size because pooled embeddings dilute the signal across more concepts (LongEmbed EMNLP 2024 +24% MRR for 512 vs 1024+; BAAI bge-m3 maintainer; voyage-context-3 ships 512 on a 32K model). Callers use `min(chunk_size, safe_max)` and get an lru_cache-deduped WARNING when `chunk_size > recommended` so long-context users don't crank chunk_size thinking more context = better. Sentinel `model_max_length >= 1e6` means unset → 512−margin (BERT/XLM-R convention); tiktoken branch uses 8191−16 to match the HF margin exactly (an earlier zero-margin 8192 was flagged off-by-one in review).

**Flow:** builder asks dispatcher once → INFO log records which branch ran (`[#400] tokenizer-dispatch ...`, operators need this by default when diagnosing context-window errors) → splitter/chunker switch on `tok.kind` → cap = `min(chunk_size, tok.safe_max_tokens)`, overlap clamped to `max(cap // 4, 1)` → oversized-vs-recommended warning fires once per (model, chunk_size, recommended) tuple per process.
**Invariant:** Never count tokens with a different tokenizer than the embedder will apply at request time; always subtract provider-side wrapping (special tokens, prefixes) from the advertised window. The two caps answer different questions — "will the API reject it" vs "will retrieval be good" — and must remain separate fields.
**Probe:** `tests/unit/test_knowledge_chunker_hf_tokenizer.py:156` (`test_regression_518_over_512_watsonx_e5`), `:129-156` (512/8192/sentinel/missing/zero defaults), `:179` (margin never underflows to 0), `:199-240` (tokenizer load caching: failure NOT cached, retries next call); `tests/unit/test_knowledge_resplit_unit_mismatch.py:111-176` (tiktoken capped at safe-max, cohere/voyage/gemini/fastembed/HF-load-failure all fall back to chars).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ChunkingTokenizer get_chunking_tokenizer _hf_tokenizer_seq_limit _recommended_chunk_tokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-dispatcher contract with kind-tagged result, dual caps (hard ceiling vs quality recommendation), the −16 wrap margin, and dedup'd advisory warnings. Adapt branch order to your provider set. Omit the fastembed Rust-tokenizer subclass if you don't ship fastembed.
