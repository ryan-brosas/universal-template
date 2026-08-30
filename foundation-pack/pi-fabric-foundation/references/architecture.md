<!-- capsule-v2 -->
# Architecture — the schema mutation guard + full-code executor

**Source:** pi-fabric (monotykamary) MIT `<branch>@<commit>`; Codebase Memory `pi-fabric`. **Question:** how does pi-fabric guard every mutation against unauthorized writes and recover a torn transaction?

## Connected graph-selected seam
**Path/Symbol:** `src/schema/controller.ts`: `SchemaController` (:88) — `authorize`/`status`/`hypothesize`/`verify`/`commit`/`abort`; `src/schema/types.ts` (SchemaEvidence, SchemaFileOperation, records, stateBinding); `src/schema/workspace.ts` (`snapshotWorkspace`: fingerprinted workspace snapshots, caps, symlinks); `src/core/atomic-write.ts` (`writeJsonAtomic`).
**Signature:** `SchemaController.authorize(ref)` blocks non-allowlisted mutations (enforce) or reports would-block (audit); `hypothesize` → typed evidence + workspace snapshot fingerprint + state binding → record stored in mesh (ifVersion 0); `verify` → re-snapshot, evidence checked (`file_exists`/`absent`/`contains`/`sha256`/`trusted_command`), certificate issued with TTL; `commit` → certificate consumed under a commit lock, operations applied, postconditions verified.
**Data Shape:** transaction journal written before, updated after (`committed`/`rolled_back`/`quarantined`); recovery on startup; allowlist = pi.read/grep/find/ls, memory.recall/expand/sessions, state.get/history/complexity, mesh.self/read/members/get/list, compact.status, schema.status/hypothesize/verify/commit/abort.

### Decisive source
```ts
// authorize blocks non-allowlisted mutations (enforce) or reports would-block (audit)
// verify re-snapshots and checks evidence, then issues a certificate with TTL
// commit consumes the certificate under a commit lock, applies operations,
//   verifies postconditions, and writes the transaction journal before/after
```

**Flow:** agent wants to mutate → calls a non-allowlisted ref → `authorize` blocks (enforce) or reports (audit). `hypothesize` stores a typed record in mesh (ifVersion 0). `verify` re-snapshots and checks evidence, issuing a TTL certificate. `commit` consumes the certificate under a commit lock, applies ops, verifies postconditions, writes the journal (committed/rolled_back/quarantined), and recovers on startup. Compaction triggers per-model via `threshold.ts`, renders sectioned summaries within byte budgets (`render.ts`), and `bounds.ts` guarantees UTF-8 safety + provenance-preserving sampling. Delegation resolves actors via `global-registry` (fan-in 25), spawns via transports (process/tmux/tmux/screen/localterm/herdr), and `budget-ledger.ts` tracks spend across the tree.
**Invariant:** a mutation can never land without a certificate issued from a verified hypothesis; a torn transaction is journaled and recovered on startup; atomic writes (`writeJsonAtomic`) survive partial failure.
**Probe:** `tests/approval-controller.test.ts` (authorize blocks/audits non-allowlisted refs), `tests/state-file-preview.test.ts` (workspace snapshot fingerprint), `tests/compaction-threshold.test.ts` (per-model compaction trigger), `tests/memory-integrity.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "SchemaController authorize verify commit journal allowlist", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the schema mutation guard (authorize → hypothesize → verify → commit with journaled recovery) and the full-code executor contract; adapt the allowlist and TTL to host; omit the pi-fabric-specific provider wiring (memory/state/mesh/compact/schema) unless the target runs on pi-fabric.
