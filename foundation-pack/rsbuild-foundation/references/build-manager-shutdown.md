<!-- capsule-v2 -->
# BuildManager + graceful shutdown — why does close() order socket→middleware→compiler and refcount signal handlers?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must keep the teardown ordering, outputFileSystem swap, readFileSync fallback, and SIGTERM+128 exit-code contract.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/buildManager.ts` — constructor 34–42, init 44–54, watch 59–61, close 63–81, readFileSync 83–91; `server/gracefulShutdown.ts` whole 1–69 (cleanupCallbacks Set 6, handleTermination 11–19, refcount 31/38–68); `server/httpServer.ts` 5–28 (http2 secure server allowHTTP1); preview close-once latch `previewServer.ts` 83–95.
**Signature:** `class BuildManager { init(); watch(); close(): Promise<void>; readFileSync(fileName): string }`; `setupGracefulShutdown(): () => void`.
**Data Shape:** cleanupCallbacks = Set<()=>Promise<void>>; closingPromise memoizes in-flight close.

### Decisive source
```ts
public async close(): Promise<void> {
  await this.socketServer.close();                       // sockets FIRST: no client learns of teardown mid-flight
  if (this.assetsMiddleware) await new Promise((r) => this.assetsMiddleware.close(() => r()));
  // `middleware.close()` only stop watching for file changes, compiler should also be closed.
  await new Promise((r) => this.compiler.close(() => r()));
}
```
```ts
this.outputFileSystem = (isMultiCompiler(compiler) ? compiler.compilers[0].outputFileSystem : compiler.outputFileSystem) || fs;
// bundle require needs a synchronous method... most implementations still provide readFileSync
return 'readFileSync' in this.outputFileSystem ? (this.outputFileSystem as typeof fs).readFileSync(f,'utf-8') : fs.readFileSync(f,'utf-8');
```
```ts
const onSigterm = () => handleTermination(constants.signals.SIGTERM + 128);   // POSIX convention: signal+N
process.exitCode ??= exitCode;   // never clobber a preset exit code
if (shutdownRefCount-- > 1) return;   // only the LAST teardown removes listeners
```

**Flow:** init() installs assets middleware, prepares socket server, THEN swaps this.outputFileSystem to the compiler's real (memfs) instance — anything captured earlier sees plain node:fs. Preview servers wrap their own close in a null-memoized promise so double-close (CLI quit + signal) is one teardown. Stdin-end triggers termination except under CI=true.
**Invariant:** (1) socket close must precede middleware/compiler close or connected clients receive RST instead of clean WS close frames; (2) outputFileSystem can be undefined until first compilation — always `|| fs` fallback; (3) removeCleanup(closeServer) BEFORE awaiting itself prevents re-entrancy deadlock in the cleanup set iteration.
**Probe:** e2e dev-server lifecycle via `cases/server/*` suites; unit coverage absent for close ordering (coverage caveat: deterministic source read). Related restart lane already covered by restart-shutdown capsule pass 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "BuildManager setupGracefulShutdown createHttpServer startPreviewServer closeServer", limit: 8 });
```

## Verdict
Adopt ordered three-stage close, late outputFileSystem binding with sync-read fallback, set-based cleanup registry with refcounted listener install, and SIGTERM+128 exit codes. Adapt http2 allowHTTP1 defaults to host TLS posture. Omit open.ts AppleScript ladder (browser opening UX).
