<!-- capsule-v2 -->
# METRIC line grammar — how does a shell script's stdout become structured metrics without a protocol?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What is the exact line format, which values/names are rejected, and how do duplicates resolve?

## parseMetricLines — anchored multiline regex + denylist + finite filter, last-wins
**Path/Symbol:** `harness/server.ts:138–151` (server copy) + `extensions/pi-autoresearch/src/utils/parse.ts:14–27`; denylist `DENIED_METRIC_NAMES` in both server :85 and `src/constants.ts:13`.
**Signature:** `parseMetricLines(output: string): Map<string, number>`; regex `` ^METRIC\s+([\w.µ]+)=(\S+)\s*$ `` with 'gm'.
**Data Shape:** Map preserving insertion order; primary metric looked up by configured name (`parsedPrimary = parsedMetricMap.get(state.metricName)`), everything else becomes secondary metrics.

### Decisive source
```ts
const regex = new RegExp(`^${METRIC_LINE_PREFIX}\\s+([\\w.µ]+)=(\\S+)\\s*$`, 'gm');
while ((match = regex.exec(output)) !== null) {
  const name = match[1];
  if (DENIED_METRIC_NAMES.has(name)) continue;   // __proto__, constructor, prototype
  const value = Number(match[2]);
  if (Number.isFinite(value)) {                  // rejects Infinity/-Infinity/NaN AND bare words
    metrics.set(name, value);                    // Map.set = LAST occurrence wins
  }
}
```

**Flow:** benchmark output → per-line match (anchored: `METRIC` must start the line) → name charset `[A-Za-z0-9_.µ]` → value token `(\S+)` coerced by `Number()`; non-finite or non-numeric silently drops the line. Duplicate names: last wins (Map overwrite — pinned by test). The parsed map is surfaced to the agent in the run response ("Use these values directly in pi-autoresearch log") so the LLM copies exact numbers instead of re-parsing logs. Unit inference for newly seen secondary names is suffix-based: `inferUnit` maps `*µs→µs, *_ms→ms, *_s|*_sec→s, *_kb→kb, *_mb→mb` else ''.
**Invariant:** the grammar's looseness IS the portability contract — any language/framework can emit metrics with one echo line; nothing but the `METRIC ` prefix and `name=value` shape is required. Prototype-pollution names are rejected BEFORE becoming object keys anywhere downstream. Non-finite values never enter state, so crash rows (metric 0) stay the only zero-ish sentinel.
**Probe:** direct test `__tests__/unit/utils.test.ts:16–119` pins all ten behaviors (basic, empty, malformed, duplicate last-wins :50–58, prototype pollution :60–72, µ/dot/underscore names :74–84, Infinity/NaN rejection :86–98, negatives, decimals); anchors `grep -rl DENIED_METRIC_NAMES harness/server.ts extensions/pi-autoresearch/src/constants.ts extensions/pi-autoresearch/src/utils/parse.ts` → all three source files (constants + two parsers — the test file exercises pollution NAMES without importing the constant).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "parseMetricLines DENIED_METRIC_NAMES inferUnit", limit: 10 });
```

## Verdict
Adopt the regex, denylist, and last-wins semantics verbatim; adapt the prefix constant if the host needs a different namespace; omit pi-specific response formatting. Direct tests are unusually thorough here (10 cases) — keep them green when porting.
