<!-- capsule-v2 -->
# appIcon PWA plane — why do icons resolve to dist-relative paths with mime lookup and manifest validation errors go to the compilation?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce icon formatting/caching, emit stage, webmanifest assembly, and error routing.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/appIcon.ts` — formatIcon cache 29–73 (`${distDir}|${publicPath}|${src}` key), processAssets 'additional' 75+, missing-file/name errors 90–120, emit + tags 120–189 (link rel=icon sizes / apple-touch-icon / manifest link).
**Signature:** `formatIcon(icon, distDir, publicPath, lookup): AppIconItem & IconExtra`.
**Data Shape:** IconExtra = {src,sizes,mimeType?} & ({isURL:true} | {isURL:false, absolutePath, relativePath}); html.appIcon {name?, icons[], filename?: string}.

### Decisive source
```ts
const absolutePath = path.isAbsolute(src) ? src : path.join(api.context.rootPath, src);
const relativePath = path.posix.join(distDir, path.basename(absolutePath));
const formatted = { ...icon, sizes: `${size}x${size}`, src: ensureAssetPrefix(relativePath, publicPath),
                    isURL: false, absolutePath, relativePath, mimeType: lookup(absolutePath) };
```
```ts
if (icon.target === 'web-app-manifest' && !appIcon.name) {
  addCompilationError(compilation, '"appIcon.name" is required when "target" is "web-app-manifest".');
  continue;   // skip THIS icon, keep building others
}
if (!(await fileExistsByCompilation(compilation, icon.absolutePath))) { addCompilationError(...); continue; }
```

**Flow:** icons are emitted via compilation assets at the ADDITIONAL stage so other plugins can still process them; webmanifest gets name+icons (192px/512px purpose maskable handling per spec) and is emitted under html.appIcon.filename defaulting to manifest.webmanifest; HTML gains `<link rel="icon">`, `apple-touch-icon`, and `rel="manifest"` tags. Format results cached by (distDir, publicPath, src) because modifyHTMLTags re-runs per build.
**Invariant:** (1) existence checks MUST use compilation.inputFileSystem (respects watch fs caching), not node fs; (2) errors go through addCompilationError — failing ONE icon must not abort the build or kill the whole HTML surface; (3) URL-form icons skip emission but still produce tags and mimeType.
**Probe:** e2e `cases/html/app-icon/index.test.ts` (335L tag+manifest assertions), `html/app-icon-public-manifest`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginAppIcon formatIcon addCompilationError fileExistsByCompilation", limit: 8 });
```

## Verdict
Adopt compile-scoped icon emission with per-icon error isolation and cache-keyed formatting. Adapt manifest fields to host PWA needs. Omit mrmime if host has its own mime table.
