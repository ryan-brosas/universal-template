<!-- capsule-v2 -->
# Record-group topology edges — how do folders get their org/app/parent/permission edges, and when is an INHERIT_PERMISSIONS edge created versus deleted?

**Source:** PipesHub AI Apache-2.0 `main@c28d133602543bd737b9791db84b76c5dee84ff7`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Record groups (folders/drives) form a hierarchy that permissions flow through — what exactly decides between BELONGS_TO(org), BELONGS_TO(app), BELONGS_TO(parent), and INHERIT_PERMISSIONS, and who synthesizes missing parents?

## Four-edge decision ladder with placeholder parents and inherit toggles
**Path/Symbol:** `backend/python/app/connectors/core/base/data_processor/data_source_entities_processor.py:` `on_new_record_groups` (:1615–1808); rename `update_record_group_name` (:1811–1838).
**Signature:** `async def on_new_record_groups(self, record_groups: list[tuple[RecordGroup, list[Permission]]]) -> None` (`@retry_on_deadlock()`); `async def update_record_group_name(self, folder_id: str, new_name: str, old_name: str = None, connector_id: str = None) -> None`.
**Data Shape:** RecordGroup carries `external_group_id`, optional `parent_record_group_id` / `parent_external_group_id`, `inherit_permissions: bool`, `group_type`, `connector_id` (INSTANCE id — doubles as the APPS node id). Permission principals resolve USER→email, GROUP→external pair, ROLE→external pair, ORG→self.org_id.

### Decisive source
```python
# app edge ONLY for top-level groups with no parent edge already present
if record_group.connector_id and record_group.parent_record_group_id is None \
   and record_group.parent_external_group_id is None:
    belongs_to_edges = await tx_store.get_edges_from_node(
        record_group_node_id, CollectionNames.BELONGS_TO.value)
    has_parent_record_group_edge = any(
        (e.get("_to") or "").startswith(f"{CollectionNames.RECORD_GROUPS.value}/")
        for e in belongs_to_edges)
    if not has_parent_record_group_edge:
        ...  # create record-group → APPS BELONGS_TO

if parent_record_group:
    await tx_store.batch_create_edges([parent_relation], collection=CollectionNames.BELONGS_TO.value)
    if record_group.inherit_permissions:
        inherit_relation = parent_relation.copy()
        inherit_relation.pop("entityType", None)          # SAME geometry, no entityType tag
        await tx_store.batch_create_edges([inherit_relation],
                                          collection=CollectionNames.INHERIT_PERMISSIONS.value)
#if inherit records is false we need to remove the edge aswell   ← handled by the dedicated toggle handler
```
**Flow:** per group: adopt-or-create identity (same external-id rule as user groups; NEW groups mint a fresh uuid here) → upsert doc → BELONGS_TO→org always → BELONGS_TO→app only when top-level AND no existing parent edge (re-reads the graph instead of trusting the payload) → unknown `parent_external_group_id` ⇒ synthesize a PLACEHOLDER parent RecordGroup and link to it → child→parent BELONGS_TO (+ twin INHERIT_PERMISSIONS edge iff `inherit_permissions`) → principal PERMISSION edges via the USER/GROUP/ROLE/ORG resolution ladder → optional `create_record_groups_relation` when internal parent id present.
**Invariant:** (1) app-edge eligibility is decided by OBSERVED graph state (any `_to` under RECORD_GROUPS), not the payload — re-parented folders never gain a spurious second root edge; (2) INHERIT_PERMISSIONS duplicates the parent edge's exact from/to geometry minus `entityType`; permission inheritance is therefore a separate traversable relation a query can follow or ignore; (3) missing parents are synthesized as placeholders so hierarchy depth survives partial vendor scopes; (4) rename is lookup-gated (warn+return on miss) and only touches name/updated_at — edges are id-stable and unaffected.
**Probe:** `grep -c 'INHERIT_PERMISSIONS' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `4`; suite `tests/unit/connectors/core/test_data_source_entities_processor.py`: `test_creates_app_edge_when_no_parent` :362, `test_creates_inherit_permissions_edge` :446, `test_parent_not_found_creates_placeholder_parent` :480, plus toggle handlers `test_inherit_permissions_false_deletes_edge` :1878 and `test_migrates_and_deletes_group` :2086 — green in executed battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "on_new_record_groups INHERIT_PERMISSIONS parent_external_group_id", limit: 10 });
```

## Verdict
Adopt the four-edge ladder (org always, app only at observed roots, parent+inherit twins, placeholder synthesis); adapt collection names and whether your store models inheritance as separate edges or expansion; omit KB-specific entityType tagging. Coverage caveat: none — coverage clean, tests green at pin.
