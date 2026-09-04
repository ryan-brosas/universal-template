<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Baserow: dynamic user-table schema kernel

## Use this for
Use when building or porting products where end users define database schemas at runtime (Airtable-like grids, no-code data apps): generating one physical table per user table, materializing ORM models on the fly without polluting a global registry, lenient type conversions that never fail on legacy data, shared through-tables for bidirectional relations, cross-process schema-artifact cache invalidation, and consistent exports while other requests run DDL. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./lenient-alter-column-try-cast.md` — per-column try_cast plpgsql function created around every ALTER so uncastable cells become NULL instead of failing the migration.
- `./safe-schema-editor-composition.md` — composed subclass swap onto the connection fixing Django's deferred-SQL atomic bug plus one-shot m2m through-table create/delete.
- `./dynamic-model-generation.md` — `Table._get_model` builds `Table{id}Model` via `type()` with unique app_label and an apps-proxy that diverts generated models from the global registry.
- `./model-cache-creation-counter.md` — restoring field attrs from Redis requires bumping Django's global field creation_counter or fields compare equal and vanish from SELECTs.
- `./version-uuid-invalidation.md` — invalidation = new UUID on the Table row; other processes' cached attrs fail the version check lazily; request-local keys die by prefix sweep.
- `./link-row-twin-m2m.md` — link fields return None from get_model_field then attach ManyToManyFields in after_model_generation, sharing one physical through table; recursion dies via the shared manytomany_models dict.
- `./serial-relation-id-allocation.md` — DB-sequence-backed `link_row_relation_id` gives both twin fields the same through table without allocation races.
- `./related-field-twin-lifecycle.md` — exact hooks (before_create/after_create/before_schema_change/after_update/after_delete) that create, move-between-tables, or delete the mirror link field.
- `./fieldtype-prepare-hooks.md` — the optional SQL fragment pair (`p_in` reshaping) each field type contributes to the try_cast body, incl. parameterized tuple form.
- `./update-field-pipeline.md` — the full update_field ordering: deepcopy snapshot → polymorphic flip → save-before-DDL → converter-or-lenient alter → after_update dependency walk.
- `./mvcc-safe-read-transactions.md` — REPEATABLE READ + first-statement FOR KEY SHARE metadata locks so exports never see ALTER-broken snapshots.
- `./system-column-ladder.md` — order/created_by/last_modified_by/background-update columns gated by per-table boolean latches encoding deployment-order truth.
- `./trashed-field-inclusion.md` — trashed columns stay on the generated model (via objects_and_trash manager) so INSERTs never violate NOT NULL on hidden columns.
- `./m2m-index-backfill.md` — idempotent check-then-create FK indexes on through tables because add_field, unlike create_model, doesn't build them.

## Capsule map
- **DDL safety plane** — `lenient-alter-column-try-cast`: ALTER ... USING `{col}_try_cast(col::text)` with exception→NULL body; drop-create-drop lifecycle per alter; `_forced` suffix fakes type drift. `safe-schema-editor-composition`: global SchemaEditorClass swap guarded by issubclass check, own outer atomic because Django's `__exit__` leaks savepoints when DEFERRED sql raises, m2m through-name sets prevent double create/delete of self-referencing link tables. `mvcc-safe-read-transactions`: lock field+table rows FOR KEY SHARE as statement #1; RR variants take the snapshot there.
- **Runtime model plane** — `dynamic-model-generation`: uuid app_label per call (thread-safe pending ops), GeneratedModelAppsProxy.get_models must return static+generated, do_all_pending_operations capped at 3 iterations, residual all_models key deleted. `model-cache-creation-counter`: cache hit ⇒ advance `DjangoModelFieldClass.creation_counter` past every restored value BEFORE adding synthetic `order`; collision symptom is per-cell re-querying. `system-column-ladder`: latches (`created_by_column_added` etc.) gate conditional attrs; system FKs are db_constraint=False/DO_NOTHING. `trashed-field-inclusion`: trashed attrs included or `objects.create()` NULLs hidden NOT NULL columns; duplicate names renamed `{name}_{db_column}`.
- **Cache coherence plane** — `version-uuid-invalidation`: signal + local prefix-sweep + row-version UUID update (never delete Redis keys); Field.save always invalidates; BASEROW_DISABLE_MODEL_CACHE short-circuits writes.
- **Relation kernel** — `link-row-twin-m2m`: None-placeholder + contribute_to_class after class creation; reverse name discovered by scanning `_field_objects` else `reversed_field_{id}`; self-referencing links reuse the same model and forbid related fields. `serial-relation-id-allocation`: `nextval()` pre_save on SerialField (sequence created by migration 0071), threaded verbatim to twin creation. `related-field-twin-lifecycle`: has_related_field defaults to not-self-referencing; retarget MOVES the twin (name/order/table) and re-points stale instances; single-sided delete uses DELETE_OBJECT strategy. `m2m-index-backfill`: add_field override ensures both through-FK indexes exist, check-then-create idempotent.
- **Conversion engine** — `fieldtype-prepare-hooks`: old/new `p_in` fragments spliced into try_cast; tuple form binds variables; same-basetype changes skip ALTER unless forced. `update-field-pipeline`: two bracket models (from_model/to_model) built around the edit; metadata saved before DDL; `altered_column` decided by db_parameters type-string comparison.

## Extending the foundation
Add one source-confirmed capsule: loader line, map entry, decisive source, invariant, direct-test probe, and `search_graph` retrieval against `ext-baserow`. Keep evidence in the capsule, not this leaf.

## Provenance
Baserow (MIT with EE/premium dirs excluded from mining), `develop@d1db1705846ba71ef6054b023d8a1bb81ce59142` (= base_sha = live HEAD, zero drift); Codebase Memory project `ext-baserow` (ready FULL 171,574n/560,476e, root $REFERENCE_ROOT/external/baserow, no stale twin). Coverage: check_index_coverage stdin-JSON ×12 cited paths all `no_recorded_issue`. parse_partial ×159 repo-wide = SCSS/env/config files only — none cited. Pass 1 mined the dynamic-schema kernel whole-file: db/{schema,atomic,sql_queries}.py, table/{models,cache}.py, core/cache.py, fields/{models,registries,fields,handler}.py + LinkRow/MultiSelect/Collaborators regions of field_types.py; direct tests read: test_db_schema.py (4), test_table_cache.py (8), test_table_models.py::test_model_coming_out_of_cache_queries_correctly, test_link_row_field_type.py (:1701/:1722/:1572).

## Full view (memory graph)
Revalidate `ext-baserow` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: try_cast lifecycle, editor composition + atomic fix, dynamic-model generation hygiene, counter-bump cache restore, version-UUID invalidation, twin-field choreography, sequence-allocated relation ids, lock-first snapshot reads. Adapt host-specific integration: Django signals/managers, cachalot, Redis django-cache backend, polymorphic content types, Postgres dialect specifics. Omit product behavior: views/filters/aggregation UI planes, webhooks, enterprise SSO/RBAC, formula engine internals (pass-2 targets below), frontend Vue modules.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`dynamic-model-generation.md`](./dynamic-model-generation.md)
- [`fieldtype-prepare-hooks.md`](./fieldtype-prepare-hooks.md)
- [`lenient-alter-column-try-cast.md`](./lenient-alter-column-try-cast.md)
- [`link-row-twin-m2m.md`](./link-row-twin-m2m.md)
- [`m2m-index-backfill.md`](./m2m-index-backfill.md)
- [`model-cache-creation-counter.md`](./model-cache-creation-counter.md)
- [`mvcc-safe-read-transactions.md`](./mvcc-safe-read-transactions.md)
- [`related-field-twin-lifecycle.md`](./related-field-twin-lifecycle.md)
- [`safe-schema-editor-composition.md`](./safe-schema-editor-composition.md)
- [`serial-relation-id-allocation.md`](./serial-relation-id-allocation.md)
- [`system-column-ladder.md`](./system-column-ladder.md)
- [`trashed-field-inclusion.md`](./trashed-field-inclusion.md)
- [`update-field-pipeline.md`](./update-field-pipeline.md)
- [`version-uuid-invalidation.md`](./version-uuid-invalidation.md)
