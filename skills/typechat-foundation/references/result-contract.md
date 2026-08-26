<!-- capsule-v2 -->
# Result contract — how do both language ports model success/failure without exceptions?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** What is the exact discriminated-result shape a porter must reproduce so every layer (model → translator → validator) composes without try/catch?

## Result union shared by every layer
**Path/Symbol:** `typescript/src/result.ts:4-45` (`Success<T>`, `Error`, `Result<T>`, `success`, `error`, `getData`) and `python/src/typechat/_internal/result.py:1-21` (`Success`, `Failure`, `Result`).
**Signature:** TS `{ success: true, data: T } | { success: false, message: string }`; Py dataclasses `Success(value: T)` / `Failure(message: str)` with `Result: TypeAlias = Success[T] | Failure`.
**Data Shape:** TS discriminates on the literal field `success`; Python has no discriminator field — callers use `isinstance(result, Success)`. Python `T` is declared covariant (`TypeVar("T", covariant=True)`); TS uses plain generic `T extends object` at translator level but plain `T` here.

### Decisive source
```ts
export type Success<T> = { success: true, data: T };
export type Error = { success: false, message: string };
export type Result<T> = Success<T> | Error;
```
```py
@dataclass
class Success(Generic[T]):
    "An object representing a successful operation with a result of type `T`."
    value: T
```

**Flow:** factories construct leaf objects → `model.complete` returns `Result<string>` → translator propagates Failure verbatim or wraps validated JSON as Success → application calls `getData(result)` which throws only at the boundary.
**Invariant:** Failures are values, never thrown, inside the pipeline; the ONLY throw site is `getData` (TS `result.ts:40-45`) when unwrapping at the edge. Python names the payload field `value` while TS names it `data` — porting either name to the other side silently breaks pattern matches.
**Probe:** `grep -c 'success: true' typescript/src/result.ts` (=2: type + factory); live suite `cd python && python -m pytest tests/test_validator.py -q` pins Success equality (`r == typechat.Success(Example(...))`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typechat", query: "Result success failure getData", limit: 5 });
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"Result success failure","limit":5}'
```

## Verdict
Adopt the two-case result union and value-not-exception propagation wholesale; adapt field naming per host convention (`data` vs `value`) consistently within one port; omit TS `getData` if the host throws at boundaries already. No direct-test caveat: both sides are covered (`tests/test_validator.py`, every example).
