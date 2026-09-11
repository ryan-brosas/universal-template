<!-- capsule-v2 -->
# Headline argument picker — how do you render one meaningful line for arbitrary tool calls?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How do captured extension tools and unknown MCP tools get a human-readable preview line without bespoke renderers per tool?

## Headline argument picker
**Path/Symbol:** `src/core/call-preview.ts:headlineArg` (:41–61); key tables :17–28.
**Signature:** `headlineArg(args: Record<string, unknown> | undefined, max = 96): string | undefined`.
**Data Shape:** priority keys in fixed order: task → path → query → message → search → pattern → command → text → prompt → question → input → content → expression → url → topic → key → filter → name → q; skip-set of structural keys (label/title/type/kind/mode/format/limit/max/offset/start/concurrency/overwrite/id/provider/namespace/server/tool/ref/recursive/synthesize/commandDigest).

### Decisive source
```ts
// The final first-string fallback covers tools whose argument names are
// unfamiliar, skipping structural/metadata keys (label/title/mode/limit/...)
// that describe the call rather than its payload.
for (const [key, value] of Object.entries(args)) {
    if (HEADLINE_SKIP_KEYS.has(key)) continue;
    if (typeof value === "string") { const cleaned = cleanOneLine(value, max); if (cleaned) return cleaned; }
}
return undefined;
```

**Flow:** walk the priority list first (preserves the dashboard's historical task→path→query→message preference) → else first string value over remaining entries that isn't a structural/metadata key → collapse all whitespace to single spaces, truncate at max−1 with `…`, return undefined when nothing qualifies.
**Invariant:** Priority order WINS over insertion order (an args object with both query and task shows the task); empty-after-clean values fall through to later candidates; control characters are deliberately NOT stripped here — the inline preview tolerates them and the dashboard sanitizes via safeText at render time (layered defense, documented in-source).
**Probe:** `tests/call-preview.test.ts` ("prefers task over path over query (dashboard order)"); grep -c 'exposes the priority key list' tests/call-preview.test.ts → 1 (the HEADLINE_ARG_KEYS list is itself an exported contract, pinned by test).
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "headlineArg HEADLINE_ARG_KEYS preview argument display", limit: 10 });
// headlineArg Function src/core/call-preview.ts 41-61
```

## Verdict
Adopt the two-tier key-priority-then-skip-list picker for any generic tool-call rendering; adapt the vocabulary lists to your tool surface; omit the fallback tier only when every renderer is bespoke.
