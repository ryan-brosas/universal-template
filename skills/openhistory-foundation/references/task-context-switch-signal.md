<!-- capsule-v2 -->
# Task-context-switch signal — when does activity in a different (or the same) application start a NEW task rather than join the current one?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** How do you split episodes on task switches without shattering rapid multi-app workflows?

## signalsTaskContextSwitch
**Path/Symbol:** `src/main/episode-segmenter.ts:signalsTaskContextSwitch` (lines 166-186) with `applicationKey` (198-202) and `lastMatching` (188-196).
**Signature:** `signalsTaskContextSwitch(current: ActivityEvent[], lastWork: ActivityEvent, event: ActivityEvent): boolean`.
**Data Shape:** gated by caller: only evaluated after ≥`contextSwitchGapMs` (2 min) of quiet since the LAST WORK event; app key = `bundleIdentifier` else `pid:<processIdentifier>`.

### Decisive source
```ts
const previousApplication = applicationKey(lastWork);
const nextApplication = applicationKey(event);
if (previousApplication && nextApplication && previousApplication !== nextApplication) return true;
const comparableKinds = ["url_changed", "document_context_changed", "window_changed"];
if (!comparableKinds.includes(event.kind)) return false;
const previousContext = lastMatching(current,
  (candidate) => candidate.kind === event.kind && applicationKey(candidate) === nextApplication);
return Boolean(previousContext && eventFingerprint(previousContext) !== eventFingerprint(event));
```

**Flow:** quiet-period gate satisfied → app-key change vs last work event ⇒ switch → same app: only context-bearing kinds are compared, against the most recent SAME-kind SAME-app event in the open episode → fingerprint divergence ⇒ switch (a second edit to the same page does not).
**Invariant:** the switch compares against `lastWork`, not the raw previous event — passive context between work bursts never masks a real switch, and the 2-min quiet requirement means rapid cross-app movement is never split. The activation event itself joins the NEW episode (test-pinned: `episodes[1].events[0].id === "browser-activation"`).
**Probe:** `src/main/episode-segmenter.test.ts:135-152` — executed GREEN at pin: different app after 2.5-min meaningful quiet splits into 2 episodes starting at the activation; same sequence at 30-s gaps stays ONE workflow.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "signalsTaskContextSwitch applicationKey lastMatching", limit: 10 });
```
Executed live byte-for-byte: returns the three cited `episode-segmenter` symbols as top rows; no unrelated subsystem ranked above them.

## Verdict
Adopt the two-tier switch test (app identity, then same-kind context fingerprint) behind an explicit quiet-period gate; adapt the comparable-kind list and quiet threshold to your stream's semantics; omit pid-fallback app keys if your platform always provides bundle ids. Coverage: `no_recorded_issue` on `src/main/episode-segmenter.ts`; probe suite executed green at pin.
