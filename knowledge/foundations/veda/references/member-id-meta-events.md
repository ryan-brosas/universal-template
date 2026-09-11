<!-- capsule-v2 -->
# Member identity in pipeline events — how do you let notifications/UI name "who did what" without parsing string IDs?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A multi-member LLM pipeline (solvers, judges, verifiers, revision) emits streaming events. Consumers (desktop notifications, terminal rendering) need to display which member produced each event. How is member identity carried so no consumer ever has to parse an ID string?

## formatMemberId + MemberMeta side channel
**Path/Symbol:** `src/pipelines/deep-think.ts`: `MemberIdParts` (:48-58), `MemberMeta` (:60-67), `formatMemberId` (:69-72); usage sites: `buildSolverMembers` (:794-810), judge tool events (:1271-1285), verifier per-check handler factory (:1713-1730), revision onMessage (:1832-1845).
**Signature:** `formatMemberId(parts: MemberIdParts): string` → `` `${type}-${index}-${backend}-${model}-${module}` ``; `MemberMeta {type, backend, model, index, module, id}` where `id` is the canonical formatted string.
**Data Shape:** type vocabulary is CLOSED at `'solver' | 'judge' | 'verifier'`; module slot holds `category/module_id`, `'uniform/none'`, `'multi'`, `'NA'`, the verification type (`'factual'|'code'|'reasoning'`), or `'revision'`.

### Decisive source
```ts
/**
 * Standardized member metadata attached to events.
 * Notifications and tool events use this instead of parsing IDs.
 */
interface MemberMeta {
  type: 'solver' | 'judge' | 'verifier';
  backend: string;
  model: string;
  index: number;
  module: string;
  id: string;  // Canonical formatted ID
}

function formatMemberId(parts: MemberIdParts): string {
  const { type, index, backend, model, module } = parts;
  return `${type}-${index}-${backend}-${model}-${module}`;
}
```
Revision deliberately borrows the verifier type for display consistency:
```ts
const revisionId = formatMemberId({
  type: 'verifier',  // Use 'verifier' type for consistent display
  backend: revision.backend,
  model: revision.model ?? 'unknown',
  index: 0,
  module: 'revision',
});
```

**Flow:** solver members get their meta once in `buildSolverMembers` (module = `category/module_id` or `'uniform/none'`) and are looked up per event via `solverMetaMap.get(event.memberId)` (:1096) → judge and verifier events SYNTHESIZE meta inline at emission time (judges: `module: effectiveMode === 'multi' ? 'multi' : 'NA'`, index always 0; verifiers: a per-check handler FACTORY captures `{index, check}` in closure — the comment says this fixes the race where parallel checks interleave events) → every event that names a member carries `member: MemberMeta` alongside its own fields; the string id exists only as a display/lookup key.
**Invariant:** The ID is a display string, NEVER a parse target — any consumer that splits it on `-` breaks on model ids containing dashes or colons; structured meta is the single source of truth for notifications/UI; the type vocabulary stays closed at three values (revision borrows `'verifier'` + `module:'revision'` rather than adding a fourth type), so display code handles exactly three shapes.
**Probe:** NO dedicated upstream test — grep over `tests/` for `formatMemberId`/`MemberMeta` returns zero references (verified pass 8). Source-pinned probe: `grep -n "formatMemberId" src/pipelines/deep-think.ts` → definition :69 + exactly four call sites (:794 solver, :1271 judge, :1715 verifier, :1832 revision). Adjacent behavioral evidence: `tests/commands/trace-format-e2e.test.ts` pins the rendered `[solver-N:backend:model:module]` label contract downstream — EXECUTED pass 8: 9 pass / 0 fail.
**Coverage caveat:** the meta side channel itself is exercised only indirectly through the full generator, which has no end-to-end test (standing caveat from deep-think-stage-machine.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "formatMemberId MemberMeta makeToolEvent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual representation (canonical display id + structured meta attached to every event) and the closed three-type vocabulary with borrowed-type display reuse for sub-stages. Adapt the id grammar to your member shapes. Omit the side channel entirely if you have no notification/rendering plane — then the id alone suffices.
