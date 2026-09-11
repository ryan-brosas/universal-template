<!-- capsule-v2 -->
# Principal resolution ladder — how do four permission principal kinds (USER/GROUP/ROLE/ORG) become graph edges without ever inventing an identity?

**Source:** PipesHub AI Apache-2.0 `main@c28d133602543bd737b9791db84b76c5dee84ff7`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** A vendor permission blob says "user X", "group Y", "role Z", or "the org" — what is the exact lookup chain per kind, and what must happen when the referenced principal does not exist locally yet?

## Resolve-or-drop per entity type; ORG is the only synthetic source
**Path/Symbol:** `backend/python/app/connectors/core/base/data_processor/data_source_entities_processor.py:` `on_new_record_groups` principal loop (:1736–1801); shared edge factory `backend/python/app/models/permission.py:` `Permission.to_arango_permission` (:34–62); enum trap :9–14.
**Signature:** input `permissions: list[Permission]` where `Permission = {external_id?, email?, type: PermissionType, entity_type: EntityType}`; output generic edge dicts appended only when BOTH `from_id` and `from_collection` resolved.
**Data Shape:** Resolution table — USER: `get_user_by_email(permission.email)` → USERS; GROUP: `get_user_group_by_external_id(connector_id, permission.external_id)` → GROUPS; ROLE: `get_app_role_by_external_id(connector_id, permission.external_id)` → ROLES; ORG: no lookup, `from_id = self.org_id` → ORGS.

### Decisive source
```python
if permission.entity_type == EntityType.USER:
    user = await tx_store.get_user_by_email(permission.email) if permission.email else None
    if user: from_id, from_collection = user.id, CollectionNames.USERS.value
    else: self.logger.warning(f"Could not find user with email {permission.email} for RecordGroup permission.")
elif permission.entity_type == EntityType.GROUP: ...   # external pair lookup, warn on miss
elif permission.entity_type == EntityType.ROLE:  ...   # external pair lookup, warn on miss
# (The ORG case is no longer needed here as it's handled by BELONGS_TO)
elif permission.entity_type == EntityType.ORG:
    from_id, from_collection = self.org_id, CollectionNames.ORGS.value
if from_id and from_collection:
    record_group_permissions.append(
        permission.to_arango_permission(from_id, from_collection, to_id, to_collection))
```
```python
class PermissionType(str, Enum):
    READ = "READER"      # member NAME != stored VALUE — PermissionType.READ.value == "READER",
    WRITE = "WRITER"     # so hierarchy tables and raw edges key on the VALUE string, never the name
```
**Flow:** dispatch on entity_type → resolve via the table (email for users, `(connector_id, external_id)` pairs for groups/roles) → unresolved ⇒ warning + that principal contributes NO edge (loop continues) → resolved ⇒ append generic edge dict carrying `role=type.value`, `type=entity_type.value` → one batched create.
**Invariant:** (1) unknown principals are DROPPED-WITH-WARNING, never guessed — a fabricated id would grant access to a nonexistent node that a later real node could inherit; (2) ORG is the ONLY principal allowed to exist by fiat (it IS the processor's tenant scope); (3) all four lookups happen INSIDE the caller's transaction so a group/role created earlier in the same sync is visible; (4) enum member names differ from values (`READ`≠`"READER"`) — every persisted comparison uses `.value`.
**Probe:** `grep -c 'get_user_by_email' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `11`; `grep -c 'PermissionType.READ' app/models/permission.py` → `0` (values live in the Enum block :10–14, not as attribute literals); suite tests: `test_role_permission_with_known_role` :270, `test_role_permission_unknown_role_skipped` :296, `test_group_permission_no_external_id` :336 — green in executed battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "to_arango_permission EntityType USER get_user_by_email RecordGroup", limit: 10 });
```

## Verdict
Adopt resolve-or-drop with the email/pair lookup split and the single synthetic-ORG exception; adapt the principal kinds and id fields to your directory; omit Arango's edge-doc field names in favor of your schema (keep role+type carried ON the edge). Coverage caveat: none — coverage clean, tests green at pin.
