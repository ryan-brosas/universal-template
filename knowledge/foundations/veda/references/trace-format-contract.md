<!-- capsule-v2 -->
# Trace format contract — how do you build a truncation primitive that never exceeds its budget, and a streaming display whose symbols stay consistent?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A deep-run streams phase headers, solver tool events, candidate content, and token summaries to a terminal. What are the truncation, numbering, and symbol contracts a reimplementation must preserve?

## One symbol table, one truncation primitive, 1-based display over 0-based indices
**Path/Symbol:** `src/util/trace-format.ts` (whole, 408L): `FORMAT_CONFIG` (:13-24), `truncateWithCount` (:131-145), `formatToolStart` (:147-166), `formatSolverToolEvent`/`formatSolverComplete` (:76-102), `formatJudgeReasoning` (:226-229), `humanizeTokens` (:253-267), `formatCompletionStatus` (:295-303), `formatTraceParsingGuide` (:377-400); direct tests `tests/util/trace-format.test.ts` (whole) + `tests/commands/trace-format-e2e.test.ts` (whole).
**Signature:** `truncateWithCount(text: string, maxLength = FORMAT_CONFIG.truncateAt) → string`; `formatSolverToolEvent(solverIndex: number, backend, model, module, toolName, toolInput?) → string`; `humanizeTokens(count: number) → string`.
**Data Shape:** `FORMAT_CONFIG { lineWidth: 80, truncateAt: 60, symbols: { phase: '▸', done: '✓', arrow: '→', ellipsis: '···', separator: '─', doubleSeparator: '═' } }`; `FormatterState { phase, candidateCount, judgeMode?, judgeBackends? }`.

### Decisive source
```ts
export function truncateWithCount(
  text: string,
  maxLength: number = FORMAT_CONFIG.truncateAt
): string {
  if (text.length <= maxLength) return text;

  const { symbols } = FORMAT_CONFIG;
  // Reserve space for "···[+NNN]" suffix (worst case ~10 chars)
  const reservedSpace = 10;
  const visibleLength = Math.max(0, maxLength - reservedSpace);
  const hidden = text.length - visibleLength;

  return `${text.slice(0, visibleLength)}${symbols.ellipsis}[+${hidden}]`;
}
```
```ts
export function formatSolverToolEvent(
  solverIndex: number, backend: string, model: string,
  module: string, toolName: string, toolInput?: unknown
): string {
  const { symbols } = FORMAT_CONFIG;
  const toolContent = formatToolStart(toolName, toolInput);
  const safeModule = module?.trim() ? module : 'unknown';
  return c.dim(`  [solver-${solverIndex + 1}:${backend}:${model}:${safeModule}] ${symbols.arrow} ${toolContent}`);
}
```
**Flow:** every renderer pulls symbols from the single `FORMAT_CONFIG` table (never inline literals) → tool events render `[solver-N:backend:model:module] → tool` with the index +1 (0-based internally, 1-based for users) and blank modules coerced to 'unknown' → `formatToolStart` extracts shell/bash `command` fields for truncation, collapses `file_change` to a fixed label, passes `mcp:*` names through raw, and returns unknown tool names verbatim → judge reasoning is NEVER truncated (full reasoning displayed) while candidate content is truncated at 200 and whitespace-normalized to one line → token counts humanize (941→"941", 236236→"236K", 1500000→"1.5M") → completion renders `✓ complete | solve → judge → verify | 90% confidence | revised` with the revised flag omitted when false.
**Invariant:** `truncateWithCount` output NEVER exceeds `maxLength` (the 10-char reservation covers the worst-case `···[+NNN]` suffix; test pins `result.length ≤ 50` for maxLength 50). Solver indices are always displayed +1. The e2e suite pins the full streaming sequence — phase header before work, per-solver tool events, completion summaries without tool chains, `#N` candidate separators, selection with confidence — as the display contract.
**Probe:** `tests/util/trace-format.test.ts` + `tests/commands/trace-format-e2e.test.ts` (executed live at pin: 45 pass / 0 fail combined) pin truncation bounds, 1-based numbering, symbol consistency, width-exact phase headers (80 chars after ANSI strip), token humanization, and the full pipeline output shape.
**Coverage caveat:** `formatTraceParsingGuide` (the yq recipe for trace.yaml) has no dedicated test — source-pinned; it is the machine-consumption half of the contract (`.final.answer`, `.run.was_revised`, `.judge.selected_index` paths).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "FORMAT_CONFIG truncateWithCount formatSolverToolEvent humanizeTokens formatCompletionStatus formatTraceParsingGuide", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single symbol table, the budget-respecting truncation primitive, 1-based display over 0-based indices, and never-truncate judge reasoning. Adapt the symbol set, line width (80), truncate-at (60), and token suffixes to your terminal culture. Omit the parsing guide only if your trace format has no machine consumers.
