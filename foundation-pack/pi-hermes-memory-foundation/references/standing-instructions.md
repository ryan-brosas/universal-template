<!-- capsule-v2 -->
# Standing instructions — always-injected, hard-budgeted user directives with loud truncation

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent persist user-authored rules that must be unconditionally present in every session (regardless of memory mode) — enforcing a hard entry/char budget, injecting them as a fenced directive block, and truncating loudly rather than silently dropping over-budget rules?

## StandingInstructions
**Path/Symbol:** `src/store/standing-instructions.ts:StandingInstructions` (class, 46–224); `load` (60–69), `add` (79–111), `remove` (113–126), `clear` (128–134), `render` (144–182), `formatForSystemPrompt` (184–186), `mutate` (192–210), `write` (213–223). Parsing helpers `parseInstructions` (231–243), `normalizeInstruction` (245–247).
**Signature:** `new StandingInstructions(filePath, maxEntries = STANDING_MAX_ENTRIES, maxChars = STANDING_MAX_CHARS)`; `add(text) → StandingInstructionResult`; `render() → { block, injectedCount, omittedCount }`.
**Data Shape:** one instruction per line in a plain Markdown file (blank lines, `#` comments, and leading `-`/`*` bullets tolerated). `StandingInstructionResult = { success, error?, message?, instructions? }`. The rendered block is a fenced `<standing-instructions>…</standing-instructions>` block stating the rules are direct user instructions that outrank defaults.

### Decisive source
```ts
// add (79-111): scan, dedupe (case-insensitive), enforce entry + char budget
const blocked = scanContent(instruction);
if (blocked) return { success:false, error: blocked };
return this.mutate((current) => {
  if (current.some(e => e.toLowerCase() === instruction.toLowerCase()))
    return { error: "That standing instruction is already pinned." };
  if (current.length >= this.maxEntries)
    return { error: `Standing instructions are capped at ${this.maxEntries} entries...` };
  const projected = [...current, instruction];
  const projectedChars = projected.join("\n").length;
  if (projectedChars > this.maxChars)
    return { error: `Standing instructions are capped at ${this.maxChars} characters...` };
  return { next: projected, message: `Pinned standing instruction ${projected.length}: ${instruction}` };
});

// render (144-182): inject up to budget; state the omission INSIDE the block
const injected = []; let used = 0;
for (const instruction of this.instructions) {
  const cost = instruction.length + 1;
  if (injected.length >= this.maxEntries || used + cost > this.maxChars) break;
  injected.push(instruction); used += cost;
}
const omittedCount = this.instructions.length - injected.length;
// block header: "The user wrote the rules below and they are always active... they outrank your own defaults."
// if omittedCount > 0: append "[!] N further standing instruction(s) could not be shown: <file> exceeds the budget..."
```

**Flow:** (1) `load` reads the file, parsing one instruction per line (deduping case-insensitively). (2) `add` scans the instruction for injection/secrets, dedupes, and enforces the entry and char budgets. (3) `mutate` runs the read-modify-write under `withMarkdownMutationLock` (the same lock the Markdown stores use) so a pin from a second session cannot clobber one from the first, then writes atomically (temp file + rename). (4) `render` injects as many instructions as fit the budget and, if any are omitted (a hand-edited file exceeded the cap), states the omission inside the block itself so both the model and the user can see it.

**Invariant:** standing instructions are always injected regardless of memory mode; provenance is user-only (model-generated memory writes through MemoryStore and never touches this file); the budget is hard and separate from the Markdown stores; over-budget rules are omitted loudly, never silently.

**Probe:** `tests/store/standing-instructions.test.ts` — `treats a hand-edited Markdown file as one instruction per line` (:33), `persists a pinned instruction and reloads it` (:58), `rejects a duplicate regardless of casing` (:70), `refuses content the memory content scanner blocks` (:80), `refuses to exceed the entry cap` (:89), `refuses to exceed the character budget` (:101), `renders a numbered, fenced block that reads as user directive` (:137), `truncates a hand-edited over-budget file loudly rather than silently` (:150). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "StandingInstructions load add render mutate formatForSystemPrompt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the always-injected standing-instruction store, the hard entry/char budget, the loud in-block truncation, the user-only provenance, and the mutation-lock-protected atomic write. Adapt the file path, the budget constants, and the fenced-block wording to the host. Omit the `formatForSystemPrompt` Pi integration and the `/memory-pin` command wiring unless a target has them.
