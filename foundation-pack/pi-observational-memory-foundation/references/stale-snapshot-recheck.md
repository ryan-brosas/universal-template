<!-- capsule-v2 -->
# Stale-snapshot re-check — recover an availability snapshot that never learned the provider, bounded and rate-limited

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** When your auth gate consults a startup-populated snapshot that may be stale or never populated, how do you add the live second half without turning every resolve into a network call?

## Path/Symbol
**Path:** `src/runtime.ts`
**Symbol:** `Runtime.recheckProviderCredential` **:229-281**, constants `AVAILABILITY_RECHECK_TIMEOUT_MS = 5_000` / `AVAILABILITY_RECHECK_REARM_MS = 60_000` **:48-49**, per-provider latch `availabilityRecheckedAt = new Map<string,number>()` **:112**; call-site gate at `resolveModel` **:183-185**.

**Signature:** `private async recheckProviderCredential(registry: unknown, model: unknown, provider: string): Promise<boolean>`

**Data Shape:** host facade exposes `refresh(options?) → Promise<unknown>` performing a live credential pass and updating the snapshot (`configuredProviders`); pi ≥0.84 forwards `{ allowNetwork, providers, signal }`, pi 0.81's facade is `refresh()` → `runtime.reloadConfig()` which ignores the options and runs a FULL network-permitted pass. The extension must work through either.

### Decisive source
```ts
const last = this.availabilityRecheckedAt.get(provider);
const now = Date.now();
if (last !== undefined && now - last < AVAILABILITY_RECHECK_REARM_MS) return false;   // rate-limit BEFORE any work
this.availabilityRecheckedAt.set(provider, now);
...
await Promise.race([
    refresh.call(registry, { allowNetwork: false, providers: [provider], signal: controller.signal }),
    new Promise<void>((resolve) => {
        controller.signal.addEventListener("abort", () => { timedOut = true; resolve(); });
    }),
]);
...
// Re-read even when the refresh reported an error or timed out: a scoped pass can
// update the snapshot for this provider and still fail elsewhere.
const recovered = hasConfiguredProviderCredential(registry, model);
```

**Flow:** only reached when everything already looks ambient-shaped (ok:true + nothing usable + not OAuth + not empty-string key + snapshot-half false) → re-arm check (per-provider 60s latch, stamped BEFORE the await so concurrent resolves collapse) → duck-type `refresh` as function else debug-log and return false → race refresh against a 5s abort timer (the timer RESOLVES the race, never rejects — "timed out" is a valid outcome whose snapshot writes are still read back) → `finally clearTimeout` → re-read the snapshot half even after error/timeout → return `recovered`.

**Invariant (what a porter gets wrong):**
1. **Race instead of signal-only timeout** because pi 0.81's facade never observes `signal` — relying on AbortController alone would hang on old hosts. The race side RESOLVES on abort rather than rejecting, so a partial scoped pass's snapshot updates still count.
2. **Rate-limit before await**: the re-arm timestamp is set before the await so N concurrent resolves pay one re-check. An unauthenticated host pays the cost once per minute, not once per consolidation.
3. **`allowNetwork:false`** — a credential re-check must never wait on a model-catalog fetch; `providers:[provider]` scopes both the work AND the snapshot writes.
4. **Never throws**: no-refresh registries and throwing refreshes both degrade to `ok:false` with diagnostics (test-pinned).
5. This implements the SECOND half of the host's own two-half gate (`hasConfiguredAuth(provider) || (await checkAuth(provider)) !== undefined`, agent-session.js): reading only the snapshot half leaves consolidation dead all session when the availability pass was skipped/aborted/failed — same silent-failure class as the ambient bug. The mirror-the-host principle from request-time-signing-gate applies here too.

**Probe (direct tests):**
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
grep -c "staleSnapshotFacade" tests/ambient-credential-auth.test.ts   # expect 6 && \
grep -c "availabilityRecheckedAt" src/runtime.ts                      # expect 3 && \
npx vitest run tests/ambient-credential-auth.test.ts                  # 12 passed (7 in the stale-snapshot describe)
```

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "recheckProviderCredential availabilityRecheckedAt refresh allowNetwork", limit: 5 });
// rank1: ...src.runtime.Runtime.recheckProviderCredential Method src/runtime.ts 229-281
```

**Verdict:** Adopt the bounded, rate-limited, version-skew-tolerant live re-check raced against a resolving timeout, with post-error snapshot re-reads. Adapt option names to your host's refresh surface. Omit nothing — every guard maps to a pinned test.
