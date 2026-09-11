<!-- capsule-v2 -->
# Recommendation/task state machines — how do accept/dismiss/queue/run transitions stay conflict-safe without row locks?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Where do illegal recommendation and remediation-task transitions get rejected, and how does a failed execution remain a RESULT rather than a thrown error?

## Private-constructor aggregates with explicit guard clauses
**Path/Symbol:** `packages/v2/table-query-ops/src/domain.ts`: `TableQueryRecommendation` (:1048-1120: `createOpen`, `rehydrate`, `accept` :1099, `dismiss` :1108), `TableQueryRemediationTask` (:1122-1220: `createQueued` :1143, `start` :1173, `succeed` :1189, `fail` :1203).
**Signature:** `accept(now): Result<Recommendation, DomainError>`; `start(workerId, now): Result<Task, DomainError>`; ids minted `tqr_`/`tqt_ + nanoid(16)`; task defaults `attempts=0, maxAttempts=3`.
**Data Shape:** recommendation states open→{accepted|dismissed}; task states queued→running→{succeeded|failed}, failed→running (retry re-entry), cancelled terminal. Every transition returns a NEW instance (immutable props spread).

### Decisive source
```ts
accept(now) {
  if (this.props.status !== 'open')
    return err(domainError.conflict({ message: 'Only open recommendations can be accepted' }));
  return ok(new TableQueryRecommendation({ ...this.props, status: 'accepted', lastModifiedTime: now }));
}
start(workerId, now) {           // failed tasks MAY restart — the retry path
  if (this.props.status !== 'queued' && this.props.status !== 'failed') return err(…conflict…);
  return ok(new Task({ ...this.props, status: 'running', attempts: this.props.attempts + 1,
                       lockedBy: workerId, lockedAt: now }));
}
```

**Flow:** handlers load aggregate via repository → call the transition → persist returned instance. Accept handler additionally picks the first `executableInPhase1` candidate as the task kind (explicit kind overrides), validating it through an independent allowlist (`isExecutablePhase1Kind`) — defense in depth against a stale snapshot carrying a non-executable kind.
**Invariant:** Illegal transitions are DOMAIN CONFLICTS (Result err), never exceptions and never silent no-ops; only running tasks can succeed/fail; `attempts` increments exactly at start (not at fail) so a crash between start/save is visible as a stuck-running row that the stale-reclaim claim can pick up.
**Probe:** `domain.spec.ts:478` "can be accepted only from open state" (+ dismiss twin); executor-side failure semantics pinned by `application.ts` RunTableQueryRemediationTaskHandler flow.
**Coverage caveat:** task transition specs live in the advisor matrix suite (`domain.spec.ts:289` describe) rather than dedicated per-method tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableQueryRemediationTask start succeed fail createQueued", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt immutable-aggregate-with-guard-clauses and the "executor failure is task state, not handler error" split; adapt status vocabularies; omit nanoid prefix conventions if you have id infrastructure.
