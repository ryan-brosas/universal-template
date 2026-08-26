<!-- capsule-v2 -->
# Responses usage projection — map provider token accounting onto a zero-cost subscription Usage shape

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how do you project provider token usage onto a host usage type without inventing prices and while failing closed to zeros?

## compactUsage / emptyUsage / usageNumber
**Path/Symbol:** src/responses.ts:46-80 (usageNumber 46-49, emptyUsage 51-60, compactUsage 63-80).
**Signature:** usageNumber(record: JsonRecord | undefined, key: string): number; emptyUsage(): Usage; compactUsage(raw: JsonRecord | undefined): Usage.
**Data Shape:** Reads input_tokens, output_tokens, total_tokens from the raw record plus input_tokens_details.{cached_tokens, cache_write_tokens} and output_tokens_details.reasoning_tokens. Every numeric read defaults to 0 unless finite and non-negative. Cost fields are structurally zero.

### Decisive source
~~~ts
function usageNumber(record: JsonRecord | undefined, key: string): number {
  const value = record?.[key]
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : 0
}

function compactUsage(raw: JsonRecord | undefined): Usage {
  if (raw === undefined) return emptyUsage()
  const inputDetails = isRecord(raw['input_tokens_details']) ? raw['input_tokens_details'] : undefined
  const outputDetails = isRecord(raw['output_tokens_details']) ? raw['output_tokens_details'] : undefined
  const inputTokens = usageNumber(raw, 'input_tokens')
  const cacheRead = usageNumber(inputDetails, 'cached_tokens')
  const cacheWrite = usageNumber(inputDetails, 'cache_write_tokens')
  const reasoning = usageNumber(outputDetails, 'reasoning_tokens')
  return {
    input: Math.max(0, inputTokens - cacheRead - cacheWrite),
    output: usageNumber(raw, 'output_tokens'),
    cacheRead, cacheWrite, reasoning,
    totalTokens: usageNumber(raw, 'total_tokens'),
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
  }
}
~~~

**Flow:** raw terminal usage record → guarded numeric reads (non-finite/negative become 0) → cached and cache-write tokens subtract from input with a floor of zero → reasoning tokens projected separately → all cost components stay zero because subscription traffic has no marginal price.
**Invariant:** malformed or hostile usage shapes can only degrade to zeros, never throw or produce negative counts; cost is never estimated; missing details subrecords are tolerated; the projection is pure (no I/O, no time dependence).
**Probe:** tests/response-runtime.spec.ts + tests/codex-compaction.spec.ts fixtures carry usage {input_tokens:20, output_tokens:4, total_tokens:24} through markerStream/compactResponse without cost assertions drifting; executed via pnpm test -- tests/response-runtime.spec.ts tests/codex-compaction.spec.ts.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.responses\\.(compactUsage|emptyUsage|usageNumber)', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt fail-closed-to-zero numeric projection and explicit structural zero costs for any subscription-backed usage mapping. Adapt field names and the host Usage shape. Omit price tables entirely — that is the point. Coverage no_recorded_issue + metadata_match for src/responses.ts; sibling quota parser usage-quota-parsing.md covers the browser-facing rate-limit variant — do not merge them.
