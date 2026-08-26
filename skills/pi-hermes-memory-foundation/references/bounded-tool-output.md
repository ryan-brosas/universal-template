<!-- capsule-v2 -->
# Bounded tool output budgeting — per-snippet caps with loud truncation markers, hard output ceiling, and clamped numeric params

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How do you stop a single search result set from flooding the model's context — while telling the model EXACTLY how much was cut and which knob raises it?

## registerSessionSearchTool (legacy variant)
**Path/Symbol:** `src/tools/session-search-tool.ts:registerLegacySessionSearchTool` (:146–246); constants (:31–33): `DEFAULT_LEGACY_SNIPPET_CHARS = 1_200`, `MAX_LEGACY_SNIPPET_CHARS = 4_000`, `MAX_LEGACY_OUTPUT_CHARS = 50 * 1024`; `truncateLegacySnippet` (:35–41), `capLegacyOutput` (:43–50); variant dispatcher (:52–64); anchor-mode twin `formatAnchorSearchOutput`/`compactReason` (:126–144).
**Signature:** `registerSessionSearchTool(pi, dbManager, sessionSearchConfig = { variant: "legacy" }, options?)`; legacy params `{query, project?, role?, limit? (1–20), snippetChars? (100–4000)}`.
**Data Shape:** details carry the audit trail: `{success, count, truncatedCount, snippetChars, outputChars, outputTruncated}`; anchors mode returns plain-text `path:startLine-endLine — reason` lines instead of snippets.

### Decisive source
```ts
function truncateLegacySnippet(text: string, maxChars: number) {
  if (text.length <= maxChars) return { text, truncated: false };
  return {
    text: `${text.slice(0, maxChars)}\n... (truncated, ${text.length} chars total — refine the query or increase snippetChars)`,
    truncated: true,                       // ← marker states TOTAL SIZE + REMEDY
  };
}

function capLegacyOutput(text: string) {
  if (text.length <= MAX_LEGACY_OUTPUT_CHARS) return { text, truncated: false };
  const suffix = `\n... (output truncated, ${text.length} chars total — refine the query or lower the result limit)`;
  return { text: `${text.slice(0, MAX_LEGACY_OUTPUT_CHARS - suffix.length)}${suffix}`, truncated: true };
  //                          ^ reserve room for the suffix so the cap is EXACT
}

// Numeric args are clamped, never trusted:
const requestedLimit = Number.isFinite(args.limit) ? Math.floor(args.limit!) : 10;
const limit = Math.min(Math.max(requestedLimit, 1), 20);
const snippetChars = Math.min(Math.max(requestedSnippetChars, 100), MAX_LEGACY_SNIPPET_CHARS);

// Empty index gets a REMEDY message naming the import command:
if (totalMessages === 0) … message: 'No sessions indexed yet. Run /memory-index-sessions to import past sessions.'
```

**Flow:** (1) config selects the variant ONCE at registration (`anchors` replaces the whole registration, same tool name); (2) legacy path validates query, checks indexed count, searches, then budgets: per-result snippet truncation first (counting victims in `truncatedCount`), whole-output cap second with suffix-reserving slice; (3) anchor mode returns line-range pointers (reason compacted to ≤180 chars) so raw transcript never enters context.
**Invariant:** every truncation is LOUD and actionable — total original size plus the specific parameter to adjust; caps are enforced on the FINAL assembled string, not just per piece; the two-level budget (snippet vs output) lets one huge message degrade alone while small results stay intact. The suffix-reservation makes the advertised cap byte-accurate. Anchors-vs-snippets is an information-density decision: point AT data instead of copying it when the consumer can read files.
**Probe:** `tests/tools/session-search-tool.test.ts` — asserts clamp bounds, truncation marker text carrying totals, output-cap exactness, zero-state remedy messages, and variant dispatch by config. Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "capLegacyOutput truncateLegacySnippet registerSessionSearchTool searchSessionAnchors", limit: 5 })`

## Verdict
Adopt for any tool that copies external text into model context. Adapt cap values and remedy command names. Pair with `session-anchor-search.md` (the anchor engine behind variant #2).
