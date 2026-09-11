<!-- capsule-v2 -->
# Exactly-once async delegate delivery — how does a background child's result reach the model exactly once across three racing delivery paths?

**Source:** billion-context-pi (MIT) `master@6a88c5565355`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** What protocol prevents a finished async delegate's payload from being delivered twice (waiter + injected notification + late wait) or zero times?

## Waiter XOR injection, with a late-wait pointer and atomic status/result flip
**Path/Symbol:** `src/delegate-tool.ts`: module `runs` Map (:181), `DelegateRun` interface (:154), `finalize` closure (:782-853, inside `runDelegate` :648-906; settled latch :785, `child.unref()` :883), `injectedWaitMessage` (:470-479), `injectResult` (:1012-1087), `formatPayload` (:1094-1106), `persistResult` (:1111-1126). Re-anchored at 6a88c556 — pre-pass-4 anchors (runs :122, finalize :617-620, injectedWaitMessage :331-340) DRIFTED when buildChildArgs was extracted.
**Signature:** three tools over one registry: `acp_delegate` (spawn) / `acp_delegate_wait({runId})` (blocking) / `acp_delegate_cancel({runId})`; DelegateRun carries `status`, `result {code,file,body}`, `injected?`, `consumed?`, `waiter?`.
**Data Shape:** result body lives in a FILE (`tmpdir()/acp-delegate/<runId>.out`); the chat only ever sees a header + 160-char task title + file path — "the model uses `read` for details… Keeping this minimal means it stays cheap to retain in context" (:1089-1093).

### Decisive source
```ts
// finalize :782-853 — the three delivery paths and their exclusivity:
if (run.waiter) { ... run.waiter(); return; }        // 1. parked waiter wins;
                                                     //    consumed=true set by
                                                     //    the wait path suppresses injection
if (run.consumed) { return; }                        // 2. already delivered via wait
const injected = injectResult(pi, ...);              // 3. no waiter: fire-and-forget
run.injected = injected;                             //    sendUserMessage(..., deliverAs:"followUp")
// Status + result flip TOGETHER (:826-831): until then the run is still
// "running" to any observer, so a concurrent wait can never see
// "finished but result missing".
// Late wait after injection: injectedWaitMessage (:470-479) returns a POINTER
// to the file, never the payload again.
```

**Flow:** spawn (`child.unref()` so the tool returns while the child lives) → on completion exactly one of: waiter resolution OR follow-up injection (`injectResult` builds the remaining-delegates line from `runs` filtered on `status==="running"` AFTER the status flip, :1031-1040) → any later `wait` returns `injectedWaitMessage` naming the runId and result file plus REMAINING running count (`remainingLineForWait` :458-462). A second CONCURRENT wait is refused outright ("already has a wait in progress") because it would overwrite `run.waiter` and orphan the first waiter's timer/listener. Cancelled runs persist nothing and delete their stream files (:795-802). There is NO status tool — polling is impossible by design, and the timeout message coaches the model: "Do NOT keep waiting or retry — go do other work."
**Invariant:** delivery is exactly-once per channel with cross-channel dedup (`injected`/`consumed` flags); `status`+`result` mutate together; EOF-watchdog finalize has no exit code but delivered output still counts (`effectiveCode` fallback :821-823); completion notifications are marked as automated system notifications, not user requests (:1074 header).
**Probe:** `tests/delegate-tool.test.ts`: `injectedWaitMessage` null when NOT injected (:154-157); dedup message names runId + file (:159-171); tolerates missing file + passes through remaining line (:172-179). Full upstream suite GREEN 414/414 at this pin (executed this pass). Companion: `tests/delegate-event-applier.test.ts` (reply/activity stream assembly).
**Coverage:** check_index_coverage src/delegate-tool.ts + tests/delegate-tool.test.ts → no_recorded_issue, metadata_match. search_graph resolves `finalize` :782-853 and `injectedWaitMessage` :470-479 source-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "makeDelegateWaitTool injectedWaitMessage runs map", limit: 10, fields: ["signature", "name", "file"] });
```
EXECUTED: resolves `src.delegate-tool.injectedWaitMessage` :470-479, `src.delegate-tool.runs` :181, plus makeDelegateWaitTool :527-613.

## Verdict
Adopt the exactly-once protocol wholesale for any async tool whose result lands after its call returned. Adopt the minimal-payload doctrine (file path + title, never inline content). Adapt the injection transport (`sendUserMessage deliverAs:"followUp"`) to your host. Omit pi-specific json-mode event streaming if your children reply plain-text.
