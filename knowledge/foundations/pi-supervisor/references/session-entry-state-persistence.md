<!-- capsule-v2 -->
# Session-entry state persistence — how does supervision state survive compaction and restart?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** Where does supervisor state live, what entry type carries it, and which scan order makes "newest wins" correct?

## SupervisorStateManager persistence kernel (`src/state/manager.ts`)
**Path/Symbol:** `src/state/manager.ts:SupervisorStateManager` (whole class :16-133; `loadFromSession` :114-127, `persist` :129-132, `ENTRY_TYPE` :14).
**Signature:** `loadFromSession(ctx: ExtensionContext): void`; `persist(): void` via `pi.appendEntry(ENTRY_TYPE, this.state)`.
**Data Shape:** State = `{active, outcome, provider, modelId, interventions[], startedAt, reframeTier?, idleSteers?}` stored as a session entry `{type:'custom', customType:'supervisor-state', data}`.

### Decisive source
```ts
const ENTRY_TYPE = 'supervisor-state';
loadFromSession(ctx) {
  const entries = ctx.sessionManager.getBranch();      // ACTIVE BRANCH ONLY
  for (let i = entries.length - 1; i >= 0; i--) {      // NEWEST FIRST
    const entry = entries[i];
    if (entry.type === 'custom' && entry.customType === ENTRY_TYPE) {
      this.state = { ...entry.data };                  // shallow copy
      return;
    }
  }
  this.state = null;                                   // summarized away ⇒ dead
}
```

**Flow:** every mutating op (`start`, `stop`, `addIntervention`, `setModel`, `updateOutcome`, tier changes) calls `persist()` immediately — append-only journaling, not snapshot-once. Reload scans the branch BACKWARD and takes the FIRST (most recent) supervisor-state entry; multiple entries exist because every mutation appended a new one. If compaction summarized the entries away, load yields `null` and supervision is off.
**Invariant:** (1) Reverse-scan-first-match IS the "latest state" rule — a forward scan would resurrect the ORIGINAL goal after goal appends. (2) Branch-scoped only: forked/other-branch states are invisible. (3) `stop()` keeps the object but flips `active:false` and blanks outcome, then persists — so the tombstone also rides the journal. (4) Persist is fire-and-forget append; there is no delete.
**Probe:** `tests/compaction.test.ts` — `restores state from custom entry in session` (:64), `uses the most recent supervisor-state entry when multiple exist` (:138), `full lifecycle: start -> compact -> reload -> repersist` (:264), `handles state loss when supervisor-state was summarized away` (:314).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "SupervisorStateManager persist appendEntry customType", limit: 8 });
```

## Verdict
Adopt custom-entry journaling + newest-wins reverse scan for any host with an appendable session log. Adapt entry type name/copy depth to your schema. Omit pi-specific `sessionManager.getBranch()` shape; any ordered entry list works.
