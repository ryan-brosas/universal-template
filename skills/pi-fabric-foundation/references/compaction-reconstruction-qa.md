<!-- capsule-v2 -->
# Compaction reconstruction QA — how do you grade a compaction summary on what it must still answer?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How can compaction quality be measured deterministically, without an LLM judge?

## Compaction reconstruction QA
**Path/Symbol:** `src/compaction/qa.ts:generateProbes/checkProbes/qaReport` (:122–286, :288–302, :304–317).
**Signature:** `generateProbes(events: CompactionEvent[], cutIndex: number): Probe[]`; `qaReport(events, cutIndex, summaryText): QaReport` with `{score, contentScore, addressScore, failures}`.
**Data Shape:** Probe `{id, class: "content"|"address", question, answer}`; probe families = goal (first user message), modified-file per kind (`edit|write`, sampled via `sampleAddressed`), unresolved-error (toolResult/bash errors never later resolved), last-modification path, last fabricRun intent `name → outcome` + `[entry <id>]` address, earlier-turn count+address one-liners, footer-recall `"memory.recall"`.

### Decisive source
```ts
export const checkProbes = (summaryText: string, probes: Probe[]): ProbeCheck => {
  for (const probe of probes) {
    if (summaryText.includes(probe.answer)) {   // substring containment IS the grader
      passed.push(probe);
    } else {
      failed.push({ probe, reason: `summary does not contain expected answer ...` });
```

**Flow:** normalize → project → render produces the summary; `generateProbes` reads ONLY ground-truth events below `cutIndex` (exclusive array boundary — never projections or rendered sections) → each probe's answer must appear verbatim in the summary text.
**Invariant:** Resolution rule for open errors is positional — an error is resolved only by a LATER successful event on the same path/command (`success.index > event.index`, pinned at exactly 2 sites: toolResult arm + bash arm); FILE_TOOLS = {"read","edit","write","grep","find","ls"}, MODIFYING_TOOLS = {"edit","write"} only; large lists grade as ADDRESSED OMISSIONS ("source entries X → Y" ranges) instead of requiring every item inline; identical inputs generate identical probes (deterministic); scores split content vs address so a summary can pass content and still fail addressability.
**Probe:** `tests/compaction-qa.test.ts` ("scores bounded omission ranges instead of requiring every large-list item inline" → failures == [] against real render engine output); grep -c 'fails the unresolved-error probe when Outstanding Context is dropped' tests/compaction-qa.test.ts → 1 (mutation test: dropping the section fails the matching probe).
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "generateProbes qaReport Probe reconstruction summary", limit: 10 });
// generateProbes Function src/compaction/qa.ts 122-286
```

## Verdict
Adopt the ground-truth-only probe generation + substring grading + addressed-omission ranges for any summarization pipeline you need to regression-test without an LLM; adapt probe families to your transcript vocabulary; omit the entry-address format if your logs lack stable ids.
