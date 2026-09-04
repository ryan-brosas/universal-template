<!-- capsule-v2 -->
# Tee-reader barrier (allSettled drain) — how does turn_end know the teed usage scan actually finished before committing pendings?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider` (node `pi-hypercharm-provider.settleTeeReaders`, `index.ts:491-496`). **Question:** Teed response bodies settle asynchronously and independently of the main stream — what is the synchronization contract that makes pending→committed accounting correct instead of racy?

## Barrier over a self-cleaning promise set
**Path/Symbol:** `index.ts:483-496` (`const teeReaders = new Set<Promise<void>>()` :483, `trackTeeReader` :485-490, `settleTeeReaders` :491-496); producers/consumers: `readUsageFromTee` `index.ts:518-566` (lock released at `:562`), capture helpers `captureRateLimitHeaders :497-504` + `captureUsage :507-515`; turn_end consumer wired at the event plane (`await settleTeeReaders()` before `commitPending`, `index.ts:1078-1079`).
**Signature:** `trackTeeReader(promise: Promise<void>): void`; `settleTeeReaders(): Promise<void>`.
**Data Shape:** module-singleton `Set<Promise<void>>` — membership IS the "scan in flight" bit; no counters, no timestamps.

### Decisive source
```ts
const teeReaders = new Set<Promise<void>>();

function trackTeeReader(promise: Promise<void>): void {
	teeReaders.add(promise);
	const release = () => { teeReaders.delete(promise); };
	promise.then(release, release);          // BOTH outcomes self-clean
}

function settleTeeReaders(): Promise<void> {
	if (teeReaders.size === 0) return Promise.resolve();
	const pending = Array.from(teeReaders);
	return Promise.allSettled(pending).then(() => undefined);
}
```

**Flow:** each `streamHypercharm` request tees its body; the scanner promise is registered via `trackTeeReader` at request start → the set drains itself on both fulfill AND reject (`.then(release, release)`), so the barrier never waits on dead readers → at `turn_end` the event plane awaits `settleTeeReaders()`, snapshotting the set ONCE into `pending` before awaiting (`Array.from` first) so promises settling mid-wait can't be double-awaited → only then does `commitPending` fold `pendingRequests/pendingSpendHc` into `sessionStats`.
**Invariant:** every teed reader is registered BEFORE any bytes are read and removed on BOTH settle paths — a `.then(release)` single-argument form would leak rejects into unhandled-rejection noise and wedge the set. The empty-set fast path returns a resolved promise (zero-cost for turns with no provider traffic). The barrier uses `allSettled` + explicit `=> undefined`, NEVER `Promise.all`: a scanner that died on an aborted main stream must not reject turn_end's commit. Pendings are committed exactly once per turn because commit zeroes them; the barrier is what guarantees the zeroing happens after the last byte was scanned.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-hypercharm-provider && grep -c "trackTeeReader\|settleTeeReaders" index.ts'` → 4; `grep -c allSettled index.ts` → 1; `grep -c releaseLock index.ts` → 1. Runtime path has no upstream test — coverage caveat recorded. (Probe paths cite the `pi-hypercharm-provider` symlink root = live `pi-ecosystem/pi-hypercharm-provider` tree at HEAD 4520704.)
**Coverage caveat:** event-plane timing (turn_end ordering) is untested upstream; the smoke suite covers none of this (runtime file).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "settleTeeReaders trackTeeReader", limit: 3 });
```

## Verdict
Adopt the self-cleaning set + allSettled barrier shape verbatim for any tee-and-commit telemetry design. Adapt the trigger point to your host's turn-end event. Omit nothing here — it is host-independent.
