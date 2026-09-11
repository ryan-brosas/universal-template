<!-- capsule-v2 -->
# Portable logical-log codec — how do you encode a cross-engine sync transaction payload with deduplicated names, stable object identity, and internal objects provably excluded?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What does the wire format for a portable (externally replayable) logical change-set look like, and which filters decide what is even eligible?

## String-table + object-map builder over the loglog protobuf primitives
**Path/Symbol:** `core/mvcc/portable_logical.rs:1-212` (whole file; feature `conn_raw_api`). Builder :93-212 (`PortableLogicalBuilder`, fields :94-98), string interning `intern_string` :123-131 (`Vec<&str>` order table + `HashMap<&str,u64>` reverse index), object map entries `add_object_map` :133-157, metadata pairs `add_metadata` :159-175, framing `finish` :177-211. Schema-row decode `portable_schema_row_from_record` :43-79; eligibility `is_portable_logical_name` :26-32, `is_portable_schema_row` :85-91, `is_portable_table_schema_row` :81-83. Field constants :10-24: TX_FIELD_STRING_TABLE=12 / OBJECT_MAP=13 / META=14; object entry = mv_table_id=1 + name_ref=2.
**Signature:** `fn add_object_map(&mut self, entry: PortableObjectMapEntry<'a>) -> Result<bool>` — returns `Ok(false)` for non-portable names OR already-seen `mv_table_id`; `fn finish(self) -> Result<Vec<u8>>` — emits string-table first, then object maps, then metadata, each as length-delimited submessages via `LogSerializer`/`log_write!`.
**Data Shape:** strings are INTERNED by first occurrence — every later reference is a varint index into the position-ordered string table (decode = zip in order). Object identity = `mv_table_id` (the MVCC canonical id), name stored once as interned ref.

### Decisive source
```rust
// :134-137 — the double filter that keeps internal machinery out of sync:
if !is_portable_logical_name(entry.name) || self.object_map_ids.contains(&entry.mv_table_id)
{
    return Ok(false);
}
// :26-32 — eligibility vocabulary:
// excludes "sqlite_" prefix, "__turso_internal_" prefix, "turso_sync_" prefix,
// and the exact names turso_cdc / turso_cdc_version.
```
The schema-row decoder is deliberately strict fail-closed: `<5 columns` ⇒ Corrupt; type/name must be Text, rootpage must be Integer, else Corrupt (:46-67) — a truncated or hostile sqlite_schema record must never materialize a portable entry. `is_portable_table_schema_row` additionally requires `rootpage != 0`.

**Flow:** commit path decodes changed sqlite_schema rows → filter through portability predicates → intern names → emit per-object `{mv_table_id, name_ref}` submessages → `finish()` frames [string table | object maps | metadata] as the tx's portable extension block consumed by the LML3 plane (see `logical-log-portable-sync`).
**Invariant:** string-table ORDER is load-bearing (indices are positional); an object's identity travels as its MVCC id, never its name; internal-object writes must be excluded BEFORE encoding so their names never appear in any portable payload.
**Probe:** in-file assertions pin id-stability ("portable object map id changed while building its payload" :152-155); decode-side tests live beside the LML serializer (`logical_log.rs` module tests); integration surface exercised via `portable_delete_op_extension_for_row_version` (`core/mvcc/database/mod.rs:732`) whose outputs flow into `serialize_row_version(..., portable_extension)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "PortableLogicalBuilder intern_string add_object_map is_portable_logical_name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt intern-once/emit-index string tables + id-keyed object maps for any compact change-feed consumed by another engine; adopt the prefix+exact-name exclusion vocabulary as a single predicate so call sites cannot drift. Adapt field numbers/wire primitives to your protobuf dialect (here: the repo's own loglog ProtoVarint/ProtoKey macros). Omit CDC-table special cases unless you also ship change-data-capture tables.
