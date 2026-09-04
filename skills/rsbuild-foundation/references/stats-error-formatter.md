<!-- capsule-v2 -->
# Stats error formatter — why does the file line always end with :1:1 and traces reverse to entry→error?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the StatsError→readable-message pipeline: filename resolution ladder, module-trace truncation, hint injection order, and dedupe filter.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/helpers/format.ts` — `formatFileName` 10–44 (data-uri 18–25, :1:1 default 43), `resolveFileName` 46–74 (file || moduleName || last-!-segment of moduleIdentifier), `formatModuleTrace` 85–128 (reverse 111, MAX=4 HEAD/TAIL=2 112–123), hints 130–235, `formatStatsError` 238–288; `helpers/stats.ts` — getStatsErrors/Warnings child-fallback 26–54, stats options dev adds hash+entrypoints 56–103, formatStats level pick 115–148, removeLoaderChainDelimiter 154–160.
**Signature:** `formatStatsError(stats: StatsError, root, level:'error'|'warning', logger): string`.
**Data Shape:** StatsError {message, file?, moduleName?, moduleIdentifier?, loc?, moduleTrace?, details?, stack?}.

### Decisive source
```ts
if (/:\\d+:\\d+/.test(fileName)) return `File: ${color.cyan(fileName)}\\n`;
if (stats.loc) return `File: ${color.cyan(`${fileName}:${stats.loc}`)}\\n`;
// Add default column and lines for linking
return `File: ${color.cyan(`${fileName}:1:1`)}\\n`;   // editors open a clickable location
```
```ts
let trace = moduleNames.slice().reverse();            // stored error → entry; humans read entry → error
const MAX = 4; const HEAD = 2, TAIL = 2;
trace = [...trace.slice(0,HEAD), `... (${trace.length-HEAD-TAIL} hidden)`, ...trace.slice(-TAIL)];
return color.dim(`Import traces (entry → ${level}):\\n  ${trace.join('\\n  ')} ${color.bold(color.red('×'))}`);
```
```ts
const innerError = '-- inner error --';
if (!verbose && message.includes(innerError)) message = message.split(innerError)[0];
message = hintUnknownFiles(message);   // loader-hint → @rsbuild/plugin-{sass,vue,...} swap
message = hintNodePolyfill(message);   // builtin-module resolve fail → plugin-node-polyfill tip
message = hintAssetsConflict(message);
```

**Flow:** verbose mode appends Details/stack and keeps full traces + inner errors; non-verbose strips them. Errors always get traces; warnings only when verbose. Blank-line dedupe filter keeps at most one consecutive empty line. Child-stats fallback exists because some errors surface ONLY on children while parent arrays stay empty.
**Invariant:** (1) trace reversal must happen BEFORE truncation or head/tail windows show wrong ends; (2) LAZY_COMPILATION_IDENTIFIER-prefixed origins are filtered from traces (lazy frames are noise); (3) hint chain runs in fixed order after inner-error strip so replacements see stable text.
**Probe:** unit snapshot coverage via `packages/core/tests/index.test.ts` build-failure fixtures; e2e error-format cases (`cases/diagnostic`, browser-logs). Direct unit suite absent for formatStatsError (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "formatStatsError formatModuleTrace hintNodePolyfill removeLoaderChainDelimiter getStatsErrors", limit: 8 });
```

## Verdict
Adopt the clickable-location default, entry-first truncated traces, ordered hint injection, and child-stats error fallback. Adapt plugin-name hints and colors to host. Omit rslog color internals.
