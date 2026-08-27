<!-- capsule-v2 -->
# locks-js-callback-release-contract — Who releases a Web Lock, and when — what is the JS-side contract over a BEAM lock manager?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** Given a BEAM lock manager that never times out, what must the embedded-language layer own so that locks are actually released after callbacks complete, and how do the three manager outcomes map onto the language's error/null idioms?

## JS-owned release-over-Beam.call seam
**Path/Symbol:** `priv/ts/locks.ts` whole (77L): `LockManager.request` (options/callback normalization, `__locks_request` call, outcome mapping, try/finally release), `query` (`__locks_query`); `lib/quickbeam/locks_api.ex` whole (23L): atom→string mapping (`:granted`→`"granted"`, `:not_available`→`"not_available"`, `:holder_down`→`"holder_down"`), `release_lock` returns nil; wiring `runtime.ex:180-182` — `__locks_request`/`__locks_release` are `{:with_caller, ...}` so the JS runtime's pid becomes the holder identity.
**Signature:** JS `navigator.locks.request(name, callbackOrOptions, maybeCallback) => Promise<T | null>`; `navigator.locks.query() => Promise<{held: LockInfo[], pending: LockInfo[]}>`; BEAM side `LocksAPI.request_lock([name, mode, if_available], caller_pid) :: String.t()`.
**Data Shape:** wire values are plain strings and booleans; the Lock object handed to the callback is a frozen-ish plain object `{name, mode}` with no release handle — release is positional by name only.

### Decisive source
```ts
const result = await Beam.call('__locks_request', name, mode, ifAvailable)

if (result === 'not_available') {
  return await callback(null)
}

if (result === 'holder_down') {
  throw new DOMException('Lock holder terminated', 'AbortError')
}

const lock: Lock = { name, mode }

try {
  return await callback(lock)
} finally {
  await Beam.call('__locks_release', name)
}
```

```elixir
def request_lock([name, mode, if_available], caller_pid) do
  case QuickBEAM.LockManager.request_lock(name, mode, caller_pid, if_available) do
    :granted -> "granted"
    :not_available -> "not_available"
    :holder_down -> "holder_down"
  end
end
```

**Flow:** the TS layer normalizes the two calling forms (callback-only vs options+callback), defaults mode to `"exclusive"` and ifAvailable to false, pre-checks an already-aborted signal → one blocking `Beam.call('__locks_request', ...)` whose caller pid IS the holder identity (the `{:with_caller}` dispatch in runtime.ex passes it through) → outcome mapping: `"not_available"` means the callback still runs but with `null` (the spec's ifAvailable semantics — the guest decides what null means); `"holder_down"` becomes an `AbortError` DOMException (the waiter's monitored predecessor died); anything else wraps the callback in `try/finally` where the FINALLY performs `__locks_release` → because the callback may be async, the release happens after the promise settles, and a throwing callback STILL releases (finally runs) → the only path where the JS layer does not release is process death, which the manager's DOWN monitor covers (capsule `lock-manager-shared-exclusive-state-machine`).
**Invariant:** (1) Release ownership is split exactly once: normal completion belongs to the language layer (finally block), abnormal holder death belongs to the BEAM layer (monitor). Neither side double-releases in the normal path because release matches name AND holder pid, and the finally's caller is the same pid that was granted. (2) The three-outcome string vocabulary is the complete wire contract — adding a fourth manager outcome requires a TS mapping change; unmapped strings would silently take the "granted" path (no else-throw), so the mapping is fail-open by construction and must stay exhaustive. (3) `ifAvailable` null-callback is awaited before return, so a slow null-callback still serializes correctly against later requests on the same name. (4) The Lock object carries no token — re-entrancy (requesting the same name from inside the callback) deadlocks by design, matching the spec's single-holder model; the ifAvailable escape hatch is the only sanctioned re-entrant probe.
**Probe:** `grep -n '__locks_request\|__locks_release\|__locks_query' lib/quickbeam/runtime.ex` → 3 hits (:180-182); `grep -n 'finally\|__locks_release' priv/ts/locks.ts` → 2 hits; `grep -n ':granted\|:not_available\|:holder_down' lib/quickbeam/locks_api.ex` → 3 hits.
**Probe:** `test/web_apis/locks_test.exs:66-77` — "lock is released after callback completes": sequential requests on the same name both succeed (proves the finally fired); `:44-57` ifAvailable-inside-held returns null; cross-runtime test (:104-129) proves holder identity is the runtime pid, not the JS thread.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "LocksAPI request_lock with_caller __locks_release navigator.locks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split-release contract for any embedded-language resource API over a BEAM manager: the language layer owns release-on-completion via finally (works for async callbacks and throwing callbacks alike), the BEAM layer owns release-on-death via monitors, and the grant identity is the CALLER PROCESS captured at dispatch time (`{:with_caller}`), never a JS thread id. Adopt the exhaustive small-string outcome vocabulary with an explicit mapping table at the boundary — and when porting, make the TS-side mapping fail-CLOSED (throw on unknown outcomes) to fix QuickBEAM's fail-open gap. Adapt the AbortError/null idioms to your guest language's cancellation model; omit the pre-abort signal check if your guest has no AbortSignal. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte, Retrieve not executed.
