<!-- capsule-v2 -->
# workerExporter handleExport kernel — what does the worker side of an export task look like, and why does it throw plain objects?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How does one wrapper serve three export variants, buffer tiny ExcelJS writes into RPC-sized chunks, and preserve error properties across the thread boundary?

## HOF wrapper + buffered pipe + deliberate error stripping
**Path/Symbol:** `app/server/lib/workerExporter.ts` — HOF `handleExport` (:17–43) wrapping each exported task (`makeXLSXFromOptions = handleExport(doMakeXLSXFromOptions)` :15; internal variants :109/:139/:155), chunk aggregator `bufferedPipe` (:48–76), dispatcher `doMakeXLSXFromOptions` (:78–93), streaming-vs-buffer workbook factory `convertToExcel` (:174–261), worksheet-name sanitizer `sanitizeWorksheetName` (:266–277), ASAR workaround default export `doNothing` (:287–288).
**Signature:** `handleExport<T extends any[]>(make: (a: ActiveDocSource, testDates: boolean, output: Stream, ...args: T) => Promise<void | ExcelBuffer>) => ({port, testDates, args}: {port: MessagePort, testDates: boolean, args: T}) => Promise<void>`.
**Data Shape:** inbound `{ port, testDates, args }` from ExportXLSX; outbound chunks via `rpc.postMessage(chunk)` with `threshold = 64 * 1024`.

### Decisive source
```ts
} catch (e) {
  log.debug("workerExporter %s %s: error %s", threadId, make.name, String(e));
  // When Error objects move across threads, they keep only the 'message' property. We can
  // keep other properties (like 'status') if we throw a plain object instead. (Didn't find a
  // good reference on this, https://github.com/nodejs/node/issues/35506 is vaguely related.)
  throw { message: e.message, ...e };
}
```
```ts
// If the buffer is large enough, post it to the callback. Also post the very first chunk:
// since this becomes an HTTP response, a quick first chunk lets the browser prompt the user
// more quickly about what to do with the download.
if (length >= threshold || flushed === 0) {
  flush();
}
```
**Invariant:** errors MUST be rethrown as plain objects — a real `Error` instance survives `postMessage` with only `.message`, so ApiError's `.status` would vanish and the HTTP layer would downgrade 403/404 to 500. ExportXLSX rehydrates with `Object.assign(new Error(e.message), e)`. The flush ladder has TWO triggers: 64KB threshold AND "first chunk always" — the first-chunk rule exists purely so the browser shows the save dialog immediately on big exports. `bufferedPipe` exists because WorkbookWriter emits many tiny writes through the zip layer; without buffering, RPC per-write overhead dominates.

**Flow:** pool invokes the wrapped function by method name → build rpc → `getStub<ActiveDocSource>("activeDocSource")` (the MAIN-thread data source, registered by streamXLSX) → wire `port.on("message")` → PassThrough piped through `bufferedPipe` into rpc posts → run variant → `port.close()` signals the main thread to end the response. Dispatcher precedence mirrors DSV: viewSectionId → tableId → whole doc (`doExportDoc` + `handleTable` per sheet). `convertToExcel(stream?, …)` dual mode: with a stream uses memory-light `WorkbookWriter({useStyles:true, useSharedStrings:true, stream})` + per-table `commit()`; without (grist-static browser context) falls back to in-memory `Workbook` and `end()` returns `wb.xlsx.writeBuffer()`. Sheet names pass through `sanitizeWorksheetName` (ExcelJS forbids `*?:/\[]`, quotes/spaces trimmed at ends). The trailing `doNothing` default export is REQUIRED: piscina's require() path must resolve under Electron ASAR (grist-electron#9).

**Probe:** deterministic greps (coverage caveat: no dedicated unit file):
```bash
cd /mnt/hdd/utopia/inspo/grist-core
grep -n "throw { message: e.message, ...e };" app/server/lib/workerExporter.ts   # 40
grep -n "flushed === 0" app/server/lib/workerExporter.ts                         # 70
grep -n "getStub<ActiveDocSource>" app/server/lib/workerExporter.ts              # 28
grep -n "export default function doNothing" app/server/lib/workerExporter.ts     # 287
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "handleExport bufferedPipe workerExporter", limit: 5 });
// → workerExporter.handleExport Function app/server/lib/workerExporter.ts 17-43 (+ bufferedPipe 48-76)
```

## Verdict
Adopt the kernel wholesale for any worker-based serializer: HOF wrapper normalizing (port, flags, args), stub-not-import for host data, buffered pipe with early-first-chunk, plain-object error transport paired with boundary rehydration. Adapt thresholds to your latency budget. Omit the ASAR shim only outside Electron packaging — but keep the comment trail; the next porter will otherwise delete the "useless" function.
