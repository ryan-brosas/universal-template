<!-- capsule-v2 -->
# Completion resolution ladder — how do argument completers get discovered through optional wrappers, and what shape caps the result?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Given schemas that may wrap fields in optional/completable layers, how does `completion/complete` find the right completer and produce a spec-legal CompleteResult?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/mcp.ts`: `handlePromptCompletion` (:370-397), `handleResourceCompletion` (:399-421), `createCompletionResult` (:1488-1497), `EMPTY_COMPLETION_RESULT` (:1499-1504), zod-shape introspection helpers `getSchemaShape`/`isOptionalSchema`/`unwrapOptionalSchema` (:1506-1528); capability auto-enable at registration (:723-728 templates, :788-800 prompts).
**Signature:** `completer(value: string, context?: {arguments?}) => string[] | Promise<string[]>`; `createCompletionResult(suggestions): {completion:{values,total,hasMore}}`.
**Data Shape:** `values = suggestions.map(String).slice(0, 100)`; `total = suggestions.length` (UNCAPPED count); `hasMore = suggestions.length > 100`.

### Decisive source
```ts
const field = unwrapOptionalSchema(promptShape?.[request.params.argument.name]);
if (!isCompletable(field)) return EMPTY_COMPLETION_RESULT;
const completer = getCompleter(field);
if (!completer) return EMPTY_COMPLETION_RESULT;
const suggestions = await completer(request.params.argument.value, request.params.context);
return createCompletionResult(suggestions);
```
```ts
function createCompletionResult(suggestions: readonly unknown[]): CompleteResult {
    const values = suggestions.map(String).slice(0, 100);
    return { completion: { values, total: suggestions.length, hasMore: suggestions.length > 100 } };
}
```

**Flow:** ref/prompt → prompt lookup (not-found/disabled throw InvalidParams) → no argsSchema ⇒ empty → field lookup with OPTIONAL unwrap (zod v4 `.def.innerType`) → completer via `getCompleter` (`isCompletable` marker from `./completable`) → run + cap. ref/resource → template matched by `uriTemplate.toString() === ref.uri` — a FIXED registered URI returns empty completion WITHOUT error (spec-legal oddity, comment admits it "probably should be" an error) → template's `completeCallback(variable)`.

**Invariant:** `total` is the TRUE suggestion count even when `values` is sliced to 100 — `hasMore` is derived from the uncapped length, never from the slice. Registration auto-enables the completions CAPABILITY when any template variable has a completer or any prompt arg is Completable — callers never declare it by hand. Missing completers degrade to the shared EMPTY constant (never thrown).

**Probe:** `test/e2e/scenarios/completion.test.ts` :246-252 (small-set values/total/hasMore), :253+ ("no-such-arg" ⇒ empty values); `packages/server/test/server/completable.test.ts` (marker/wrapper semantics).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "handlePromptCompletion createCompletionResult unwrapOptionalSchema getCompleter", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt uncapped-total/capped-values pairing + wrapper-unwrapping completer lookup + capability-auto-enable on registration; adapt the zod-introspection duck-typing; omit MCP ref vocabulary.
