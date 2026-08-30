<!-- capsule-v2 -->
# Compaction summary renderer — how do you render fixed-section bounded summaries where EVERY section fits its byte cap and the whole summary never exceeds the global budget?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** given projected section lines (goal/files/activity/outstanding/turns/status), how do you guarantee per-section AND whole-document UTF-8 byte bounds while keeping the most informative lines under truncation pressure?

## Section ladder with earliest+latest line sampling and a final global clip
**Path/Symbol:** `src/compaction/render.ts` whole file (82L): `SECTION_ORDER` (:4-11), byte caps (:13-17), `POINTER_LINE` (:27-28), `sampledLines` (:30-39), `boundedBlock` (:41-50), `renderSummary` (:52-82); `src/compaction/bounds.ts` (`MAX_SUMMARY_BYTES` :1, `clipUtf8` :8-20, `utf8Bytes` :3-5). Consumers: `src/compaction/hook.ts:29`, `src/compaction/branch-summary.ts:19`. Direct tests `tests/compaction-qa.test.ts:106,209` (real-engine fixtures).
**Signature:** `renderSummary(sections: Sections, options: RenderOptions): string`; `RenderOptions = {firstEntryId, lastEntryId, lastTimestamp, requestLines?, summaryKind?: "compaction"|"branch"}`; `boundedBlock(header, sourceLines, maxBytes): string`.

### Decisive source
```ts
// earliest ceil(keep/2) + latest floor(keep/2) sampling with an addressed gap
const sampledLines = (lines, keep) => {
  if (lines.length <= keep) return [...lines];
  const earliest = Math.ceil(keep / 2);
  const latest = Math.floor(keep / 2);
  return [...lines.slice(0, earliest),
    `… omitted ${lines.length - keep} rendered lines`,
    ...lines.slice(lines.length - latest)];
};
// fit loop: try full length, then shrink one line at a time to ZERO
for (let keep = capped.length; keep >= 0; keep--) {
  const lines = sampledLines(capped, keep);
  const block = [header, ...lines].join("\n");
  if (utf8Bytes(block) <= maxBytes) return block;
}
return clipUtf8(header, maxBytes);   // even the header alone is clipped to cap
```

**Flow:** for each of the six sections in FIXED order (`[Session Goal]` 4096B → `[Files And Changes]` 4608B → `[Fabric Activity]` 2048B → `[Outstanding Context]` 4608B → `[Earlier Turns]` 3072B → `[Current Status]` 2048B): skip empty sections, clip each line to 1024B (`MAX_RENDERED_LINE_BYTES`) BEFORE sampling, cap input at 128 lines (`MAX_INPUT_LINES_PER_SECTION`), then run the keep-shrinking loop until the joined block fits its per-section budget. The `[Compaction Request]` block (3072B) renders right after `[Session Goal]`, or UNSHIFTED FIRST when goal was empty (:62-64). Transcript renders last as a bare `---` block (5120B), then the footer `---` block (1536B): `` `[compacted ${timestamp}; cumulative source entries ${range}]` `` or the branch variant `[branch summarized …; structural source entries …]` (:74-76) plus the memory.recall POINTER_LINE. Final safety net: if the whole summary exceeds `MAX_SUMMARY_BYTES` (32 KiB), hard-clip to 32KiB−1 bytes and re-append `\n`.
**Invariant:** every rendered block individually respects its byte cap (the loop's terminal case clips the header alone), so a section can never blow the global budget by itself; omission markers are ADDRESSED (`omitted N rendered lines`) matching the compaction-reconstruction-QA probe grammar (test :215 pins `summary).toContain("omitted 24 file addresses")` produced upstream by projections, same convention); empty sections contribute NOTHING — not even their header; footer vocabulary differs between compaction and branch kinds but shares the entry-range address.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pi-ecosystem/pi-fabric && grep -n "MAX_INPUT_LINES_PER_SECTION = " src/compaction/render.ts | wc -l'` → 1 (:16); `grep -n "omitted .* rendered lines" src/compaction/render.ts | wc -l` → 1 (:36); `grep -n 'summaryKind === "branch"' src/compaction/render.ts | wc -l` → 1 (:74); `grep -c "boundedBlock(" src/compaction/render.ts` → 5 call sites; `grep -c clipUtf8 src/compaction/render.ts` → 4; tests: `tests/compaction-qa.test.ts:215` expects `"omitted 24 file addresses"` + `:216` `"omitted 16 earlier turns"` against the real normalize→project→render engine.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "renderSummary compaction summary render sections bounded", limit: 5, fields: ["signature", "name", "file"] });
```
(Rank #1 resolves `renderSummary` :52-82 and rank #3 `boundedBlock` :41-50 line-exact.)

## Verdict
Adopt per-section byte budgets with line-level pre-clipping, earliest+latest sampling with addressed omissions, and the final whole-document clip for any fixed-section summarizer; adapt the section roster/caps to your domain; omit the compaction-request unshift special case if you have no model-initiated compaction channel. Direct-test coverage via the QA suite exercising the real engine — no coverage caveat.
