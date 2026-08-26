<!-- capsule-v2 -->
# cache_strings plane — where does string interning get configured, and which producers opt OUT?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** A porter adding a PyString-interning optimization must know its full config→consumer chain and where caching is deliberately suppressed.

## Config read once at build, copied into per-call Extra, consumed only through `new_py_string` (All-mode gate); URL parsing hardcodes None
**Path/Symbol:** `src/validators/mod.rs:155-157` (config read) + `SchemaValidator.cache_str` (:121) + `Extra.cache_str` (:689/:705); `src/validators/validation_state.rs:ValidationState::cache_str/maybe_cached_str` (:131-137); `src/tools.rs:new_py_string` (:142-149).
**Signature:** `fn new_py_string<'py>(py: Python<'py>, s: &str, cache_str: StringCacheMode) -> Bound<'py, PyString>`.
**Data Shape:** jiter `StringCacheMode::{All, Keys, None}`; CoreConfig key `cache_strings` accepts True/False/'keys'; default All; repr maps All/Keys/None → "cache_strings=True"/"'keys'"/"False" (mod.rs:400-407).

### Decisive source
```rust
// tools.rs — the ONLY pydantic-core-side consumer gate
pub(crate) fn new_py_string<'py>(py: Python<'py>, s: &str, cache_str: StringCacheMode) -> Bound<'py, PyString> {
    // we could use `bytecount::num_chars(s.as_bytes()) == s.len()` as orjson does, but it doesn't appear to be faster
    if matches!(cache_str, StringCacheMode::All) {
        cached_py_string(py, s)
    } else {
        PyString::new(py, s)
    }
}
```

**Flow:** `config.get_as("cache_strings")? .unwrap_or(StringCacheMode::All)` runs ONCE in SchemaValidator::new and is stored on the validator; each call copies it into Extra so ValidationState exposes `cache_str()` (JSON-plane consumers pass it to jiter, e.g. `JsonValue::as_py_string(cache_str)` return_enums.rs:484) and `maybe_cached_str` (transformed strings, string.rs:163-167 lower/upper/passthrough). `Keys` mode is honored inside JITER's parser only — core's own `new_py_string` treats it like None. Deliberate opt-out: url.rs hardcodes `StringCacheMode::None` at both parse sites (:91,:320) because URLs are high-cardinality. The standalone `from_json` function exposes `cache_strings=` kwarg defaulting All (lib.rs:46-61).
**Invariant:** caching decision is per-VALIDATOR (build-time), not per-call — a port making it a per-call knob breaks the documented repr contract and the tests that pin it. Interning shares one PyString object across validation outputs; any host with per-request isolation semantics must treat cached strings as immutable/global.
**Probe:** direct probe Q6 executed live @ pin byte-matching tests/test_config.py::test_cache_strings (:140-151): plain_repr of default validator contains 'cache_strings=True'; CoreConfig(cache_strings=False) → 'cache_strings=False'; CoreConfig(cache_strings='keys') → "cache_strings='keys'".
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "cache_str string cache mode maybe_cached_str config", limit: 10 });
// live run this pass: rank-1 = ValidationState.cache_str (validation_state.rs:131-133); maybe_cached_str :135-137, mod.rs field/config-read sites, and test_config.test_cache_strings all surface in the top band
```

## Verdict
Adopt build-time config + single choke-point helper pattern; adapt the intern table to your runtime's string pool (jiter `cached_py_string` here); omit Keys-mode emulation outside your JSON parser unless you port jiter's key-cache too. Caveat: jiter internals are not vendored in this repo — Keys-mode parser behavior is described from call-site evidence only. Coverage: tools.rs, validation_state.rs, mod.rs, test_config.py no_recorded_issue @ gen 2026-08-25T20:09:30Z.
