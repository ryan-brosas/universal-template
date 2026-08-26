<!-- capsule-v2 -->
# Managed extension timers — how do you let third-party code schedule background work without letting one bad callback kill the host?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** A plugin calls setInterval and its callback throws on a fresh stack, bypassing every dispatch try/catch — what is the containment contract?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/extensions/managed-timers.ts:ManagedTimers` (:1-83 whole); wired at `extensions/runner.ts:ExtensionRunner#managedTimers` (:483-493); teardown at `runner.ts:emitSessionShutdownEvent` (:387-399).
**Signature:** `new ManagedTimers(onError: (event: string, error: string, stack?: string) => void)`; `setInterval(cb, ms?, ...args): Timer` / `setTimeout(...)` / `clear(timer)` / `clearAll()`.
**Data Shape:** Raw `Timer` handles in a private `Set`; one-shots self-deregister before running; onError receives `${kind}_callback` ("interval_callback"/"timeout_callback"), message, optional stack.

### Decisive source
```ts
// issue #5664: raw setInterval escapes handler-dispatch try/catch -> uncaughtException -> fatal postmortem
#run(kind: "interval" | "timeout", callback: (...args: unknown[]) => void, args: unknown[]): void {
	try {
		const result = callback(...args) as unknown;
		if (result instanceof Promise) {
			result.catch((err: unknown) => this.#report(kind, err));
		}
	} catch (err) {
		this.#report(kind, err);
	}
}
// setTimeout wrapper deregisters BEFORE running so a throwing one-shot cannot linger in the set:
const timer = setTimeout(() => { this.#timers.delete(timer); this.#run("timeout", callback, args); }, ms, ...args);
```
**Flow:** sanctioned ctx.setInterval/setTimeout -> wrap callback in #run -> sync throw caught OR rejected promise .catch-ed -> #report logs warn + forwards to onError -> session shutdown emits session_shutdown then `finally { disposeFileFallbacks(); clearManagedTimers(); }`.
**Invariant:** (1) no timer callback can reach the process uncaughtException path; (2) every handle is `.unref()`-ed — background timers never keep the process alive; (3) cleanup runs even when shutdown handlers fail/timeout (finally, not after-await).
**Probe:** no dedicated ManagedTimers unit test at this pin — probe by anchor instead (coverage caveat recorded honestly): grep "unref?.()" and "this.#timers.delete(timer)" in managed-timers.ts must both hit; grep "clearManagedTimers" in extensions/runner.ts must hit :1210.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "ManagedTimers", limit: 10 });
```

## Verdict
Adopt: wrap-everything timer registry with contained callbacks, unref-ed handles, one-shot early deregister, teardown finally-clear. Adapt: route onError into your own host error bus (oh-my-pi emits ExtensionError with extensionPath "<timer>"). Omit: nothing else host-specific.