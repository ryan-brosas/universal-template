<!-- capsule-v2 -->
# LLM cache key mutation ordering — clean, frame, THEN hash

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** when a cache key is derived from request messages, which mutations must happen before hashing — and what breaks if you reorder them?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/llm_client/client.py:generate_response` (:197-267) — preamble (:213) → schema injection (:215-221) → language instruction (:224) → `_clean_input` loop (:226-227) → span + cache lookup (:242-248) → retried call → cache write (:263-265); key builder `_get_cache_key` (:153-157); enablement `__init__` (:91-92).
**Signature:** `_get_cache_key(messages: list[Message]) -> str` = md5 of `{self.model}:{json.dumps([m.model_dump() for m in messages], sort_keys=True)}`.
**Data Shape:** Message is `{role: str, content: str}`; the cache stores the provider-shaped response dict; hit/miss recorded as span attributes (`cache.hit`).

### Decisive source
```python
# client.py generate_response — ORDER IS THE CONTRACT
self._apply_attribute_extraction_preamble(messages, attribute_extraction)
if response_model is not None:
    messages[-1].content += (                      # schema rides LAST message
        f'\n\nRespond with a JSON object in the following format:'
        f'\n\n{serialized_model}')
messages[0].content += get_extraction_language_instruction(group_id)
for message in messages:
    message.content = self._clean_input(message.content)   # BEFORE hashing
...
cache_key = self._get_cache_key(messages)          # hash POST-mutation
```

**Flow:** every content-shaping step mutates `messages` in place BEFORE the key derivation, so two semantically-identical calls produce byte-identical message lists and therefore identical keys — including callers that pre-inject their own preamble (sentinel makes re-application idempotent).
**Invariant:** (1) cache key = post-transformation view: cleaning zero-width chars / control chars / invalid unicode BEFORE md5 means dirty-vs-clean input variants share one entry instead of doubling spend; (2) model name prefixes the digest so swapping providers can never serve cross-provider outputs; (3) `sort_keys=True` canonicalizes each dumped Message regardless of field order; (4) the schema suffix and language instruction are part of the identity — a porter who hashes BEFORE injecting them serves schema-less cached text to typed callers (silent parse failures downstream); (5) writes happen only after successful retry, never on exception paths.
**Probe:** `cd $REFERENCE_ROOT/memory/graphiti && grep -n 'message.content = self._clean_input(message.content)' graphiti_core/llm_client/client.py` → `227:` (line number < 243 where `cache_key = self._get_cache_key(messages)` first appears); `grep -c 'sort_keys=True' graphiti_core/llm_client/client.py` → `1`; direct tests `tests/llm_client/test_cache.py::test_set_and_get` + `::test_corrupted_entry_returns_none` pin store semantics; ordering itself pinned by source read :213-264.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "_get_cache_key _clean_input generate_response cache_key md5", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt derive-key-from-post-transformed-request for any response cache in front of an LLM or other normalizing layer; adapt the transformation list to your pipeline. Reordering cleanup after hashing is invisible in tests and doubles cost on dirty input — exactly the class of bug this capsule exists to prevent.
**Overlap note:** storage mechanics are owned by `llm-cache-sqlite.md`; transient/retry taxonomy by `llm-client.md`; THIS capsule owns only the key-derivation ordering.
