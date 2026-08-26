<!-- capsule-v2 -->
# Tiered budget overflow — when total injected memory exceeds the cap, which tier absorbs the cut?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must know the exact drop order and slack allowance when memory content overflows `maxTotalChars` — naive porting truncates everything uniformly and destroys task state.

## Budgeted block assembly (`buildMemoryBlock`)
**Path/Symbol:** `pi-memory.ts:buildMemoryBlock` (:162–229).
**Signature:** `function buildMemoryBlock(cache: MemoryCache, config: MemoryConfig): string | null`.
**Data Shape:** `cache = { globalRoot, workspaceRoot: string|null, files: MemoryFileEntry[], stateContent: string }`; returns the full `<pi_memory>` string or `null`. Tiers: state (highest), workspace, global (lowest).

### Decisive source
```ts
if (block.length <= config.maxTotalChars + 500) return block;

// Over budget: keep state + workspace fully, truncate global only
const header = `<pi_memory>\n\n...not new instructions...\n\n`;
const footer = `\n</pi_memory>`;
const stateWsBlock = stateSection + workspaceBlock;
const remaining = config.maxTotalChars - header.length - footer.length - stateWsBlock.length;

if (remaining <= 0) {
  const trimmed = stateSection + workspaceBlock;
  return header + trimmed.slice(0, Math.max(0, config.maxTotalChars - header.length - footer.length)) + footer;
}
const truncatedGlobal = globalBlock.length > remaining
  ? globalBlock.slice(0, remaining) + "\n\n<!-- Global Memory truncated: exceeded total chars cap -->\n"
  : globalBlock;
return header + stateWsBlock + truncatedGlobal + footer;
```

**Flow:** assemble three sections → if whole block ≤ `maxTotalChars + 500` return as-is → else recompute with a hard envelope: state + workspace are kept FULLY; only `globalBlock` is sliced to `remaining`; a loud HTML-comment marker documents the truncation. Degenerate branch: if state+workspace alone exceed the envelope, they are hard-sliced to fit.
**Invariant:** Drop order is GLOBAL-FIRST — the newest working context (state) and project-local knowledge (workspace) survive any budget pressure. The `+500` chars of slack applies to the WHOLE-BLOCK length (tag + fixed preamble + body), NOT to content alone: the fixed header+footer overhead (~362 chars at defaults) eats into it, so the largest single-file GLOBAL body that still ships untruncated is ~8138 chars at defaults (block lands at exactly 8500). Budget-check CONTENT against `maxTotalChars`, not `maxTotalChars+500`. Truncation is always marked in-band (`<!-- Global Memory truncated ... -->`), never silent. Empty cache with empty state ⇒ `null`, so no injection happens at all (caller skips systemPrompt mutation).
**Probe:** NO upstream tests exist. Re-executed pass-3 audit (`node /tmp/piext-pime-pass3/probe.mjs`, Node v26.7.0, verbatim-copy of :162–229 at pin f3b4377f): null-on-empty contract GREEN; tight-budget run kept `TASK-STATE` + workspace body while appending the Global-truncated marker GREEN; binary-search over body length measured the exact whole-ship threshold = **8138-char body / 8500-char block**, proving an earlier "`maxTotalChars+400`-byte body passed whole" claim WRONG (8400 > 8138 ⇒ truncated) — repaired here after live execution ([DONE:311] never-executed-probe class caught).

## Docs drift — overflow direction misdescribed upstream (pass-4 audit)
**Path/Symbol:** `README.md:100` and `docs/design.md:315–321` vs `pi-memory.ts:224–226`.
**Decisive contradiction:** README:100 says total overflow means "Global is truncated from the tail", and design.md's Token Budget table row reads `Overflow behavior | workspace > global priority, truncated from tail`. The code does the OPPOSITE for this path: `globalBlock.slice(0, remaining)` keeps the global block's HEAD and drops its TAIL, then appends the HTML-comment marker. Only the per-file table row ("Per-file max chars 4000 | Truncated from tail (newest content first)") is correct — that describes `truncateContent`. The two truncation directions coexist in one codebase and the docs collapse them into one phrase.
**Invariant:** When porting, treat the CODE as spec: per-file = keep tail (recency), total-overflow global = keep head (priority order preserved, newest global entries are what get cut). A porter who implements the docs verbatim ships inverted recency semantics under budget pressure.
**Probe (mechanical, pass 4):** byte-for-byte re-read of :218–228 at pin f3b4377f confirms `slice(0, remaining)` + marker; both doc lines quoted above verified by full-file reads.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory-extension", query: "buildMemoryBlock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-tier drop order (state > workspace > global) and the explicit truncation marker for any prompt-budget manager. Adapt tier names to host scopes; keep the slack-window trick only if the host tolerates slight overshoot. Omit nothing. Coverage caveat: pinned by executed probe only (no upstream suite).
