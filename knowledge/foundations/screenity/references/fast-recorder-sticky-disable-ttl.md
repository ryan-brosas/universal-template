<!-- capsule-v2 -->
# Sticky device-disable TTL — how does a failure ban self-heal without racing concurrent writers?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** When a hardware codec fails once, how do you ban it per device yet guarantee recovery — and who is allowed to clear the ban early?

## Lazy-expiry sticky state
**Path/Symbol:** `src/media/fastRecorderGate.ts:87-119` (`getFastRecorderStickyState`), `:186-226` (`markFastRecorderFailure`), constant `STICKY_DISABLE_TTL_MS = 14 days` :85.
**Signature:** `getFastRecorderStickyState(): Promise<FastRecorderStickyState>`; `markFastRecorderFailure(reasonCode: string, details?: Record<string, any>): Promise<void>`.
**Data Shape:** four storage keys (`fastRecorderDisabledForDevice/Reason/Details/At`); TTL compared against `lastFailureAt`; every write is wrapped in try/catch that degrades to "enabled" / no-op.

### Decisive source (expiry-on-read)
```ts
// Report stale disables as cleared. Don't wipe other keys here to
// avoid racing concurrent setters; next failure overwrites anyway.
const expired =
  disabledRaw &&
  lastFailureAt > 0 &&
  Date.now() - lastFailureAt > STICKY_DISABLE_TTL_MS;
if (expired) {
  try {
    await chrome.storage.local.set({ [STORAGE_KEYS.stickyDisabled]: false });
  } catch {}
  return { disabled: false };
}
```

### Decisive source (authoritative late report clears a coarse ban)
```ts
if (isFastRecorderFailureTransient(reasonCode, errStr, detail)) {
  // Clear any sticky disable a coarser path set earlier in this same
  // attempt (e.g. the BG no-first-chunk alarm fires without detail and
  // can't discriminate; the detailed recorder-side report arriving here
  // is authoritative). ...
  await chrome.storage.local.set({
    [STORAGE_KEYS.stickyDisabled]: false,
    [STORAGE_KEYS.lastFailureAt]: Date.now(),
    fastRecorderTransientFailure: { reasonCode, details, at: Date.now() },
  });
  return;
}
```
On a real (non-transient) failure it sets the four keys AND calls `invalidateCachedProbe()` — "a real failure outranks a cached probe pass, which would otherwise vouch for this machine for the rest of its TTL."

**Flow:** failure → classify → transient? clear-sticky+log-transient : set-sticky+invalidate-probe → later reads lazily expire after 14 days by rewriting only `stickyDisabled=false`.
**Invariant:** expiry must not delete reason/details keys (concurrent-setter race); only the detailed in-attempt report may flip a sticky flag back off; all storage errors degrade fail-open.
**Probe:** deterministic anchors: grep for `avoid racing concurrent setters` (:97-98), `authoritative` (:199-200 comment block), `outranks a cached probe pass` (:220-221). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
trace_path(project="screenity", function_name="markFastRecorderFailure", direction="inbound")
→ observed callers_total=19: Recorder.jsx (8 sites incl. armStartGateTimeout/onError/onFinalized),
  Region.Recorder (5), CloudRecorder (maybeStartRecording/startRecording), chooseTrackEncoder,
  handleAlarm, addAlarmListener.alarmListener — the ban writer is shared by every failure path.
```

## Verdict
Adopt lazy expiry-on-read plus the transient-clears-coarse-ban rule. Adapt key names/TTL duration to your product's tolerance. Omit Screenity's specific reason codes (`webcodecs-no-first-chunk`, etc.) unless porting its watchdog too.
