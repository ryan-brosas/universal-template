<!-- capsule-v2 -->
# Knowledge file-binding lifecycle — how do you bind/unbind files to a shared collection so failures never strand either side?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** In what order must embedding, binding-row writes, and destructive cleanup run when attaching, refreshing, or removing a file from a knowledge collection?

## Add / update / remove handler trio
**Path/Symbol:** `backend/open_webui/routers/knowledge.py:add_file_to_knowledge_by_id` (:1371–1464), `update_file_from_knowledge_by_id` (:1468–1548), `remove_file_from_knowledge_by_id` (:1557–1652); model twins `backend/open_webui/models/knowledge.py` (:709–762); bulk twin `reindex_knowledge_files` (:332–408).
**Signature:** `POST /knowledge/{id}/file/add | /file/update | /file/remove` with `KnowledgeFileIdForm {file_id: str, directory_id?: str}` and `delete_file: bool = Query(True)` on remove.
**Data Shape:** shared prelude = knowledge exists ∧ ¬external ∧ (owner ∨ `AccessGrants.has_access('knowledge', id, 'write')` ∨ admin) else 400 ACCESS_PROHIBITED; responses are `KnowledgeFilesResponse(**knowledge, files=get_file_metadatas_by_id)` + a typed publish_event.

### Decisive source
```python
# KB write-access alone is not enough — caller must also be able to read the file.
if file.user_id != user.id and user.role != 'admin':
    if not await has_access_to_file(file.id, 'read', user, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
...
    await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=knowledge.id, filter={'file_id': form_data.file_id})
    # Remove by file_id first
    await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=knowledge.id, filter={'hash': file.hash})
    # Remove by hash as well in case of duplicates
```

**Flow (add):** dual gate — KB-write prelude PLUS a separate file-read check with the comment above (`:1415–1421`) plus FILE_NOT_PROCESSED when `file.data` empty; then ORDER MATTERS: `process_file(collection_name=kb.id)` embeds FIRST, the `KnowledgeFile` binding row is written SECOND (:1433–1439), event last — an embedding failure strands nothing because no binding row exists yet. **Flow (update):** `has_file` membership validated BEFORE mutation; delete-by-file_id from the kb collection; re-run process_file. **Flow (remove):** INVERTED — unbind row first, then dual vector deletes by `file_id` then by `hash` ("in case of duplicates"), each except-pass with the "bypassing embedding processing" comment; the DESTRUCTIVE arm (delete `file-{id}` collection + `Files.delete_file_by_id`) fires only when `delete_file` AND FILE ownership (`file.user_id == user or admin`, :1620–1633) — a KB-writer can unbind but not destroy someone else's file. Bulk twin: admin-only reindex deletes each kb collection skip-don't-raise, re-processes every file capturing per-file failures into `failed_files`, publishes KNOWLEDGE_REINDEXED(subject_id='all'), always returns True.
**Invariant:** add is embed-then-bind; remove is unbind-then-purge; destructive cleanup requires ownership of the FILE, not just write on the collection.
**Probe:** `grep -n "KB write-access alone is not enough" backend/open_webui/routers/knowledge.py` → 1415; `grep -n "Remove by hash as well in case of duplicates" backend/open_webui/routers/knowledge.py` → 1614.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", name_pattern: "(add_file_to_knowledge|update_file_from_knowledge|remove_file_from_knowledge).*", limit: 20 });
```
(resolves all five nodes at the cited ranges.)

## Verdict
Adopt: the ordering algebra and the dual-gate pattern (collection permission ≠ permission to read members); ownership-gated destructive cleanup; per-file failure capture in bulk reindex. Adapt: event names/shape; directory_id placement. Omit: Svelte toast UX. Caveats recorded honestly: the MODEL layer swallows exceptions (add→None :739–740, remove→False) and the ROUTER ignores the add() return — only `process_uploaded_file` checks it; the UI consumer (`KnowledgeBase.svelte addFileHandler` :747–765) is optimistic and rolls back via `fileItems.filter((file) => file.id !== fileId)` on failure. Zero test files at pin; evidence source+graph only.
