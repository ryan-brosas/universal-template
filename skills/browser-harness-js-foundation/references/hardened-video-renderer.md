<!-- capsule-v2 -->
# Hardened review/export renderer — how do you render and encode video in the user's own browser without wrecking it, then verify the artifact?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the disposable-page lifecycle, the token-guarded file server, and the MP4 verification ladder?

## Detached browserContext page + random-token allowlist server + ffprobe contract checks
**Path/Symbol:** `skills/cdp/sdk/video-render.ts:serveDirectory` (:110-150), `isServableRecordingFile` (:100-108), `openPage`/`closePage` (:168-198), `bounded` (:246-254), `exportWebm` (:506-554), `exportVideo` verification (:615-637).
**Signature:** `serveDirectory<T>(root: string, fn: (baseUrl: string) => Promise<T>): Promise<T>` (spawns, runs, always closes) · `openPage(session, url): Promise<BrowserPage>`.
**Data Shape:** servable paths are a fixed HTML/JS allowlist plus `\d+.jpg`, `.privacy-review/\d+.jpg`, `.renderer-review/<uuid>.png|jpg`; export must be exactly ONE 1920×1080 H.264 yuv420p stream.

### Decisive source
```ts
const absoluteRoot = realpathSync(resolve(root));
const token = randomBytes(24).toString('hex');
if (!url.pathname.startsWith(`/${token}/`)) { response.writeHead(404).end('not found'); return; }
...
if (!info.isFile() || info.isSymbolicLink() || !realpathSync(path).startsWith(absoluteRoot + sep)) {
  response.writeHead(403).end('forbidden');     // traversal + symlink escape denied
}
```
page lifecycle (failure-safe):
```ts
browserContextId = (await bounded(session.domains.Target.createBrowserContext())).browserContextId;
targetId = (await bounded(...Target.createTarget({ url:'about:blank', browserContextId }))).targetId;
... catch → close partial target + dispose context before rethrowing
```
and the export verification:
```ts
if (videoStreams.length !== 1 || stream?.codec_name !== 'h264' || stream?.width !== 1920
  || stream?.height !== 1080 || stream?.pix_fmt !== 'yuv420p')
  throw new Error('export must contain one 1920x1080 H.264 yuv420p video stream');
if (Math.abs(actual - expected) > Math.max(1, expected * 0.08))
  throw new Error(`export duration ${actual}s does not match composition ${expected}s`);
run('ffmpeg', ['-v','error','-err_detect','explode','-i', output, '-f','null','-'], ...);
```

**Flow:** render root served ONLY under a per-run random token with an extension/path allowlist, symlink+traversal rejected → renderer page lives in a THROWAWAY browserContext on the connected browser (never the user's tabs), torn down in `finally` even after partial failure; every CDP step wrapped in `bounded(op, label, timeout)` → WebM captured via `Browser.setDownloadBehavior` into the same context with size-stability polling (two equal stats 300ms apart) then rename → ffmpeg CRF20 yuv420p faststart → probe contract + duration tolerance max(1s, 8%) + full `-err_detect explode` decode pass + 3-frame final contact sheet → on ANY failure the webm/partial/output files are deleted.
**Invariant:** (1) Rendering is ISOLATED from user state: fresh browserContext + explicit dispose; docs mandate a fully detached headless profile for the whole job. (2) The file server trusts NOTHING: token prefix, filename allowlist, containment re-check post-resolve — because it serves a directory containing private frames. (3) Export refuses to overwrite existing outputs and cleans its own debris on failure (`completed` flag gates cleanup). (4) `withVideoLock` (video.ts :594-624) serializes ALL review/export machine-wide via pid-recorded lockfile with stale-pid liveness probing (`process.kill(owner, 0)`).
**Probe:** no direct test for render (needs live Chromium+ffmpeg). Deterministic probes: `grep -n "randomBytes\|isServableRecordingFile\|err_detect" skills/cdp/sdk/video-render.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "serveDirectory", limit: 3, fields: ["signature", "name", "file"] });
// resolves video-render.serveDirectory @ video-render.ts:110-150
```

## Verdict
Adopt the disposable-context rendering + token-allowlisted static server + probe-contract verification as one unit whenever you render heavy media inside a browser you don't own; adapt resolution/fps constants to your GPU budget; omit the download-behavior dance only if your renderer can write files directly.
