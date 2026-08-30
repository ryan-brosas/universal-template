<!-- capsule-v2 -->
# Live SSE dashboard export — how does a static HTML file become a live view of the JSONL?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What is served, how do clients get updates, and what is the server's lifecycle?

## startStaticServer + registerSseClient — two-file allowlist, /events stream, reuse-if-same-workdir
**Path/Symbol:** `extensions/pi-autoresearch/index.ts` — template injection :672–693, serve allowlist :695–709, SSE :711–720, server :722–778, export command :780–801, teardown `stopDashboardServer` :648–670.
**Signature:** `/autoresearch export` → render template (title from first config entry, logo inlined as data:URL) into `mkdtemp('pi-autoresearch-dashboard-')/index.html` → bind ephemeral port on 127.0.0.1 → open browser.
**Data Shape:** served paths ONLY `/` (rendered html) and `/autoresearch.jsonl` (raw file); `/events` = text/event-stream with `retry: 1000`.

### Decisive source
```ts
function resolveServedFile(workDir: string, requestPath: string): string | null {
  if (requestPath === '/') return dashboardServerHtmlPath;
  if (requestPath === '/autoresearch.jsonl') return autoresearchJsonlPath(workDir);
  return null;                                   // everything else 404s — no directory listing
}
// same workdir ⇒ keep server, swap html pointer:
if (dashboardServer && dashboardServerWorkDir === resolvedWorkDir && dashboardServerPort) {
  dashboardServerHtmlPath = resolvedDashboardHtmlPath;
  resolve(dashboardServerPort);
  return;
}
```

**Flow:** export → build fresh temp HTML each call (old temp dirs orphan by design — tmp cleanup owns them) → reuse the running server when the workdir matches (clients survive) else stop+rebind → browser opens → page polls/fetches `/autoresearch.jsonl` and subscribes to `/events`; SSE clients tracked in a Set and force-closed on stop. Teardown hooks: off/clear/shutdown all call `stopDashboardServer`.
**Invariant:** the two-path allowlist means NO arbitrary filesystem read escapes via URL crafting. The rendered HTML carries only cosmetic data (title/logo) — experiment DATA always comes live from the JSONL endpoint, so the page can never show stale numbers after a refresh. Single-server-per-process is enforced by the module-level singleton quartet (`dashboardServer/Port/WorkDir/HtmlPath`).
**Probe:** anchors: `grep -n 'dashboardSseClients' extensions/pi-autoresearch/index.ts | wc -l` → 5 (:632 set decl, add :718, delete :719, drain loop ×2 :649–651 area); `grep -n "requestPath === '/autoresearch.jsonl'" extensions/pi-autoresearch/index.ts` → :707; `grep -cn 'stopDashboardServer()' extensions/pi-autoresearch/index.ts` → 4 call sites + 1 def (:648).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "startStaticServer registerSseClient writeDashboardFile stopDashboardServer", limit: 10 });
```

## Verdict
Adopt the allowlisted static+SSE pattern for any file-backed live dashboard; adapt template/paths; omit the browser-open spawn for headless hosts. Coverage caveat: untested directly — source-pinned.
