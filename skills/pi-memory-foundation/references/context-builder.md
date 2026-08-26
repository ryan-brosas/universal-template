<!-- capsule-v2 -->
# Context builder — priority-ordered, per-section-capped memory context for injection

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent assemble the injected memory context from scratchpad, daily logs, search results, and long-term memory in a stable priority order, each within its own char/line cap and an overall cap?

## Context builder
**Path/Symbol:** `index.ts:buildMemoryContext` (780–869).
**Signature:** `buildMemoryContext(searchResults?: string): string`.
**Data Shape:** Sections appended in priority order: scratchpad (open items only, `start`, 2000/120) → today's daily (`end`, 3000/120) → search results (`start`, 2500/80) → MEMORY.md (`middle`, 4000/150) → yesterday's daily (`end`, 3000/120). Overall `CONTEXT_MAX_CHARS = 16_000`. Returns `""` when no section has content; else a `# Memory\n\n<section>---<section>` block.

### Decisive source
```ts
// Priority order (782): scratchpad > today's daily > search > MEMORY.md > yesterday
const sections: string[] = [];
const scratchpad = readFileSafe(SCRATCHPAD_FILE);
if (scratchpad?.trim()) {
  const openItems = parseScratchpad(scratchpad).filter((i) => !i.done);
  if (openItems.length > 0) sections.push(formatContextSection("## SCRATCHPAD.md (working context)", serializeScratchpad(openItems), "start", CONTEXT_SCRATCHPAD_MAX_LINES, CONTEXT_SCRATCHPAD_MAX_CHARS));
}
// ... today, searchResults, longTerm (mode "middle"), yesterday ...
if (sections.length === 0) return "";

const context = `# Memory\n\n${sections.join("\n\n---\n\n")}`;
if (context.length > CONTEXT_MAX_CHARS) {
  const result = buildPreview(context, { maxLines: Number.POSITIVE_INFINITY, maxChars: CONTEXT_MAX_CHARS, mode: "start" });
  const note = result.truncated ? `\n\n[truncated overall context: showing ${result.previewChars}/${result.totalChars} chars]` : "";
  return `${result.preview}${note}`;
}
return context;
```

**Flow:** (1) `ensureDirs()` guarantees the layout exists. (2) Each section is built only if its source file has non-empty content, so absent files contribute nothing. (3) Sections join with `---` separators under a `# Memory` header. (4) If the joined context exceeds 16K, it is truncated `start`-mode with an honest overall note.

**Invariant:** the priority order is stable (working context first, durable facts last); a missing/empty source contributes zero bytes; the final string never exceeds `CONTEXT_MAX_CHARS`; truncation is always reported.

**Probe:** `test/unit.test.ts` — `buildMemoryContext` describe (:551) verifies section ordering, per-section caps, and the overall 16K cap with the `[truncated overall context]` note; `before_agent_start injects memory into system prompt` (:1382) and `includes usage instructions` (:1392) in the `lifecycle hooks` describe. Coverage caveat: `test/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "buildMemoryContext formatContextSection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the priority-ordered context assembly, the per-section caps, the empty-section suppression, and the overall 16K cap with an honest note. Adapt the section labels, caps, and file names to the host. Omit nothing here — this is the portable context-builder core.
