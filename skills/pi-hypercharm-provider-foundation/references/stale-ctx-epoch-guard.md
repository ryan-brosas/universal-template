<!-- capsule-v2 -->
# Stale-ctx epoch guard — how do async continuations survive session replacement (fast-resume, /new, /fork) without crashing pi?

**Source:** pi-hypercharm-provider MIT `main@4520704` (commit `82de131` "guard stale extension ctx in detached refresh chains"); Codebase Memory project `pi-hypercharm-provider`. **Question:** Every background `.then(() => updateStatus(ctx))` captured a ctx at schedule time — when the session is replaced mid-flight, that ctx is stale and THROWS. How do you disarm those chains without try/catch noise at every call site?

## Epoch counter + stale-error swallow
**Path/Symbol:** epoch `let statusEpoch = 0` `index.ts:628-629` (bumped `++statusEpoch` FIRST line of `session_start` `index.ts:1031-1032`); detector `isStaleCtxError` `index.ts:713-715`; guarded entry `updateStatus` `index.ts:719-725`; deferred render `updateStatusAfter(promise, ctx)` `index.ts:727-734`; key-resolution veto `index.ts:1049-1050`; model-swap veto `index.ts:1059`.
**Signature:** `updateStatusAfter(promise: Promise<void>, ctx: ExtensionContext): void`; `isStaleCtxError(err: unknown): boolean`.
**Data Shape:** module-singleton integer; every detached continuation captures `const epoch = statusEpoch` AT SCHEDULE TIME and compares against the live value AFTER its await.

### Decisive source
```ts
function isStaleCtxError(err: unknown): boolean {
	return err instanceof Error && err.message.includes("This extension ctx is stale");
}

// Render entry point: swallows the stale-ctx throw so a refresh racing a
// session replacement (newSession/fork/switchSession/reload) can't crash pi.
function updateStatus(ctx: ExtensionContext): void {
	try {
		renderStatus(ctx);
	} catch (err) {
		if (!isStaleCtxError(err)) throw err;
	}
}

// Re-render once an async refresh lands, unless the session was replaced
// meanwhile (epoch bump) — its ctx is stale and the render is obsolete anyway.
function updateStatusAfter(promise: Promise<void>, ctx: ExtensionContext): void {
	const epoch = statusEpoch;
	void promise.then(() => {
		if (epoch === statusEpoch) updateStatus(ctx);
	});
}
```
Veto points inside the `session_start` chain:
```ts
const epoch = ++statusEpoch;
...
resolveApiKey(ctx.modelRegistry).then(() => {
	// A session replacement while the key resolved invalidated the
	// captured ctx (fast-resume, /new, /fork); nothing below may touch it.
	if (epoch !== statusEpoch) return;
	...
	revalidateModels(...).then((freshBase) => {
		if (freshBase && epoch === statusEpoch && !signal.aborted) { ... }
```

**Flow:** every `void refresh(...).then(() => updateStatus(ctx))` call site became `updateStatusAfter(refresh(...), ctx)` (:820 out-of-credits path, :883 command leg, :958 interactive leg, :1055-1056 prefetch legs, :1071 model_select) → old sessions' continuations wake, see a bumped epoch, and silently drop their render → the NEW session's own chain renders with its own fresh ctx.
**Invariant:** TWO complementary defenses for two different failure shapes: (a) the EPOCH prevents obsolete WORK from ever touching a dead ctx (cheapest check first — no throw happens at all), while (b) the MESSAGE-SUBSTRING catch in `updateStatus` is the safety net for any remaining direct-render race (e.g. synchronous `updateStatus(ctx)` calls whose ctx went stale between check and use). The catch is deliberately narrow (`instanceof Error && message.includes(...)`) and RE-THROWS anything else — swallowing all errors would mask real bugs as missing footer lines. Epoch capture must happen BEFORE the await; comparing against live `statusEpoch` after it. AbortControllers cancel I/O; the EPOCH cancels CONTINUATIONS — you need both because aborts stop fetches but not already-resolved promises queued on them.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pi-hypercharm-provider && grep -cE "epoch [!=]= statusEpoch" index.ts'` → 3 (`!==` veto at :1050, `===` guards at :732 and :1059; exact-string `grep -c "epoch === statusEpoch"` alone → 2); `grep -c "++statusEpoch" index.ts` → 1; `grep -c "This extension ctx is stale" index.ts` → 1; `grep -c updateStatusAfter index.ts` → 7 (1 def + 6 call sites). Direct test `tests/status.smoke.ts` imports nothing of this (runtime plane) — coverage caveat recorded.
**Coverage caveat:** runtime event plane untested upstream; guard logic verified by source-read + grep counts only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "stale extension ctx updateStatusAfter", limit: 3 });
// → pi-hypercharm-provider.updateStatusAfter Function index.ts 727-734
//   pi-hypercharm-provider.isStaleCtxError Function index.ts 713-715
```

## Verdict
Adopt the epoch-capture-before-await + narrow-stale-swallow pair verbatim for any host whose extension ctx dies with its session while background work outlives it. Adapt the sentinel message to your host's exact stale error text. Omit nothing — the narrowness of both checks IS the pattern.
