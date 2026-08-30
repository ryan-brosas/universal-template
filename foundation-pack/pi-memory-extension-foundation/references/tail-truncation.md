<!-- capsule-v2 -->
# Tail truncation — when a memory file exceeds its injection budget, which half survives?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must decide whether over-budget memory content drops its head or its tail — the wrong choice silently hides the newest knowledge.

## Truncate-tail primitive (`truncateContent`)
**Path/Symbol:** `pi-memory.ts:truncateContent` (:113–116).
**Signature:** `function truncateContent(content: string, maxChars: number): string`.
**Data Shape:** Input raw file text; output either the untouched original (`content.length <= maxChars`) or a marker line prepended to exactly the LAST `maxChars` characters.

### Decisive source
```ts
function truncateContent(content: string, maxChars: number): string {
  if (content.length <= maxChars) return content;
  return "... [truncated, tail retained]\n" + content.slice(-maxChars);
}
```

**Flow:** length check → under budget = byte-identical passthrough → over budget = prepend literal marker `... [truncated, tail retained]\n` then keep only `slice(-maxChars)` (the tail).
**Invariant:** NEWEST content wins. Markdown memory files append chronologically, so the tail carries the latest decisions/lessons; the head (oldest entries) is what gets dropped. Output length ≤ `maxChars + len(marker)` always.
**Probe:** NO upstream test suite exists at HEAD (repo ships zero test files). Deterministic probe executed this run against shipped source bytes on Node v26.7.0 (`node /tmp/pime-probe/probe.mts`, ALL GREEN ×13): tail kept (`TAIL-NEWEST-2026` present), head dropped (`HEADER-STALE` absent), marker prepended, short content returned untouched.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory-extension", query: "truncateContent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt truncate-from-head/keep-tail semantics plus the loud truncation marker for any appended-log-shaped memory store. Adapt the marker text to host conventions if needed (it is user-visible inside prompts). Omit nothing — the function is dependency-free and total. Coverage caveat: pinned by this run's executed probe only, not by an upstream direct test.
