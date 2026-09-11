<!-- capsule-v2 -->
# LookupKey — how do validation_alias strings/lists address dicts, objects, and JSON uniformly?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** What alias syntax exists and how does lookup behave across the three input planes?

## Simple | Choice{alias,field-name} | PathChoices(dotted/indexed paths); JSON dedups LAST-wins so scans run reversed
**Path/Symbol:** `src/lookup_key.rs:LookupKey/LookupPath` (:18-200+).
**Signature:** `from_py(py, value, alt_alias: Option<&str>)`: string ⇒ Simple(+alt_alias makes Choice); list-of-strings ⇒ ONE path; list-of-lists ⇒ PathChoices.
**Data Shape:** `LookupPath { py_key: Bound<PyString>, first_key: &str, rest: Vec<LocItem> }` — rest items are S(key) or I(index) steps like `['foo', 'bar']`, `('users', 0, 'name')`.

### Decisive source
```rust
Self::Simple(path) => match dict.iter().rev()
        .find_map(|(k, v)| (k == path.first_key()).then_some(v)) { ... }
// FIXME: use of find_map in here probably leads to quadratic complexity  (:161)
```

**Flow:** Four access backends share one shape: `py_get_dict_item` (dict.get), `py_get_mapping_item` (.get() protocol w/ mapping_get returning None-vs-PydanticUndefined), `simple_py_get_attr`/`py_get_attr` (getattr chain, errors→GetAttributeError ValError), `json_get` (jiter JsonObject scan REVERSED — jiter keeps the LAST duplicate key, so scanning backwards finds the surviving entry first). PathChoices tries each full path in order; intermediate steps must all resolve. Error locs reuse LocItem directly (`apply_error_loc` uses the matched path's items honoring loc_by_alias).
**Invariant:** A field's lookup is built once at build time (LookupKeyCollection holds primary+alternates selected by by_alias/by_name at runtime) — never string-mangled per request. Missing key returns Ok(None) (drives the default ladder); only attribute ACCESS failures become errors.
**Probe:** `grep -n 'quadratic complexity' src/lookup_key.rs` =1 (:161); `grep -n 'iter().rev()' src/lookup_key.rs` ≥3; direct tests: tests/validators/test_model_fields.py alias families green this pass.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "LookupKey PathChoices json_get", limit: 4 });
// live rank-family: lookup_key.rs symbols resolve line-exact
```

## Verdict
Adopt: three-form alias grammar, single-shape multi-backend resolution, None-means-absent semantics, last-dup-wins JSON scan direction. Adapt dotted-path parsing to your alias syntax. Omit the quadratic FIXME fix upstream hasn't made (document it instead).
