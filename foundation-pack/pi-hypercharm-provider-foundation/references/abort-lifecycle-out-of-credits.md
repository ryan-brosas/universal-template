<!-- capsule-v2 -->
# Abort-controller lifecycle + out-of-credits one-shot notify — how do you cancel in-flight background work across session boundaries without leaking?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** How do you manage multiple background fetch controllers (catalog revalidation, status polling) so a new session cancels the old session's work, and how do you alert exactly once on balance exhaustion?

## Dual AbortControllers + commitPending 402 path
**Path/Symbol:** `index.ts:420-421` (`cachedApiKey`, `revalidateAbort`), `index.ts:626-632` (`statusAbort`, `statusEpoch`, `lastCreditsFetchAt`, `creditsInFlight`, `metaFetched`), abort wiring `index.ts:1031-1041` + `:1100-1106`, out-of-credits `index.ts:815-825`.
**Signature:** module-level `revalidateAbort: AbortController | null`; `statusAbort: AbortController | null`; `commitPending(ctx): void`.
**Data Shape:** two independent controller slots — one for catalog revalidation, one for status/account fetches; signals combined with timeouts via `AbortSignal.any([...])`.

### Decisive source
```ts
pi.on("session_start", async (_event, ctx) => {
	revalidateAbort?.abort();
	revalidateAbort = new AbortController();
	const signal = revalidateAbort.signal;
	statusAbort?.abort();
	statusAbort = new AbortController();
	...
});
pi.on("session_shutdown", (_event, ctx) => {
	revalidateAbort?.abort();
	statusAbort?.abort();
	ctx.ui.setStatus(STATUS_KEY_SESSION, undefined);
	ctx.ui.setStatus(STATUS_KEY_ACCOUNT, undefined);
	ctx.ui.setWidget(WIDGET_KEY, undefined);
});
```
Out-of-credits handling inside `commitPending`:
```ts
if (pendingSawOutOfCredits) {
	pendingSawOutOfCredits = false;
	// Re-fetch now so the balance reflects exhaustion immediately
	updateStatusAfter(refreshCredits(cachedApiKey, ..., true), ctx);
	if (!outOfCreditsNotified && ctx.hasUI) {
		outOfCreditsNotified = true;
		ctx.ui.notify("HyperCharm is out of Hypercredits — recharge at hyper.charm.land", "error");
	}
}
```

**Flow:** every `session_start` aborts BOTH prior controllers before creating replacements (a fast session_start/session_start cycle orphans the first revalidation mid-flight) AND bumps `statusEpoch` so stale continuations drop their renders (see stale-ctx-epoch-guard.md) → all fetch helpers accept an optional external signal and combine it with their own timeout (`AbortSignal.any([timeout, signal])`) → shutdown aborts and clears UI.
**Invariant:** a revalidation completing AFTER its session died must be ignored — the continuation checks `!signal.aborted` AND `epoch === statusEpoch` before hot-swapping models (`:1059`). The 402 flag is consumed exactly once per turn; the user notification fires ONCE per session (`outOfCreditsNotified` latch) even across repeated exhausted calls. Forced refetch on 402 bypasses the 15s throttle so the shown balance matches the failure immediately; its render now rides `updateStatusAfter` so an exhausted turn landing in a dying session cannot crash pi.
**Probe:** runtime lifecycle untested upstream — deterministic probe: source-read confirms every `.abort()` has a matching fresh-controller assignment or terminal event, and no fetch path omits signal combination. Coverage caveat recorded.
**Coverage caveat:** untested upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "session_shutdown abort", limit: 5 });
```

## Verdict
Adopt dual-slot controller replacement + aborted-check-before-swap + latched error notification. Adapt to your host's session/shutdown events. Omit provider-specific messaging.
