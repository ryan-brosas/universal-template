<!-- capsule-v2 -->
# Update ladder — how does a memory update change text/metadata/expiration without ever moving its scope or corrupting history?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** what is the exact update choreography across payload merge, re-embed, history, and entity-store repair?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `update` (:1815-1867), `_update_memory` (:2032-2092); identity guard `_strip_identity_keys` (:143-162) with `existing_payload` context.
**Signature:** `update(memory_id, text=None, metadata=None, expiration_date=_UNSET, data=None)` — `data` is the deprecated alias; at least one of text/metadata/expiration_date required.
**Data Shape:** merged payload = deepcopy(existing payload) ⊕ caller metadata (identity keys stripped) ⊕ recomputed `data`/`hash`/`text_lemmatized`; `created_at` preserved from the existing payload, `updated_at` set to now.

### Decisive source
```python
new_metadata = deepcopy(existing_memory.payload)
if metadata is not None:
    new_metadata.update(_strip_identity_keys(metadata, existing_memory.payload))
...
self.db.add_history(memory_id, prev_value, data, "UPDATE",
                    created_at=new_metadata["created_at"],
                    updated_at=new_metadata["updated_at"], ...)
# Entity-store cleanup: strip this memory's id from old-text entities,
# then re-extract entities from the new text and link them back.
session_filters = {k: new_metadata[k] for k in ("user_id", "agent_id", "run_id") if new_metadata.get(k)}
if text_changed:
    self._remove_memory_from_entity_store(memory_id, session_filters)
    self._link_entities_for_memory(memory_id, data, session_filters)
```

**Flow:** validate something-to-update → normalize expiration (or `None` to CLEAR it — sentinel `_UNSET` distinguishes "not passed" from "clear") → pre-embed new text once in `update()` and pass it via `existing_embeddings` so `_update_memory` never re-embeds → fetch existing (store failure RE-RAISES as 5xx-worthy; missing id raises ValueError 4xx-worthy) → deep-merge payload → vector_store.update → history row `(prev_value, data, "UPDATE")` with preserved created_at → if TEXT changed only: unlink old entities then relink from new text.
**Invariant:** scope keys (`user_id/agent_id/run_id/actor_id`) are immutable after creation — identical re-sends are silently accepted via `existing_payload`, changed values warn-and-drop; `created_at` survives every update; expiration clearing uses explicit `None` because a falsy check would conflate it with "not passed"; entity repair runs ONLY on text change (metadata-only updates skip it).
**Probe:** `tests/memory/test_main.py::test_update_memory_metadata_cannot_change_identity_fields` (:438); `tests/test_main.py::test_update_can_change_expiration_date_without_changing_text` (:241).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_update_memory strip_identity_keys update expiration_date immutable scope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the payload-deepcopy-merge + immutable-scope + created_at-preservation trio; adapt the deprecation aliasing; omit nothing — the entity-repair-on-text-change ordering is load-bearing for store consistency.
