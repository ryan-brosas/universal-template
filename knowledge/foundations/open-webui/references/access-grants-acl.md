<!-- capsule-v2 -->
# Access-grants ACL plane — how do you replace a per-model JSON ACL column with a relational grant table without changing who can see or edit what?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When migrating resource authorization from an `access_control` JSON blob on each row to shared grant rows, how do reads, list filters, writes, and the boot backfill preserve the old semantics?

## Point check: limit(1) existence over three principal arms
**Path/Symbol:** `backend/open_webui/models/access_grants.py:AccessGrantsTable.has_access` (562-620).
**Signature:** `async def has_access(self, user_id: str, resource_type: str, resource_id: str, permission: str = 'read', user_group_ids: Optional[set[str]] = None, db: Optional[AsyncSession] = None) -> bool`.
**Data Shape:** Grant row = `(resource_type, resource_id, principal_type ∈ {user, group, anyone}, principal_id, permission ∈ {read, write})`. Public wildcard is `principal_type='user', principal_id='*'`; owner access is implicit (never stored).

### Decisive source
```python
result = await db.execute(
    select(AccessGrant)
    .filter(
        AccessGrant.resource_type == resource_type,
        AccessGrant.resource_id == resource_id,
        AccessGrant.permission == permission,
        or_(*conditions),  # public user:* ∨ direct user ∨ member groups
    )
    .limit(1)
)
grant = result.scalars().first()
return grant is not None
```
(access_grants.py 603-613)

**Flow:** build principal conditions → resolve `user_group_ids` lazily via `Groups.get_groups_by_member_id` only when the caller passed `None` → single `SELECT ... WHERE permission == requested OR(arms) LIMIT 1` → existence boolean.
**Invariant:** exact permission match — holding `read` never implies `write`, and vice versa. There is no owner row; ownership checks live at call sites (`has_permission_filter` adds `DocumentModel.user_id == user_id` as its own arm).
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "return grant is not None" backend/open_webui/models/access_grants.py` → 620; `grep -n "principal_id.in_(user_group_ids)" backend/open_webui/models/access_grants.py` → 605 (the point-check group arm; the `in_(group_ids)` spelling belongs to the filter methods at 776/812/875/909).

## List filter: the same algebra compiled to SQL
**Path/Symbol:** `access_grants.py:AccessGrantsTable.has_permission_filter` (723-830).
**Signature:** `def has_permission_filter(self, db, query, DocumentModel, filter: dict, resource_type: str, permission: str = 'read')` — synchronous expression builder; caller awaits execution.
**Data Shape:** `filter = {'user_id': str|None, 'group_ids': [str]}`; `permission='read_only'` delegates to `_has_read_only_permission_filter`.

### Decisive source
```python
grant_exists = (
    select(AccessGrant.id)
    .where(
        AccessGrant.resource_type == resource_type,
        AccessGrant.resource_id == DocumentModel.id,
        AccessGrant.permission == permission,
        or_(public_arm, direct_user_arm_if_any, group_arm_if_any),
    )
    .correlate(DocumentModel)
    .exists()
)
owner_or_grant = [grant_exists]
if user_id:
    owner_or_grant.append(DocumentModel.user_id == user_id)
query = query.filter(or_(*owner_or_grant))
```
(access_grants.py 787-829, condensed)

**Flow:** if neither `user_id` nor `group_ids` present, return the query unfiltered (caller opted out of ACL scoping); else compile a correlated `EXISTS` subquery plus the explicit owner arm so multiple matching grants cannot duplicate rows.
**Invariant:** the point-check (`has_access`) and the list filter must agree per row; the EXISTS shape exists precisely so `JOIN` fan-out can't duplicate listed resources.

## Write bridge and input normalization
**Path/Symbol:** `access_grants.py:set_access_control` (405-441) + `normalize_access_grants` (150-188).
**Signature:** `async def set_access_control(self, resource_type, resource_id, access_control: Optional[dict], db=None) -> list[AccessGrantModel]`; `def normalize_access_grants(access_grants: Optional[list]) -> list[dict]`.
**Data Shape:** legacy JSON `{'read': {'user_ids': [], 'group_ids': []}, 'write': {...}}` ↔ grant dicts `{id, principal_type, principal_id, permission}`.

### Decisive source
```python
if principal_type not in (PRINCIPAL_TYPE_USER, PRINCIPAL_TYPE_GROUP, PRINCIPAL_TYPE_ANYONE):
    continue
