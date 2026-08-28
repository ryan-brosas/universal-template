<!-- capsule-v2 -->
# Usage stats rendering — how do you display token usage without leaking it into the stdout payload?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** Where does token usage get rendered, in which channel, and what happens to the richer usage fields a backend may report?

## One 9-line renderer, stderr-only, two-counter display contract
**Path/Symbol:** `src/util/format.ts:formatUsageStats` (:3-9, whole file); call sites `src/commands/run.ts:279` and `src/commands/resume.ts:140` (both `console.error`); type `src/backend/types.ts:UsageStats` (:14-19); re-exported by `src/util/index.ts:22`.
**Signature:** `formatUsageStats(usage?: UsageStats | null): string`.
**Data Shape:** `UsageStats = { inputTokens: number; outputTokens: number; cachedTokens?: number; costUsd?: number }`. Output: `` `Tokens: ${inputTokens} in, ${outputTokens} out` `` or the sentinel `'Tokens: ?'` when usage is null/undefined.

### Decisive source
```ts
export function formatUsageStats(usage?: UsageStats | null): string {
  if (!usage) {
    return 'Tokens: ?';
  }

  return `Tokens: ${usage.inputTokens} in, ${usage.outputTokens} out`;
}
```
**Flow:** backend response carries optional `usage` → the command handler reaches the renderer only inside the file-output arm (`run.ts:278-280`: after `Response saved to <path>`, when `response.usage` is truthy) → the line goes to **stderr**, never stdout (run.ts:279, resume.ts:140 are the only call sites, both `console.error`). The JSON arm bypasses the renderer entirely and embeds the whole `usage` object into the stdout payload (`run.ts:283-286`), so `cachedTokens`/`costUsd` survive machine consumption but are dropped by the human text arm.
**Invariant:** usage is diagnostics — it never appears on stdout in text mode, keeping the two-channel discipline (stdout = payload only, per run-protocol-exit-contract.md). The display contract is exactly the two-counter pair: `cachedTokens` and `costUsd` are silently omitted from the text rendering even when present. A missing usage renders the `Tokens: ?` placeholder rather than being skipped, so the line's presence is stable when the file-output arm runs.
**Probe:** no dedicated upstream test exists (grep-verified: no test file references `formatUsageStats` or the `Tokens:` literal; the function is exercised only transitively by suites that build usage objects). Source-pinned probe executed byte-for-byte at pin: `grep -n "formatUsageStats" src/util/format.ts` → `3:export function formatUsageStats(usage?: UsageStats | null): string {`; `grep -rn "console.error(formatUsageStats" src/` → run.ts:279, resume.ts:140.
**Coverage caveat:** no-dedicated-test caveat per the pass-5 precedent; the renderer is trivial enough that the source excerpt is the full contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "formatUsageStats Tokens inputTokens outputTokens stderr usage rendering", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the channel rule (usage lines to stderr, full usage object only in the machine payload) and the placeholder sentinel for missing usage. Adapt the literal format and which optional fields the text arm shows to your host. Omit the separate renderer if your host has no text/JSON dual arm — but keep usage out of the stdout payload either way.
