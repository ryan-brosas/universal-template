<!-- capsule-v2 -->
# PyError result railway — how does the shipped API surface replace exceptions with typed errors, and how do error messages accumulate up the call chain?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What is the modern error-return contract of the Python plugin API (`PyResult`/`PyError`/`ErrorSink`) and its message-chaining rule?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/errorProcessing/{PyResult.kt,PyError.kt,MessageError.kt,ExecError.kt,ErrorSink.kt}`. Aliases `PyResult.kt:11` `typealias PyResult<T> = Result<T, PyError>` and `:15 PyExecResult<T>`; helper `failure()` `:17`; chaining op `getOr(actionFailed, onFailure)` `:33-44`. Sealed error root `PyError.kt:19` with `_messages = CopyOnWriteArrayList` `:20` and render `val message get() = _messages.reversed().joinToString("\n")` `:21`. UI sink: `fun interface ErrorSink : FlowCollector<PyErrorDetail>` `ErrorSink.kt:20`, default via application service `:28`.
**Signature:** `fun createUser(): PyResult<User>` + `readFromJson().getOr("failed to read from json file $file") { return it }`.
**Data Shape:** `PyError` sealed class; `MessageError(message)` open subclass (arbitrary user-facing message); `ExecError = ExecErrorImpl<*>` carries `exe: Exe` (sealed `OnEel(EelPath)` / `OnTarget(String)`, `Exe.fromString` try-Eel-fallback-string), `args`, `errorReason: ExecErrorReason`, `asCommand` render.

### Decisive source
```
// PyResult.kt:33-38
inline fun <SUCC, ERR : PyError> Result<SUCC, ERR>.getOr(actionFailed: String, onFailure: (Failure<ERR>) -> Nothing): SUCC {
  when (this) {
    is Result.Failure -> { error.addMessage(actionFailed); onFailure(this) }
    is Result.Success -> return result
  }
}
// PyError.kt doc: "Upper levels will add additional information there."
//   → renders newest-first: _messages.reversed().joinToString("\n")
//   → yields "Can't get pilot: Can't create user: Can't read file."
```

**Flow:** leaf returns `failure(PyError…)` → each level calls `.getOr("<context>")` which APPENDS its own description to the same error object then propagates → topmost UI layer emits through `ErrorSink` (business layers must NOT emit; they return `PyResult`/`PyError`).
**Invariant:** NEVER `catch(Exception)`/`runCatching` a `PyError` (explicit class doc) — errors are values; message order is append-at-level + reversed render, so a porter who prepends instead of appending breaks the readable chain. Legacy bridge exists and is marked migrate-away: `PyExecutionException` wraps `PyError` into `ExecutionException` (`@ApiStatus.Obsolete`, `packaging/PyExecutionException.kt:12`).
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -c 'addMessage' com/jetbrains/python/errorProcessing/PyResult.kt com/jetbrains/python/errorProcessing/PyError.kt` → sums to `2` (1+1);
`grep -n 'reversed().joinToString' com/jetbrains/python/errorProcessing/PyError.kt` → line 21;
`grep -n 'fun interface ErrorSink' com/jetbrains/python/errorProcessing/ErrorSink.kt` → line 20;
`grep -c 'data class On' com/jetbrains/python/errorProcessing/ExecError.kt` → `2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyError ErrorSink FlowCollector addMessage", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: typed-result railway with per-level context append + reversed join; keep UI emission at one sink boundary. Adapt: `Result`/`Either` host type. Omit: Eel path machinery details (platform-specific).
