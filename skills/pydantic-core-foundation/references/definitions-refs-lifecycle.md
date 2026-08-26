<!-- capsule-v2 -->
# Definitions & refs — how do recursive schemas build without infinite recursion, and which three errors can fire?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** What is the ref/definition lifecycle contract a port must keep (including the weak-pointer subtlety)?

## Arc<OnceLock<T>> slots filled at most once; refs hold Weak; duplicate/missing/duplicate-fill are distinct errors
**Path/Symbol:** `src/definitions.rs:DefinitionsBuilder/Definitions/DefinitionRef/RecursionSafeCache/LazyName` (whole file, 269L).
**Signature:** `get_definition(&mut self, reference: &str) -> DefinitionRef<T>` (:145); `add_definition(&mut self, reference: String, value: T) -> PyResult<DefinitionRef<T>>` (:165); `finish(self) -> PyResult<Definitions<T>>` (:188).
**Data Shape:** `Definition<T> { value: Arc<OnceLock<T>>, name: Arc<LazyName> }`; `DefinitionRef<T> { reference: Arc<String>, value: Weak<OnceLock<T>>, name: Arc<LazyName> }`. Integer ReferenceIds are mentioned in docs but the map key is the Arc'd string (`AHashMap<Arc<String>, Definition>`).

### Decisive source
```rust
// add_definition — second fill of the same ref:
Err(_) => return py_schema_err!("Duplicate ref: `{}`", reference),
// finish — any slot never filled:
if def.value.get().is_none() {
    return py_schema_err!("Definitions error: definition `{}` was never filled", reference);
}
```

**Flow:** Forward references: builder hands out empty slots via `get_definition` (validators store the Weak-ref `DefinitionRefValidator` and continue building); when the referenced schema is built it calls `add_definition` filling that SAME slot. Weak in the ref breaks A→B→A Arc cycles so SchemaValidator owns the graph. `finish()` fails the whole build if ANY slot is unfilled. Debug formatting of recursive structures terminates because `DefinitionRef::fmt` prints only its LazyName, and LazyName computes through `RecursionSafeCache::get_or_init(init, "...")` which returns the literal `"..."` default when re-entered mid-computation (AtomicBool compare_exchange recursion latch, :225-243).
**Invariant:** One fill per ref ever — even identical duplicate schemas error as "Duplicate ref". Refs upgrade() lazily; after `finish`, all upgrades succeed. The `"..."` recursion-default pattern is reusable anywhere lazy names recurse.
**Probe:** `grep -c 'Duplicate ref' src/definitions.rs` =1 (:172); `grep -c 'was never filled' src/definitions.rs` =1 (:191); direct tests: tests/validators/test_definitions.py + test_definitions_recursive.py green this pass (in 283-passed batch).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "DefinitionsBuilder add_definition never filled", limit: 4 });
// live rank-family: definitions.rs symbols resolve line-exact
```

## Verdict
Adopt: single-slot-once semantics with three distinct failure messages, weak refs from users to break cycles, recursion-safe lazy naming. Adapt OnceLock to your language's atomic-once cell. Omit the integer-id performance note (implementation detail of the hash map).
