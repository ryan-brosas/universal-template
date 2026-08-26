<!-- capsule-v2 -->
# Caller runtime affinity — how do I resolve the true caller when the provider registry shares one streamFn across conversations?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** When a host registers one process-wide provider whose stream closure may belong to a different conversation than the caller, how do I recover the caller's identity per request?

## Per-call sessionId → bound InstanceRuntime map
**Path/Symbol:** `src/providers.ts:resolveCallRuntime` (132-143), `bindSessionRuntime` (120-130), `sessionRuntimes`/`MAX_SESSION_RUNTIMES` (117-118).
**Signature:** `function resolveCallRuntime(options: SimpleStreamOptions | undefined, fallback: InstanceRuntime): InstanceRuntime`; `bindSessionRuntime(sessionId: string, runtime: InstanceRuntime): void`.
**Data Shape:** `sessionRuntimes: Map<string, InstanceRuntime>` capped at 256; `InstanceRuntime = { ui: ExtensionUIContext | null; cwd: string; sessionKey: string }`. Stream options carry `options.sessionId` (= host sessionManager id).

### Decisive source
```ts
const sessionId = (options as { sessionId?: unknown } | undefined)?.sessionId;
if (typeof sessionId !== "string" || !sessionId) return fallback;
const bound = sessionRuntimes.get(sessionId);
if (bound) return bound;
// The caller's session never bound (older host, bootstrap session): still
// key the pool by the caller's true conversation id so histories don't merge.
return { ...fallback, sessionKey: sessionId };
```

Bounded map with insertion-order refresh:
```ts
export function bindSessionRuntime(sessionId: string, runtime: InstanceRuntime): void {
  // Re-binding the same id replaces the previous instance's runtime — refresh
  // insertion order so active conversations aren't evicted before idle ones.
  sessionRuntimes.delete(sessionId);
  sessionRuntimes.set(sessionId, runtime);
  while (sessionRuntimes.size > MAX_SESSION_RUNTIMES) {
    const oldest = sessionRuntimes.keys().next().value;
    if (oldest === undefined) break;
    sessionRuntimes.delete(oldest);
  }
}
```

**Flow:** each extension instance binds its runtime under the host session id on `session_start` → at request time `streamDroid` calls `resolveCallRuntime(options, closureRuntime)` → bound id wins; unbound id yields `{...fallback, sessionKey: id}`; missing id falls back to the (untrusted) closure instance.
**Invariant:** Two conversations sharing a cwd must never share agent history — pool keys derive from the RESOLVED `sessionKey`, and an unbound-but-present sessionId still re-keys it; only a truly absent sessionId may use the closure identity.
**Probe:** `test/context-forward.test.ts:59-84` ("resolveCallRuntime prefers the caller's bound runtime over the closure instance"): Monica's registry race resolving Grace's call returns Grace's cwd+sessionKey; unbound `sess-unknown` keeps Monica's cwd but re-keys to `sess-unknown`; `undefined` options return the closure object itself.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "bindSessionRuntime resolveCallRuntime sessionRuntimes", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the three-rung ladder (bound map → synthetic re-key → closure fallback) and the delete-then-set insertion-order refresh with a bounded LRU map. Adapt the option field name (`sessionId`) and what InstanceRuntime carries to your host. Omit Pi-specific session_start binding mechanics; any per-instance registration hook works.
