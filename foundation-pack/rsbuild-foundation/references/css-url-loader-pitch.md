<!-- capsule-v2 -->
# CSS url loader pitch — why does the ?url loader re-execute the css pipeline via importModule and emit with immutable?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the pitch-phase child compilation, name-source fallback ladder, and hash-placeholder immutability rule.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/loader/cssUrlLoader.ts` — HASH_PLACEHOLDER_REGEX 16–17, `getCSSUrlNameSource` 31–34, `getCSSContent` 39–50, `getContentHash` 52–62, main fn 64–66 (returns source untouched), `pitch` 68–116.
**Signature:** `export const pitch: PitchLoaderDefinitionFunction<CSSUrlLoaderOptions>(remainingRequest): Promise<string>`.
**Data Shape:** options `{filename: string|(pathData,assetInfo)=>string, modules}`; emitted export = `import.meta.rspackPublicPath + "<filename>"`.

### Decisive source
```ts
const moduleExports = await this.importModule(`!!${remainingRequest}`);   // run the FULL css pipeline as a child build
const content = getCSSContent(moduleExports);   // unwrap .default; non-string → loud throw
```
```ts
const nameSource = getRelativePath(path.join(root,'src'), resourcePath)   // prefer src/-relative
  ?? getRelativePath(root, resourcePath)                                  // else root-relative
  ?? path.basename(resourcePath);                                         // else basename
const contentHash = getContentHash(this, content);   // compilation's own hashFunction/digest
const { path: filename, info } = this._compilation.getAssetPathWithInfo(filenameTemplate, pathData);
this.emitFile(filename, content, undefined, { ...info, ...assetInfo,
  immutable: info.immutable || HASH_PLACEHOLDER_REGEX.test(filenameTemplate) });
return `export default import.meta.rspackPublicPath + ${JSON.stringify(filename)};`;
```

**Flow:** the pitch returning a string SHORT-CIRCUITS the normal loader chain for the URL import — the module's value becomes the emitted asset URL expression. CSS Modules files are rejected loudly (?url of a modules file is meaningless). The `!!` prefix bypasses matching loaders so the child request hits exactly the css pipeline. Hash placeholder detection (`[hash]`,`[contenthash]`,`chunkhash`, namespaced forms) marks the asset immutable for long-term caching.
**Invariant:** (1) contentHash must use the COMPILATION's hashFunction/digest or filenames mismatch sibling assets; (2) publicPath must NOT be baked in at emit time — runtime concatenation keeps dev/prod prefixes working; (3) pitch MUST return the export string from the PITCH phase (main fn returns source unchanged and is never used).
**Probe:** e2e `cases/css/url-query/index.test.ts` (+ url-query-filename-function, url-query-css-modules rejection family), snapshot `css.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "cssUrlLoader pitch importModule getAssetPathWithInfo emitFile", limit: 8 });
```

## Verdict
Adopt pitch-phase child compilation, src-root-relative naming ladder, compilation-hash reuse, placeholder-driven immutability, and runtime publicPath concat. Adapt the runtime global (`import.meta.rspackPublicPath`) to host. Omit CSS Modules rejection if host lacks modules.
