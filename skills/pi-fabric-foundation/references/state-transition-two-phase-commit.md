<!-- capsule-v2 -->
# State two-phase commit — how do you run propose→commit over a CAS key with compensating rollback, and why must rollback become forbidden the instant the commit marker lands?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does a durable world-model head stay crash-safe and contention-correct when every write is an independent compare-and-swap on a shared store?

## Proposal event → ledger CAS writes → pending head → commit marker → proof upgrade, with reverse-order compensation before the marker only
**Path/Symbol:** `src/state/store.ts`: `transition` (:604-793), `markHeadCommitted` (:795-827), `advanceHead`/`advanceHeadWithBefore` (:829-878), `rollbackWrites` (:880-909), `lastDeletedVersion` (:915-932); constants `CAS_RETRY_LIMIT = 8` (:86), `EVENT_ROLLBACK_LIMIT = 8` (:92). Direct tests: `tests/state-provider.test.ts` describe("StateStore") — :45, :88, :113, :648, :689, :742, :805, :861, :907, :1110 (30/30 GREEN via repo vitest).
**Signature:** `transition(input, identity, cwd?): Promise<{event: MeshEvent, head: StateHead}>`; `advanceHeadWithBefore({payload, from?, force?, expectedVersion, identity}): {entry, before}`.

### Decisive source
```ts
const expectedVersion = physicalCurrent?.version ?? this.lastDeletedVersion(CURRENT_KEY);
// … publish proposal (phase:"proposed") → CAS ledgers (each AppliedStateWrite{key,before,written})
const advanced = await this.advanceHeadWithBefore({ payload /* commitProof v1 "pending" */, … });
await this.store.publish({ kind: "transition.committed", … }); commitMarkerPublished = true;
const committedHead = await this.markHeadCommitted(advanced.entry, identity);   // CAS proof→committed
} catch (error) {
  if (commitMarkerPublished) throw new Error(
    `State transition committed, but its durable head proof remains pending: ${boundedError(error)}`);
  const rollback = await this.rollbackWrites(
    [...(headWrite ? [headWrite] : []), ...applied.reverse()], identity);
```

**Flow:** pre-validation rejects a physically-present but structurally-invalid head ("uncommitted or quarantined proposal") and checks the declared `from` against the committed head's `to` unless `force`. Complexity reductions require non-empty evidence BEFORE any write. The write ladder is strictly ordered; every completed write is captured with its before-value. Failure before the marker runs compensation in REVERSE order: restore prior values at `written.version`, or delete newly-created keys while RECORDING their post-delete versions into the rejection event (chunked by 8) — `lastDeletedVersion` later scans rejected events backwards so a future CREATE stays version-aware instead of colliding at version 0. After the marker, compensation is FORBIDDEN: a failed proof-upgrade throws "committed, but its durable head proof remains pending". CAS contention re-reads and re-validates the chain — still chained ⇒ retry with the new version (bounded 8), broken ⇒ error naming the ACTUAL head label. `markHeadCommitted` reconciles idempotently: same transitionId already committed ⇒ adopt it.
**Invariant:** a proposal is invisible until its marker (history/verification fold only committed phases); quarantine vs rejection is explicit (`quarantine: rollback.errors.length > 0`); restoration failures surface in the thrown detail as "rollback quarantine" — the head never silently half-applies.
**Probe:** executed byte-for-byte: `grep -n "CAS_RETRY_LIMIT = " src/state/store.ts` → :86; `grep -c "commitMarkerPublished" src/state/store.ts` → 3 (:665 decl, :719 set, :723 check); `grep -n "applied.reverse()" src/state/store.ts` → :730; `grep -n "EVENT_ROLLBACK_LIMIT" src/state/store.ts | head -2` → :92, :739; suite GREEN (state-provider 30/30).

## Get live surrounding code
**Retrieve:** executed live against project `pi-fabric`:
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "advanceHeadWithBefore markHeadCommitted rollbackWrites lastDeletedVersion transition commit marker pending", limit: 6 });
```
(Rank #1–4 resolve `rollbackWrites` :880-909, `markHeadCommitted` :795-827, `lastDeletedVersion` :915-932, `advanceHeadWithBefore` :839-878 line-exact.)

## Verdict
Adopt captured-before-value compensation in strict reverse order, the post-marker rollback prohibition with a loud pending-proof error, deleted-key version carry for post-delete CAS creation, and contention errors that name the actual current state; adapt retry limits, chunk sizes, and event vocabulary to your store; omit the complexity-evidence precondition if you have no self-improvement loop to police — but keep SOME pre-write admission gate that requires replayable justification for risky transitions.
