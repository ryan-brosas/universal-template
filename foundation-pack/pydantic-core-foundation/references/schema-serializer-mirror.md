<!-- capsule-v2 -->
# SchemaSerializer — how does the serializer mirror the validator, and what state does to_json carry between calls?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** What is the serializer build/entry contract and the per-instance JSON-size heuristic?

## CombinedSerializer tree + Definitions<Arc<CombinedSerializer>>; expected_json_size is a persistent AtomicUsize
**Path/Symbol:** `src/serializers/mod.rs:SchemaSerializer` (:38-198); `to_json`/`to_jsonable_python` free functions (:200-295).
**Signature:** `CombinedSerializer::build_base(schema_dict, config, &mut definitions_builder)`; methods `to_python(value, &mut SerializationState)`, `to_json` via `shared::to_json_bytes(value, &serializer, &mut state, indent, ensure_ascii, expected_size)`.
**Data Shape:** `SchemaSerializer { serializer: Arc<CombinedSerializer>, definitions: Definitions<Arc<CombinedSerializer>>, expected_json_size: AtomicUsize (init 1024), config: SerializationConfig, py_schema, py_config }`.

### Decisive source
```rust
let bytes = to_json_bytes(value, &self.serializer, &mut state, indent,
    ensure_ascii.unwrap_or(false), self.expected_json_size.load(Ordering::Relaxed))?;
state.warnings.final_check(py)?;
self.expected_json_size.store(bytes.len(), Ordering::Relaxed);
```

**Flow:** Build mirrors validators exactly (DefinitionsBuilder of serializers, DefinitionRefSerializer for recursion). Every entry constructs a fresh `SerializationState` (warnings accumulator, include/exclude filter stack, Extra{mode, by_alias, exclude_unset/defaults/none/computed, round_trip, fallback, serialize_as_any, context}) then runs the tree, ending with `warnings.final_check()` BEFORE returning — unexpected-value warnings raise after full serialization. The stored size feeds the writer's initial buffer capacity only (perf heuristic), updated after every to_json call. Free functions (`to_json`) bypass schema trees using `AnySerializer::get()` + inference.
**Invariant:** Warnings never abort mid-tree; they accumulate and fire once. `__reduce__` reconstructs from the ORIGINAL schema+config dicts (both SchemaValidator :393-396 and SchemaSerializer :183-186) — pickling round-trips rebuild rather than serialize compiled trees.
**Probe:** `grep -n 'expected_json_size' src/serializers/mod.rs` =4 hits (:43,:68,:173,:178); direct tests: tests/serializers/test_model.py + test_any.py green this pass (166 passed).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "SchemaSerializer expected_json_size SerializationState", limit: 4 });
// live rank-family: serializers/mod.rs symbols resolve line-exact
```

## Verdict
Adopt: mirrored builder architecture (validators and serializers as sibling trees over shared definitions), state-per-call with terminal warning check, size-hint caching. Adapt buffer heuristic freely. Omit pickle reconstruction if your objects are unpicklable anyway — but keep schema retention for reprs/debugging.
