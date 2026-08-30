<!-- capsule-v2 -->
# agenda-spec-serialization-roundtrip — how does DB→file materialization stay byte-stable under one serializer?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How do you guarantee that rewriting a spec file from DB state produces byte-identical files (so reconcile loops converge) while CAS-guarding concurrent edits?

## One canonical serializer; fixed field order; presence-keyed optionals; hash-CAS updates
**Path/Symbol:** `sdk/packages/core/src/tasks/specs/task-spec-parser.ts` (`serializeAgendaTaskSpec` :434-461; `agendaTaskSpecToCreateInput` :463-494); consumers via `sdk/packages/core/src/tasks/agenda-task-manager.ts` + `tasks/specs/task-spec-file-store.ts`.
**Signature:** `serializeAgendaTaskSpec(input: AgendaTaskSpecWriteInput): string`; `agendaTaskSpecToCreateInput(spec, createdBy): AgendaTaskCreateInput`.
**Data Shape:** Fixed field ORDER: taskId, type, priority (`?? 3`), title, [description], [availableAt], expiresAt, [cwd], resourcePaths (ALWAYS emitted, default `[]`), [assignee], [modelSelection], [mode], [systemPrompt], [maxIterations], [timeoutSeconds], automationEligible (ALWAYS emitted, default true). Optional fields spread only when present. YAML `lineWidth: 0`; body trimmed with trailing `\n`.

### Decisive source
```ts
const yaml = YAML.stringify(frontmatter, { lineWidth: 0 }).trimEnd();
return `---\n${yaml}\n---\n\n${input.instructions.trim()}\n`;
// agendaTaskSpecToCreateInput: availability default is immediately-available
// but never available-after-expiry:
const defaultAvailableAt = new Date(Math.min(Date.now(), expiresAtMs - 1)).toISOString();
```
Live funnel (executed this pass): `trace_path serializeAgendaTaskSpec inbound → callers_total = 6`: AgendaTaskManager.{createTask, ensureScope, reconcileFileStore, reconcileScope, updateTask} + AgendaTaskSpecFileStore.writeSpec — every DB→file materialization goes through ONE serializer, which is why reconcileFileStore's rewrite-back converges to byte-stable files.

**Flow:** manager mutation → serialize (canonical bytes) → file store publish: createOnly uses hard-link so target races fail atomically; conditional updates pass `expectedContentHash` — store re-reads, compares, refuses with "changed before update" on mismatch; temp files never survive (`.tmp` cleanup pinned by test).
**Invariant:** Serialization is canonicalization, not formatting: identical logical state always renders identical bytes regardless of which of the six callers writes, so hash-CAS and disk-vs-DB drift detection are sound.
**Probe:** `grep -cF 'changed before update' sdk/packages/core/src/tasks/specs/task-spec-parser.test.ts` → 1 (:248). Test pins (`task-spec-parser.test.ts`, read whole): "atomically writes and reads a canonical task spec" (+ every dir entry `!entry.endsWith(".tmp")`), "refuses create collisions and stale conditional updates", "does not allow paths outside its managed directory".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.specs.task-spec-parser.serializeAgendaTaskSpec" });
// observed: Function lines 434-461 verbatim; trace_path inbound callers_total=6
```

## Verdict
Adopt single-canonical-serializer funnels with fixed field order + presence-keyed spreads + hash-CAS conditional publishes for any DB↔file mirrored store. Adapt field sets and YAML library. Omit Cline's task schema. Coverage: no_recorded_issue @ gen 2026-08-24T16:12:41Z; suite read whole; runner-BLOCKED honestly (no node_modules).