if permission not in ('read', 'write'):
    continue
...
if principal_type == PRINCIPAL_TYPE_ANYONE and (principal_id != WILDCARD_PRINCIPAL_ID or permission != 'read'):
    continue

key = (principal_type, principal_id, permission)
deduped[key] = {...}
```
(access_grants.py 160-186, condensed)

**Flow:** `set_access_control` deletes all grants for `(resource_type, resource_id)` then inserts the converted set in one commit — full replacement, not a diff. `normalize_access_grants` drops invalid entries silently and dedupes by `(principal_type, principal_id, permission)`, minting uuid ids when absent.
**Invariant:** `anyone` grants are structurally capped at `('anyone', '*', 'read')` — no-auth visibility can never become writable, no matter what the API form sends.

## Boot migration backfill
**Path/Symbol:** `backend/open_webui/migrations/versions/f1e2d3c4b5a6_add_access_grant_table.py:upgrade` (28-223).
**Data Shape:** seven resource tables `(knowledge, prompt, tool, model, note, channel, file)` carry legacy `access_control` columns before this revision.

### Decisive source
```python
if is_null:
    # Files: NULL = private (no entry needed, owner has implicit access)
    # Other resources: NULL = public (insert user:* for read)
    if resource_type == 'file':
        continue  # Private - no entry needed

    key = (resource_type, resource_id, 'user', '*', 'read')
    ...
# Handle {} = private/owner-only - NO entries needed
```
(f1e2d3c4b5a6_add_access_grant_table.py 108-147, condensed)

**Flow:** create `access_grant` with unique constraint `uq_access_grant_grant` (line 48) + two indexes → inspect each table fresh (`insp.clear_cache()` after table-rebuilding migrations) → per-row: NULL/JSON-null means PUBLIC read (`user:*`) for every type EXCEPT `file` where NULL = PRIVATE; `{}` or empty read/write lists mean private (no rows); otherwise explode read/write user/group ids into grant rows → drop every `access_control` column afterwards via `batch_alter_table`.
**Invariant:** best-effort inserts swallow per-row exceptions (`except Exception: pass`) and dedupe through a process-local `inserted` set — the migration prefers partial success over failing the whole upgrade, and the unique constraint makes re-runs idempotent-ish at the DB level.
**Probe:** `grep -n "uq_access_grant_grant" backend/open_webui/migrations/versions/f1e2d3c4b5a6_add_access_grant_table.py` → 48; `grep -n "resource_type == 'file'" backend/open_webui/migrations/versions/f1e2d3c4b5a6_add_access_grant_table.py` → 110; `grep -n "batch.drop_column('access_control')" backend/open_webui/migrations/versions/f1e2d3c4b5a6_add_access_grant_table.py` → 223.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "access grant permission check has_access principal", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the grant algebra: three-arm existence check with exact-permission matching, correlated-EXISTS list filters with an explicit owner arm, delete-all-then-insert replacement writes, silent-invalidating normalization that caps anonymous grants at read-only. Adapt the SQLAlchemy models/session plumbing and the lazy group resolution to your host. Omit open-webui's seven-table migration specifics beyond the NULL-semantics lesson: decide explicitly whether NULL meant public or private per resource type before backfilling — open-webui itself had to special-case files. Coverage caveat: all cited paths are graph-clean (`no_recorded_issue`, metadata_match) but have no upstream tests; claims pinned by direct source reads at the lines cited above.
