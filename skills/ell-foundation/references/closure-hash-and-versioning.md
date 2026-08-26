<!-- capsule-v2 -->
# closure hash and versioning — what exactly is hashed into an LMP version id, and when?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** What identity makes two versions of a prompt-program "the same", and when does the hash get computed under lazy vs eager versioning?

## md5 over formatted source + cleaned deps + qualname
**Path/Symbol:** `src/ell/util/closure.py:_generate_function_hash` (:295-297), `_clean_src` (:395-417), `_update_ell_func` (:299-308); wiring in `src/ell/lmp/_track.py` (:54-60, :157-161) and `serialize_lmp` (:201-257).
**Signature:** `_generate_function_hash(source: str, dsrc: str, qualname: str) -> "lmp-" + md5hex`.
**Data Shape:** `source` = Black-formatted function source; `dsrc` = Black-formatted dependency-only file (function body removed); name munging for lambdas: `<lambda>` → `<lambda@{hash[:6]}>`.

### Decisive source
```python
# closure.py:104-112
dsrc = _clean_src(dirty_src_without_func)

# Format the sorce and dsrc soruce using Black
source = _format_source(source)
dsrc = _format_source(dsrc)

fn_hash = _generate_function_hash(source, dsrc, func.__qualname__)

_update_ell_func(outer_ell_func, source, dsrc, globals_and_frees['globals'], globals_and_frees['frees'], fn_hash, uses)
```

```python
# _track.py:58-59 + 157-161 — the lazy/eager split
if not hasattr(func_to_track, "__ell_hash__") and not config.lazy_versioning:
    func_to_track.__ell_force_closure__()
...
# inside tracked_func, AFTER execution:
if not hasattr(func_to_track, "__ell_hash__") and config.lazy_versioning:
    ell.util.closure.lexically_closured_source(func_to_track, forced_dependencies)
serialize_lmp(func_to_track)
```

**Flow:** hash inputs are normalized first (Black formatting makes whitespace irrelevant; deps file excludes the body so docstring edits DO change hashes but call-site noise does not). Version numbering in `serialize_lmp`: depth-first serialize `__ell_uses__`, then look up versions by FQN; if this exact `lmp_id` exists → skip (idempotent); else `version = max(created_at row).version_number + 1`; autocommit additionally generates an LLM commit message from old-vs-new closure. Lambda naming injects a hash fragment into the stored name so anonymous programs remain addressable.
**Invariant:** hashing is content-addressed over *static text*, never runtime state — state belongs to invocations via state_cache_key; and lazy versioning means a never-called LMP has NO `__ell_hash__` — any code reading it must force closure or handle absence.
**Probe:** `tests/test_closure.py:test_lexical_closure_uses_type` (:108-116) and `test_lexical_closure_signature` (:100-107) pin that signature/type changes flow through closure attrs; store-side idempotence pinned by `tests/test_sql_store.py:test_write_lmp` (:21-78, double-write keeps one row).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "invocation id deterministic hash content", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.util.closure._generate_function_hash @ src/ell/util/closure.py:295-297
```

## Verdict
Adopt content-hash identity over normalized (formatted) source plus a body-free dependency file. Adapt the formatter (Black) to your language's canonical formatter. Omit lambda-name munging only if your store forbids anonymous programs entirely.
