<!-- capsule-v2 -->
# Compaction normalization contract — how do you turn raw session entries into a typed event stream that summaries can trust without ever reading prose or leaking thinking?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what exactly does normalizeEntries extract, how are tool results paired to calls, and what is the thinking-erasure accounting contract?

## Structural-only extraction: 1-based indices, id-paired results, branch-fact replay, erased-thinking counter
**Path/Symbol:** `src/compaction/normalize.ts` whole (:1-510): event union `CompactionEvent` (:106-115), `boundedJsonValue` sanitizer (:131-164) with bounds :120-124, `isPiCustomMessageEntry` (:188-204), `normalizeEntries` (:254-486), `countErasedThinkingBlocks` (:493-508), `firstLine` (:218-222). Consumers: `src/compaction/projections.ts`, `src/compaction/branch-summary.ts`, `src/compaction/qa.ts` (all import from here). Direct tests `tests/compaction.test.ts` + `tests/compaction-qa.test.ts`.
**Signature:** `normalizeEntries(entries: SessionEntry[]): CompactionEvent[]`; `countErasedThinkingBlocks(entries): number`; each event carries `{index (1-based, stable, drives brief-transcript "(#N)" refs), entryId (stable fact id), sourceEntryId (entry that carried it)}`.
**Data Shape:** nine kinds — user / assistantText / customMessage / toolCall / toolResult / bash / fabricPhase / fabricRun / fabricOperation; custom-details sanitizer bounds: depth ≤12, nodes ≤256, collections ≤64, strings ≤1024 bytes, total ≤8KB; ANY unrepresentable member ⇒ whole details dropped (`undefined`).

### Decisive source
```ts
// Header comment :12-23 — the two governing principles:
// Normalization extracts ONLY typed structure — roles, tool names, JSON
// arguments, isError flags, bash commands and exit codes. It never inspects
// prose. Assistant thinking parts are deliberate scratchpad, not commitments:
// they are never normalized into events.

for (const entry of entries) {
  if (entry.type === "branch_summary") { pushBranchFacts(entry); continue; }  // replay facts
  ...
  if (part.type === "toolCall" && ...) { calls.set(part.id, {entryId, name, args}); push(...); }
  if (role === "toolResult") {
    const pending = toolCallId ? calls.get(toolCallId) : undefined;   // STRUCTURAL pairing
    if (toolName === "bash") { const command = pending && typeof pending.args.command === "string"
        ? pending.args.command : ""; push({ kind:"bash", ..., exitCode: null }); }
    if (toolName === "fabric_exec") { /* fabricRun w/ subordinal `call:<id>`,
        outcome: nested?.outcome ?? (isError ? "failed" : "succeeded"),
        then nested phases `phase:<i>` + operations */ }
  }
}
// countErasedThinkingBlocks mirrors normalizeEntries' walk EXACTLY so the
// details counter cannot disagree with what the summary silently dropped (:488-492)
```

**Flow:** caller selects the cumulative raw active-branch prefix BEFORE the kept boundary → branch_summary entries are flattened back into first-class facts (so compaction-of-compaction preserves history) → assistant toolCall parts register into a pending-call map keyed by toolCallId → toolResult entries look up their call structurally (id match, NEVER prose similarity) so bash events carry the originating command; bashExecution message role derives isError as `exitCode !== null && exitCode !== 0` while tool-result bash pins `exitCode: null` for later enrichment → fabric_exec results expand their embedded projection trace into run/phase/operation events with deterministic subordinals (`call:<id>`, `phase:<i>`) and composite addresses `<entryId>/<subordinal>` → malformed custom_message entries are skipped per-entry inside try/catch without poisoning the stream (:343-345).
**Invariant:** thinking parts are never events — erasure stays auditable ONLY through `countErasedThinkingBlocks`, whose walk must mirror the selector (a porter adding a new event kind must update both); pairing state lives only within one normalize pass (map is per-invocation).
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pi-ecosystem/pi-fabric && grep -n "It never inspects prose" src/compaction/normalize.ts'` → line 17; `grep -n "calls.set(part.id" src/compaction/normalize.ts` → 368; `grep -n "const pending = toolCallId ? calls.get(toolCallId) : undefined" src/compaction/normalize.ts` → 387; `grep -c "export const countErasedThinkingBlocks" src/compaction/normalize.ts` → 1 (the mirrored counter, :493); `grep -c 'pushBranchFacts' src/compaction/normalize.ts` → 2; tests: `grep -rn "normalizeEntries" tests/compaction.test.ts | head -3` resolves direct coverage (graph rank #2/#3 name tests.compaction.test.toolResult / compaction-qa).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "normalizeEntries compaction event stream toolResult pairing", limit: 10, fields: ["signature", "name", "file"] });
```
(Rank #1 resolves `normalizeEntries` src/compaction/normalize.ts 254-486.)

## Verdict
Adopt structural-only normalization with stable 1-based indices, id-keyed result pairing, branch-fact flattening, and the mirrored erased-thinking counter for any summarizer built over raw session logs; adapt the kind taxonomy to your entry schema; omit the fabric_* expansion when your host has no nested execution trace. Coverage caveat: pairing/fabric expansion legs are exercised via compaction integration tests, not a dedicated unit file.
