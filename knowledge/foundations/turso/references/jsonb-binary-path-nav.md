<!-- capsule-v2 -->
# JSONB binary format + path navigation — how are JSON edits applied in place?

**Source:** turso (Limbo) MIT `main@f1800bb8c` (re-anchored from `def9a060`); Codebase Memory project `turso`. **Question:** What is the on-wire JSONB encoding and the path-navigation state that Set/Insert/Replace operations ride on?

## Jsonb container + navigate_path/operate_on_path
**Path/Symbol:** `core/json/jsonb.rs` format constants (:17-22: `SIZE_MARKER_8BIT=12`, `16BIT=13`, `32BIT=14`, `MAX_JSON_DEPTH=1000`, `INFINITY_CHAR_COUNT=5` — value corrected in the pass-14 drift wave from the previously recorded 8), `from_str` (:2508), `navigate_path` (:2590), `operate_on_path` (:2644); ops `SetOperation`/insert/replace with `allows_replace` (:753)/`allows_insert` (:758); path model in `core/json/path.rs`; key-label encoding/decoding rules split out into `json-path-label-escape-duality.md` at pass 15 (`new_key_element_type` :3578, `compare` :3598).
**Signature:** `pub fn navigate_path(&mut self, path: &JsonPath, mode: PathOperationMode) -> Result<Vec<JsonTraversalResult>>`; `pub fn operate_on_path<T: PathOperation>(&mut self, path: &JsonPath, operation: &mut T) -> Result<()>`.
**Data Shape:** binary JSONB blob where element sizes carry size markers 12/13/14 (8/16/32-bit length follow); traversal returns a STACK of `JsonTraversalResult { field_key_index: JsonLocationKind, field_value_index, array_position_info: Option<ArrayPositionKind> }` — one entry per consumed path element.

### Decisive source
```rust
// core/json/jsonb.rs::navigate_path — array-locator lookahead + intermediate Upsert
let next_is_array = matches!(path_iter.peek(), Some(PathElement::ArrayLocator(_)))
    && !matches!(current, PathElement::ArrayLocator(_));
let segment_mode = if is_intermediate_segment {
    PathOperationMode::Upsert        // intermediates auto-create containers
} else {
    mode                             // final segment keeps caller's mode
};
...
pos = match &result.array_position_info {
    Some(ArrayPositionKind::SpecificIndex(idx)) => *idx,
    None => result.field_value_index,
};
```

**Flow:** parse text → JSONB blob (depth-capped at 1000) → operations walk path elements; each step either navigates into an existing key/index or (Upsert mode at INTERMEDIATE segments only) creates the missing object/array shell; the operation object (Set/Insert/Replace/Remove) then executes against the final location and rewrites sizes back through the marker ladder.
**Invariant:** Only intermediate segments get forced Upsert — the LAST segment must honor the caller's mode or `$.a[2] = 5` would create phantom array slots instead of failing/replacing per SQL semantics. Size markers are part of record identity: growing a value rewrites its size prefix chain.
**Probe:** `core/json/jsonb.rs::test_set_operation` (:5435, drift-shifted from :5422 at the pass-14 pin — set "name" to "Jane", output compact `{"name":"Jane","age":30}`); `test_navigate_root_path` (:5308, was :5295 — Root() path yields stack len 1, JsonLocationKind::DocumentRoot); `test_binary_roundtrip` (:5175, was :5162). Text anchors: `grep -c 'SIZE_MARKER_8BIT: u8 = 12' core/json/jsonb.rs` → 1; `grep -c 'MAX_JSON_DEPTH: usize = 1000' core/json/jsonb.rs` → 1. Suite: `cargo test -p turso_core --features json --lib -- json::` → 175 passed, re-executed GREEN at `main@1654d1587` (pass 15).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "navigate_path operate_on_path JsonTraversalResult", limit: 10 });
```

## Verdict
Adopt the marker-ladder binary layout, traversal-stack result shape, and intermediate-Upsert rule. Adapt error taxonomy (`core/json/error.rs`) to host errors. Omit the vtab/cache planes (`json/vtab.rs`, `json/cache.rs`) unless porting JSON functions' cursor plumbing.
