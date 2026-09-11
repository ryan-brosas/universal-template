<!-- capsule-v2 -->
# V3 phased add pipeline — how does one additive LLM call become batch-persisted memories without hallucinated IDs?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how does `add()` turn messages into stored memories in the shipped V3 phased batch pipeline, and what must a porter preserve so the LLM can never invent or corrupt memory IDs?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `_add_to_vector_store` (:879-1206) — Phase 0 context (:918-921), Phase 1 retrieval + UUID mapping (:923-938), Phase 2 single-call extraction (:940-989), Phase 3 batch embed (:991-1003), Phases 4-5 dedup (:1005-1043), Phase 6 batch persist (:1045-1084), Phase 7 batch entity linking (:1086-1190), Phase 8 save (:1192-1206).
**Signature:** `_add_to_vector_store(self, messages, metadata, filters, infer, prompt=None)`; non-infer branch (:880-914) stores each message raw with per-msg role/actor metadata.
**Data Shape:** extraction response parsed as `json.loads(response).get("memory", [])`; each item `{"text": str, "attributed_to"?: str}`; records tuple `(memory_id, text, embedding, payload)`; payload carries `data`, `text_lemmatized`, `hash` (md5 of text), `created_at`/`updated_at` (UTC ISO).

### Decisive source
```python
# Map UUIDs to integers (anti-hallucination)
existing_memories = []
uuid_mapping = {}
for idx, mem in enumerate(existing_results):
    uuid_mapping[str(idx)] = mem.id
    existing_memories.append({"id": str(idx), "text": mem.payload.get("data", "")})
# ...LLM sees ONLY integer ids; ADD events mint fresh uuid4 ids server-side...
except Exception as e:
    # Re-raise so callers can implement provider fallback / retry.
    # The original silent ``return []`` made upstream callers unable to
    # distinguish "LLM unavailable" (429/5xx/timeout) from "LLM
    # extracted no facts" -- both surfaced as an empty list.
    raise LLMError(f"LLM extraction failed: {e}") from e
```

**Flow:** parse messages → embed the conversation → fetch top-10 existing scoped memories → hand the LLM integer-indexed candidates (ADDITIVE_EXTRACTION_PROMPT, agent suffix when agent-scoped) → one JSON response yields new facts → batch-embed (`embed_batch`, per-item fallback) → drop duplicates by md5 hash against BOTH the fetched set and within-batch `seen_hashes` → batch `vector_store.insert` with per-row fallback → `batch_add_history` with per-row fallback → batch entity linking (7a global dedup → 7b batch embed with None-padding when counts mismatch → 7c `search_batch` top_k=1 → 7d exact-or-semantic(≥0.95) match splits updates vs inserts → 7e single batch insert) → `db.save_messages` under the session scope.
**Invariant:** the LLM never sees real vector IDs (integer mapping is the anti-hallucination fence); hash dedup runs before any insert so identical text can never double-store; every batch operation degrades to per-item without failing the whole batch; empty extraction still saves the messages to SQLite; LLM transport failure RAISES (`LLMError`) instead of returning `[]`.
**Probe:** `tests/test_main.py` add suites; `tests/memory/test_main.py` (extraction parsing, identity stripping); `tests/utils/test_entity_extraction.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_add_to_vector_store phased batch pipeline uuid_mapping additive extraction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the phase ordering, integer-ID fence, hash-dedup-before-insert, and batch-with-per-row-fallback shape; adapt prompt text and provider JSON mode; omit the hosted-platform variants. Caveat: prompts live in `mem0/configs/prompts.py` (data pack, not mined).
