<!-- capsule-v2 -->
# Payload projection — which payload keys get promoted to top-level results, and where does freeform metadata land?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how do raw vector-store payloads become stable API result shapes across get/get_all/search?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `get` promoted keys (:1224-1250), `_get_all_from_vector_store` (:1342-1377), `_search_vector_store` formatting (:1690-1729); `MemoryItem` model.
**Signature:** promoted list `[user_id, agent_id, run_id, actor_id, role, attributed_to, expiration_date]`; core keys `{data, hash, created_at, updated_at, id, text_lemmatized, attributed_to}`.
**Data Shape:** result = MemoryItem dump (id/memory/hash/created_at/updated_at/score) + promoted keys at top level + everything else nested under `metadata`.

### Decisive source
```python
for key in promoted_payload_keys:
    if key in memory.payload:
        memory_item_dict[key] = memory.payload[key]

additional_metadata = {k: v for k, v in memory.payload.items() if k not in core_and_promoted_keys}
if additional_metadata:
    memory_item_dict["metadata"] = additional_metadata
```

**Flow:** every read path (get / get_all / search) applies the SAME projection: pydantic `MemoryItem` core → promote scope/actor/role/attribution/expiration to the top level (they're query-relevant identity fields) → bucket leftovers into `metadata`. get_all over-fetches (`max(limit*4, 60)`) and cuts at `output_limit` AFTER expiry filtering; search additionally attaches `score_details` when explain=True and skips payloads with no `data`.
**Invariant:** the promoted-keys list is duplicated across three methods by design — a porter centralizing it must keep all three call sites in lockstep or get/search/get_all return different shapes for the same row; internal bookkeeping keys (`text_lemmatized`, `hash`) are never leaked into user-facing metadata.
**Probe:** `tests/test_main.py::test_get_all` (:312 — asserts promoted `user_id` at top level); expired-hiding variants (:335, :351).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "promoted_payload_keys MemoryItem additional_metadata core_and_promoted_keys", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-bucket projection (core/promoted/metadata); adapt key names to your schema; keep the leak-proof exclusion of bookkeeping keys.
