<!-- capsule-v2 -->
# Browser-log stack symbolication — why is the first user frame the only one mapped, and when do runtime frames survive?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce summary/full/none formatting tiers, TraceMap caching, root-relative path math, and runtime-frame filtering.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/browserLogs.ts` — `isValidMethodName` 16–18, `isRspackRuntimeStack` 20–26, `findFirstUserFrame` 33–41, `parseFrame` 46–86 (CachedTraceMap 71–77), `resolveOriginalLocation` 92–114, `resolveSourceRelativeToRoot` 120–134, `formatFullStack` 176–239 (filter gate 231–233), `formatBrowserErrorLog` 245–292; HTML linkification in `server/overlay.ts` (`formatDisplayPath` 7–24 lastIndexOf('/node_modules/'), `convertLinksInHtml` PATH_RE 39–40 + ANSI-span relocation 74–78, `renderErrorToHtml` 96–97).
**Signature:** `formatBrowserErrorLog(message, context, fs, stackTrace:'summary'|'full'|'none', stackFrames|null, cachedTraceMap): Promise<string>`.
**Data Shape:** CachedTraceMap = Map<sourceMapPath, TraceMap> per connection; frames = stacktrace-parser output.

### Decisive source
```ts
const frame = parsed.find((f) => f.file !== null && f.column !== null && f.lineNumber !== null && SCRIPT_REGEX.test(f.file));
...
let tracer = cachedTraceMap.get(sourceMapPath);
if (!tracer) { tracer = new TraceMap((await readFileAsync(fs, sourceMapPath)).toString()); cachedTraceMap.set(sourceMapPath, tracer); }
const originalPosition = originalPositionFor(tracer, { line: lineNumber ?? 0, column: column ?? 0 });
```
```ts
const absoluteSourcePath = path.isAbsolute(source) ? source : path.join(path.dirname(sourceMapPath), source);
return path.relative(context.rootPath, absoluteSourcePath);   // → src/App.tsx:10:20 style locations
```
```ts
// Hide Rspack runtime frames only when other useful stack frames with locations exist.
const shouldFilterRspackRuntime = formattedFrames.some((f) => !f.isRspackRuntime && f.hasLocation);
```

**Flow:** 'summary' maps ONLY findFirstUserFrame and appends ` at method (loc)` dim suffix — cheap and usually sufficient; 'full' walks every frame but shows unmapped raw locations only in verbose mode; mapping failures degrade silently to next-best. process-is-not-defined errors gain a fixed 4-line remediation hint block.
**Invariant:** (1) fetch `<file>.map` through getFileFromUrl/outputFileSystem — maps live in memfs during dev; (2) sources inside a .map are relative TO THE MAP's directory, not cwd — join(dirname(mapPath)) before relativizing or every location is wrong; (3) filtering runtime frames requires a surviving located non-runtime frame — an all-runtime stack must print as-is or the error becomes unactionable.
**Probe:** e2e `cases/browser-logs/basic-error/index.test.ts:7/:18` (expectLog/expectNoLog), `stack-trace-full`, `dedupe-log/index.test.ts:14+` (repeat suppression across rebuilds), unit-style snapshot `packages/core/tests/overlay.test.ts:115+` (convertLinksInHtml table).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "formatBrowserErrorLog findFirstUserFrame parseFrame convertLinksInHtml formatDisplayPath", limit: 8 });
```

## Verdict
Adopt tiered symbolication with per-connection TraceMap cache, map-relative source resolution, conditional runtime-frame hiding, and ANSI-aware linkification. Adapt hint text to host conventions. Omit react-specific error decoders (separate product surface).
