<!-- capsule-v2 -->
# Worker-report gate — exactly-one tag-pair protocol with lenient field parsing and honest degradation

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How do I parse a structured handoff block out of an LLM's final message so protocol violations fail loudly while field-level sloppiness degrades gracefully?

## Count-first structural gate, then per-field warnings
**Path/Symbol:** `src/util/report-parse.ts:parseWorkerReport` (:182–334).
**Signature:** `function parseWorkerReport(response: string): WorkerReportParseResult` — discriminated union `{ ok: true; block; report; warnings[] } | { ok: false; reason: 'no-block'|'malformed'; detail?; tail }`.
**Data Shape:** `<worker_report>` block with camelCase-mapped Factory fields: status(completed|failed|blocked), salient_summary, what_was_implemented, what_was_left_undone, verification(command ran/exit attrs + evidence tool/surface attrs), tests, discovered_issues(issue severity attr), needs.

### Decisive source
```ts
// Invariant: exactly one <worker_report> opening tag and one closing tag.
// Count them across the whole response first — the lenient extraction regex
// cannot distinguish nested/stray openers, so a count mismatch must fail.
const openTags  = (response.match(/<worker_report\b/gi) ?? []).length;
const closeTags = (response.match(/<\/worker_report\s*>/gi) ?? []).length;
if (openTags === 0 && closeTags === 0) return { ok: false, reason: 'no-block', tail: lastLines(response, 40) };
if (openTags !== 1 || closeTags !== 1) return { ok: false, reason: 'malformed', ... };

// Invariant: nothing may follow the block.
const afterIndex = (last.index ?? 0) + block.length;
if (response.slice(afterIndex).trim().length > 0)
  return { ok: false, reason: 'malformed', detail: 'content follows the <worker_report> block...', tail: ... };

// Strict integer shape only — parseInt would accept '1oops'/'1.5'.
if (/^-?\d+$/.test(trimmed)) exit = parseInt(trimmed, 10);
else warnings.push(`verification <command> has invalid exit value "${exitRaw}"`);
```

**Flow:** count open/close tags over the WHOLE response (0/0 → no-block; ≠1/≠1 → malformed — catches nested and stray openers the lazy regex can't see) → extract single block → trailing-content check → parse fields leniently: missing required fields and unknown enum values become WARNINGS while parsing continues (`status` falls back to `'failed'`; invalid evidence tools/severities are preserved verbatim plus warning; blocked-without-needs warns). Every failure carries a 40-line response tail for stderr diagnosis. Pure module — persistence lives in run.ts.
**Invariant:** Structure is strict, content is lenient: exactly-one-block + nothing-after are HARD failures (the runner exits non-zero), while every field-level defect is recoverable. Exit attributes accept only `/^-?\d+$/` — `parseInt`-style coercion is explicitly called out as wrong in-source.
**Probe:** `tests/util/report-parse.test.ts` (:123–309) — ladder pins `multiple blocks are a protocol failure`, `nested/stray opening tag is a protocol failure`, `prose after the block is a protocol failure`, `partially numeric exit values are rejected, not coerced`, `unknown evidence tool → warning, value preserved`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "parseWorkerReport worker_report malformed warnings", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the count-first gate, nothing-after invariant, and warning-not-throw field policy for any LLM-produced structured artifact. Adapt the field vocabulary to your own handoff contract. Omit the Factory-specific fields only if your driver never branches on them.
