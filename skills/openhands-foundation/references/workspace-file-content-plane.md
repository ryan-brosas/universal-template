<!-- capsule-v2 -->
# Workspace file-content plane — how does a browser preview workspace files (text/HTML/images/PDF) against a cookie-authenticated static server, per backend kind?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How do you authenticate top-level `<iframe>`/`<img>` requests that cannot carry headers, and classify bytes without downloading what you can stream?

## Cookie-minted workspace session + four-kind content classifier
**Path/Symbol:** `src/hooks/query/use-workspace-session.ts` (`useWorkspaceSession` :46–95, `joinWorkspaceUrl` :103–116); `src/hooks/query/use-workspace-file-content.ts` (`classifyKind` :96–103, `isLikelyBinary` :105–112, `queryFn` :186–292); `src/components/features/files-tab/file-content-viewer.tsx` (:69–230).
**Signature:** `POST /api/auth/workspace-session` exchanges `X-Session-API-Key` for an `oh_workspace_session_key` cookie scoped to `/api/conversations`; `useWorkspaceFileContent(relativePath: string | null)` → `WorkspaceFileContent { path, kind: "text"|"image"|"pdf"|"binary", text, staticUrl, mimeType }`.
**Data Shape:** queryKey embeds conversation identity + `isCloud ? "cloud" : baseUrl` + relativePath + absoluteFilePath + `workspaceMutationCount` — an agent-side edit tick refetches the SAME path while consumers append the same counter to `staticUrl` (`withWorkspaceCacheBuster`) so iframe/img caches bust in the same tick.

### Decisive source
```ts
// use-workspace-file-content.ts — git's own binary heuristic.
function isLikelyBinary(buffer: ArrayBuffer): boolean {
  // Same heuristic git uses: presence of a NUL byte in the first ~8KB.
  const view = new Uint8Array(buffer, 0, Math.min(buffer.byteLength, 8000));
  for (let i = 0; i < view.length; i += 1) {
    if (view[i] === 0) return true;
  }
  return false;
}
```
```ts
// viewer, PDF branch — deliberately NOT sandboxed; comment documents why:
// Chromium refuses to instantiate its built-in PDF viewer inside any
// sandboxed frame (the `sandbox` attribute disables plugins unconditionally…).
// HTML/SVG previews instead render with sandbox="allow-same-origin" so
// relative assets resolve while missing allow-scripts keeps scripts inert.
```

**Flow:** local backend → mint session ONCE (`staleTime/gcTime Infinity`; the cookie lives in the browser jar; LOCAL-ONLY because a cloud Set-Cookie dies inside the proxy hop and fetch-with-credentials can't attach cross-origin anyway) → classify by extension: image/pdf are NEVER fetched (rendered from `staticUrl` directly — test-pinned), text is fetched with `credentials:"include"` (cookie travels; no custom header ⇒ no CORS preflight), NUL-sniffed into binary, decoded UTF-8 `fatal:false` → cloud backend diverges structurally: `readCloudConversationFile` returns a STRING via `/api/v1/app-conversations/{id}/file`, paths anchored ABSOLUTE (`getGitPath(repo, workingDir)` + forced leading slash) because the runtime download rejects relative paths; binary bytes cannot round-trip through the string API (documented best-effort limitation) → viewer ladder: plain mode = highlighted source or fallback; rich mode = img / unsandboxed pdf iframe / sandboxed HTML iframe / prose markdown / highlighted code, with DISTINCT testids for load-error vs unpreviewable-binary and format-named Office messages (.pptx→PowerPoint) driven by a label-doubles-as-allow-list map.
**Invariant:** Auth for embedded artifacts must ride cookies minted for a scoped path, never custom headers. Never download bytes you can hand to the browser as a URL (image/pdf). Load failure and "fetched but not previewable" are different UI states. One mutation tick refreshes both the decoded text and every sibling asset in the rich preview.
**Probe:** `__tests__/hooks/query/use-workspace-file-content.test.tsx` (370 L WHOLE) — image/PDF no-fetch (:138–171), NUL flip (:173–194), mutation-tick refetch (:196–222), cloud absolute-path anchoring to working_dir (:321–344), SVG data-URI (:346–368); `file-content-viewer.test.tsx` it.each rich+plain over real ZIP-with-NUL .pptx bytes (:100–123). Both files' flagged parse-partial lines (:14/:18) are `importOriginal<typeof import(…)>()` scaffolding — read directly, benign.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "workspace file content static url binary sniff viewer", limit: 10 });
```

## Verdict
Adopt the cookie-session mint + extension classification + NUL-sniff + never-fetch-streamable-kinds posture and the dual cache-bust keying. Adapt endpoints/MIME tables; omit the cloud string-API branch if your backend serves bytes faithfully. Coverage: no_recorded_issue on all three source paths at gen 2026-08-24T16:13:32Z.
