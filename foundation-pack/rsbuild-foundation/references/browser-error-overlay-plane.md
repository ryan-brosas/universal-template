<!-- capsule-v2 -->
# Browser error-overlay plane — how do server-formatted errors become a dismissible shadow-DOM overlay, and why does hostname resolution probe DNS twice?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `rsbuild`. **Question:** a porter reproducing dev-server error UX must know the server-side escape→ANSI→linkify pipeline (and its skip-lists), the client element's dismissal/fallback contract, and the localhost DNS-divergence guard feeding the HMR entry.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/overlay.ts` — `formatDisplayPath` (7–28), `convertLinksInHtml` (30–101), `renderErrorToHtml` (103–105); `server/ansiHTML.ts:ansiHTML` (29–63); consumers `server/socketServer.ts` (:302 errors, :478 browser logs); client `client/overlay.ts` (1–229), `client/log.ts` (1–18); host guard `server/hmrFallback.ts:resolveHostname` (23–35) consumed once at `server/assets-middleware/index.ts:254`.
**Signature:** `renderErrorToHtml(error: string, root?: string): string`; `createOverlay(title, content)` / `clearOverlay()` registered via `registerOverlay` only when `document` exists.
**Data Shape:** socket `errors` message carries BOTH `text` (all formatted errors) and `html` (overlay-filtered subset joined by `\n\n`, trimmed); anchors carry machine path in `data-file` (absolute, root-joined) and pretty text as content.

### Decisive source
```ts
// server pipeline — ORDER IS THE CONTRACT: escape FIRST, then ANSI→span, then linkify
return convertLinksInHtml(ansiHTML(escapeHtml(error)), root);
// per-line linkify with skip-lists and the ANSI close-span relocation trick:
if (NODE_INTERNAL_RE.test(line) || RSPACK_RUNTIME_RE.test(line)) return line;   // node:internal… / webpack/runtime/
const hasClosingSpan = file.includes('</span>') && !file.includes('<span');
const filePath = hasClosingSpan ? file.replace('</span>', '') : file;           // move </span> AFTER the anchor
const absolutePath = root && !isAbsolute ? path.join(root, filePath) : filePath;
return `<a class="file-link" data-file="${absolutePath}">${displayPath}</a>${suffix}`;
```
```ts
// pnpm display collapse: keep the LAST node_modules segment
for (const needle of ['/node_modules/', '\\node_modules\\']) {
  const index = filePath.lastIndexOf(needle);
  if (index !== -1) return filePath.slice(index + 1);
}
```
```ts
// client: custom element w/ shadow root; one-shot Esc listener; immediate-close dedup
root.querySelector('.close')?.addEventListener('click', this.close);
const onEscKeydown = (e) => { if (e.key === 'Escape' || e.code === 'Escape') { this.close();
  document.removeEventListener('keydown', onEscKeydown); } };
document.querySelectorAll<ErrorOverlay>(overlayId).forEach((n) => n.close(true)); // avoid stacked overlays
void fetch(`/__open-in-editor?file=${encodeURIComponent(file)}`);                 // data-file → editor
```
```ts
// hmrFallback: NOT a websocket fallback — a DNS-divergence guard for the HMR client URL
const [defaultLookup, explicitLookup] = await Promise.all([
  dns.lookup(LOCALHOST), dns.lookup(LOCALHOST, { verbatim: true })]);
const match = defaultLookup.family === explicitLookup.family && defaultLookup.address === explicitLookup.address;
return match ? undefined : defaultLookup.address;   // mismatch → bind the CLIENT to the resolved address
```

**Flow:** stats errors/warnings/browser logs → `formatStatsError` (existing capsule) → overlay filter (`dev.client.overlay.errors(err)` may drop entries from the HTML tier only, `text` stays complete) → `renderErrorToHtml` per error → socket message per token → client `createOverlay` mounts the custom element (guard chain: no customElements → warn+noop; existing overlays closed immediately; DOM failure → warn fallback); non-browser environments never register and log an info hint. Separately, at middleware setup the resolved host (DNS guard applied when host is exactly `localhost`, wildcard → `localhost`) is passed to `applyHMREntry` so the injected client connects to the address the server actually bound.

**Invariant:** HTML safety comes from ordering (escape before any span/anchor injection) plus the skip-lists; the overlay must be single-instance (immediate close) and always dismissible (X / outside click / Esc / animation-finish removal with `close(true)` bypass). The DNS guard must only rewrite when the two lookup strategies DISAGREE.

**Probe:** `packages/core/tests/overlay.test.ts` (267 lines) pins: full ANSI code table incl. bright 91–97 aliasing to 31–37 and background codes ignored; nested spans; unbalanced-close padding; ANSI-span relocation inside linkified paths; file:/// stripping win/unix; relative-path root-joining into data-file; node:internal and webpack/runtime skips; URL linkification; formatDisplayPath pnpm collapse + non-node_modules relativization. Executed source pins: pipeline order overlay.ts:104, `n.close(true)` client/overlay.ts:219, `verbatim: true` hmrFallback.ts:15.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "resolveHostname localhost dns verbatim family mismatch", limit: 10 });
```
Executed post-reindex: `resolveHostname` rank#1 (23–35 line-exact). Adversarial RED observed: query "fallback when websocket disconnects reconnect" returns 20 hits WITHOUT hmrFallback.ts — the file name misleads; only capsule vocabulary retrieves it.

## Verdict
Adopt the ordered render pipeline, dual text/html socket payload with overlay-level filtering, shadow-DOM custom-element overlay with its three dismissal paths and fallback warnings, and the double-lookup DNS guard. Adapt colors/editor endpoint to your product. Omit rsbuild's specific CSS. Coverage caveat: client/log.ts has no dedicated suite (18-line level gate: silent −1 < error 0 < warn 1 < info 2); suites not executable in this lane (no node_modules).
