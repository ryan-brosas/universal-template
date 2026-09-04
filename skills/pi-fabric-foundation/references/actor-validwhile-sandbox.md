<!-- capsule-v2 -->
# validWhile sandboxed predicate — how do you let a config author ship arbitrary activation-conditions code without handing it your host?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** how do you evaluate a user-supplied JS predicate over runtime facts with zero host access, bounded time/memory, and synchronous-only semantics?

## QuickJS guest with frozen facts and deny-all tools
**Path/Symbol:** `src/actors/predicate.ts` whole file (:1-90); QuickJS engine at `src/runtime/quickjs-runtime.ts:execute`.
**Signature:** `validateActorValidWhile(value?): Promise<void>` (create-time syntax probe); `evaluateActorValidWhile(source, facts): Promise<{valid, reason?}>`.
**Data Shape:** `{version: 1, source: string}` ≤16,000 chars; facts envelope `{activation, current:{latestActivationSequence, mainRevision, taskRevision, idle, now}}` serialized into the guest as `π.facts`; return must be `boolean` or `{valid, reason?}`.

### Decisive source
```ts
const execute = async (source, facts?) => {
  const result = await (await runtime()).execute(
    predicateProgram(source.source, facts !== undefined),
    async () => { throw new Error("validWhile cannot call host tools"); },  // deny-all
    { timeoutMs: 100, memoryLimitBytes: 16 * 1024 * 1024,
      maxLogChars: 0,
      strings: { facts: JSON.stringify(facts) } });
  if (result.terminationReason !== "completed") throw new Error(...);
```
Guest wrapper freezes the parsed facts deep (`Object.freeze` walk), invokes the predicate once, and **throws if it returns a thenable** — "validWhile must return synchronously" (:33 of the program string).

**Flow:** create → validate runs the program in "declare only" mode (type-checks it is a function) → per activation, `#validity()` evaluates with fresh facts → non-completed termination (timeout/abort/error) throws → caller converts to `{valid:false}` + `lastError`, records a `stale` silent message, and rejects any blocking ask.
**Invariant:** the sandbox has NO capability surface (host-call callback always throws) and NO async escape; evaluation happens twice per item (pre-run AND pre-delivery) so an activation invalidated mid-run never delivers. A porter who passes raw objects instead of frozen JSON strings lets the predicate retain references into host state.
**Probe:** `tests/actor-valid-while.test.ts:114` ("invalidates a tool-error activation when Main advances before it runs"), :170 ("rejects a blocking ask when its direct activation is invalid"), :187 (latest-activation-wins across event types).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "evaluateActorValidWhile predicate freeze facts", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the frozen-facts + deny-all-tools + sync-only contract whenever untrusted condition code gates automation; adapt the facts schema to your domain; omit the two-phase validate/evaluate split only if you re-validate on every load anyway. Direct tests pin invalidation timing — no coverage caveat.
