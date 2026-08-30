<!-- capsule-v2 -->
# Conditional upsert update modes — which points of a conditional insert survive, and who decides?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** A conditional upsert carries points plus a filter and an update mode. Against what state is each point kept or dropped, and why must the same decision run at both submit time and apply time?

## Three modes judged against current segment state, shared by apply and resolution
**Path/Symbol:** `lib/shard/src/update/points/upsert.rs`: `retain_conditional_upsert_points` (:60-95), `conditional_upsert` (:97-121); helpers `lib/shard/src/update/helpers.rs`: `select_excluded_by_filter_ids` (:60-73); `lib/shard/src/segment_holder/mod.rs`: `select_existing_points` (:1138); resolution twin `lib/shard/src/resolve.rs`: `resolve_conditional_upsert` (:202-216).
**Signature:** `pub(crate) fn retain_conditional_upsert_points(segments: &SegmentHolder, points_op: &mut PointInsertOperationsInternal, condition: Filter, update_mode: Option<UpdateMode>, hw_counter: &HardwareCounterCell) -> OperationResult<()>`; `pub fn conditional_upsert(segments, op_num, operation: ConditionalInsertOperationInternal, hw_counter) -> OperationResult<usize>`.
**Data Shape:** `ConditionalInsertOperationInternal { points_op, condition: Filter, update_mode: Option<UpdateMode> }`; modes Upsert (default when None), InsertOnly, UpdateOnly. Returns the number of upserted points.

### Decisive source
```rust
// upsert.rs :60-95 — the mode table, judged against CURRENT segment state:
match update_mode {
    UpdateMode::Upsert => {          // default: insert new, update existing that match
        let points_to_exclude = select_excluded_by_filter_ids(segments, point_ids, condition, ...)?;
        points_op.retain_point_ids(|idx| !points_to_exclude.contains(idx));
    }
    UpdateMode::InsertOnly => {      // skip ALL existing points entirely
        let existing_points = segments.select_existing_points(point_ids);
        points_op.retain_point_ids(|idx| !existing_points.contains(idx));
    }
    UpdateMode::UpdateOnly => {      // only existing AND condition-matching
        let points_to_exclude = select_excluded_by_filter_ids(segments, point_ids.clone(), condition, ...)?;
        let existing_points = segments.select_existing_points(point_ids);
        points_op.retain_point_ids(|idx| existing_points.contains(idx) && !points_to_exclude.contains(idx));
    }
}

// helpers.rs :60-73 — "excluded" = in the id set but NOT matching the filter:
let non_match_filter = Filter::new_must_not(Condition::Filter(filter)).with_point_ids(point_ids);
Ok(points_by_filter(segments, &non_match_filter, hw_counter)?.into_iter().collect())

// upsert.rs :113-117 — zero-hit ops must not stall startup recovery:
if upserted_points == 0 {
    segments.bump_max_segment_version_overwrite(op_num);
}
```

**Flow:** a conditional upsert arrives → each point is classified by existence (across all segments) and, for modes that use it, by whether its CURRENT stored data matches the condition → the surviving subset is upserted through the normal two-phase path → if nothing survived, the holder's persisted-version waterline is bumped so the WAL can acknowledge without touching segments. The SAME retention function runs at submit time inside pre-WAL resolution, where the survivor subset becomes a plain `UpsertPoints` record before the WAL append.
**Invariant:** (1) the keep/drop decision reads live segment state, so it must be re-runnable at both submit and apply time from the same function — two implementations would drift; (2) InsertOnly ignores the condition entirely (existence is the whole test); UpdateOnly requires both existence AND match; (3) an all-dropped op still advances the version waterline, or startup replay would re-apply no-op ops forever; (4) because the resolved form is a plain upsert, replay never re-evaluates the condition.
**Probe:** `lib/collection/src/model_testing/apply/writes.rs::apply_upsert_conditional` (:308-345, read at pin): six-case truth table — (Upsert, absent)=apply, (Upsert, present)=apply iff payload matches, (InsertOnly, absent)=apply, (InsertOnly, present)=never, (UpdateOnly, absent)=never, (UpdateOnly, present)=apply iff matches. Companion unit test `lib/shard/src/resolve.rs::resolve_conditional_insert_only_drops_existing_points` (:326-351): resolving an insert-only op over {existing 1, new 100} yields a plain upsert of exactly [100].

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "conditional upsert point condition filter resolve", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-retention-function pattern: one pure "which ids survive" routine parameterized by mode, called from both the apply path and the pre-WAL resolver, with the zero-hit waterline bump as part of the apply contract. Adapt the existence check to your storage's cross-segment id lookup. Omit the deferred-points exclusion corner case (`helpers.rs::deferred_points_to_exclude_by_filter`, :19-58) unless you have multi-copy segments with deferred heads — it exists so an old non-deferred copy matching the filter cannot win over a newer deferred copy that does not.
