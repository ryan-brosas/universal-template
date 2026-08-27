<!-- capsule-v2 -->
# Transitive file access resolver — how do you answer "can this user read/write this file?" when access arrives via collections, channels, chats, or models?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** How do you resolve file permission through every object that can contain the file, without letting read access launder into write/delete?

## Five-arm ACL resolver
**Path/Symbol:** `backend/open_webui/utils/access_control/files.py:has_access_to_file` (:19–118; graph fan-in 17).
**Signature:** `async def has_access_to_file(file_id: str | None, access_type: str, user: UserModel, db: AsyncSession | None = None, user_group_ids: set[str] | None = None) -> bool`
**Data Shape:** access_type ∈ {'read','write'}; optional precomputed `user_group_ids` set threads ONE group-membership fetch across arms and folder entries.

### Decisive source
```python
    # Check if the file is associated with any knowledge bases the user has access to.
    # An object (knowledge base or workspace model) confers write/delete on a file only when
    # the object's OWNER owns that file; otherwise a read-only file laundered into an object
    # the user controls would gain write/delete on it (CWE-863). Read access is unaffected.
    ...
        ) and (access_type == 'read' or knowledge_base.user_id == file.user_id):
            return True
```

**Flow:** (1) missing file ⇒ False; direct ownership short-circuits True (:42–43); (2) KB arm — every knowledge base containing this file grants when user owns/has granted permission on the KB AND the excerpt's owner-match holds for write; (3) shortcut arm — `file.meta.collection_name` names ONE candidate KB fetched directly instead of scanning all accessible KBs (:66–86); (4) channel membership confers READ only (:89–91); (5) shared chats checked as a BATCH via `AccessGrants.get_accessible_resource_ids(resource_type='shared_chat')` (:94–105); (6) workspace models attaching the file in `meta.knowledge` follow the same write-conferment rule (:109–116). Folder helpers reuse the resolver per entry with the shared group set.
**Invariant:** containment NEVER upgrades a read-shared file to writable — write/delete requires the containing object's OWNER to own the FILE (CWE-863 rule, excerpt above); deny is the default return.
**Probe:** `grep -n "read-only file laundered into an object" backend/open_webui/utils/access_control/files.py` → 47; `grep -n "access_type == 'read' or knowledge_base.user_id == file.user_id" backend/open_webui/utils/access_control/files.py` → 63 and 73.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", name_pattern: ".*has_access_to_file.*", limit: 6 });
```
(resolves the single definition :19–118 with fan-in 17 across files/knowledge/chats routers.)

## Verdict
Adopt: the write-conferment ownership rule for ANY containment hierarchy; batched existence checks over per-item loops; single-fetch shortcut when the container id is already known on the resource; group-set threading. Adapt: arm list to your object types. Omit: folder-entry filtering specifics. Honest caveats: docstring says callers should check ownership separately BEFORE calling, yet the body also returns True on direct ownership (:42) — treat ownership handling as included but keep caller-side checks when composing gates; denial at the HTTP layer is 404-shaped in callers (e.g. process/status :663–667), not 403. Zero test files at pin; evidence source+graph only.
