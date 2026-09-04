<!-- capsule-v2 -->
# Virtual file + prototype-chained context — how do processor-created virtual files keep their disk identity, and how do per-rule contexts stay cheap?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you represent "block 3 of readme.md" as a lintable unit without losing the physical path, and how do you stamp per-rule context without copying the world?

## VFile + FileContext
**Path/Symbol:** `lib/linter/vfile.js:VFile` (:63–113) with `hasUnicodeBOM/stripUnicodeBOM` (:23–53); `lib/linter/file-context.js:FileContext` (:11–88).
**Signature:** `new VFile(path, body, {physicalPath?})`; `new FileContext({cwd, filename, physicalFilename, sourceCode, languageOptions, settings})`, frozen once; `fileContext.extend(extension)`.
**Data Shape:** VFile keeps `path` (virtual, may be `0.js` inside a processor), `physicalPath` (disk truth, defaults to path), `body` (BOM-stripped string|Uint8Array), `rawBody` (as given), `bom:boolean`. BOM detection is dual-representation: charCode 0xFEFF for strings vs bytes EF BB BF for Uint8Array.

### Decisive source
```js
// VFile: strip on the way in, remember everything:
this.path = path;
this.physicalPath = physicalPath ?? path;
this.bom = hasUnicodeBOM(body);
this.body = stripUnicodeBOM(body);   // slice(1) string | slice(3) bytes
this.rawBody = body;
// FileContext: one frozen shared base + prototype extension per rule
// (runRules creates it ONCE; each rule gets a derived object):
extend(extension) {
  return Object.freeze(Object.assign(Object.create(this), extension));
}
```

**Flow:** `_verifyWithFlatConfigArrayAndProcessor` wraps every preprocessed block as a VFile carrying `physicalPath: block.physicalPath` so config resolution and rule context see virtual path while parsers/reporters can still find the real file; `<text>` placeholders are normalized away by splitting on `path.sep` (`normalizeFilename`). Rule contexts inherit from the single frozen FileContext via prototype — only `id`/`options`/`report` are own-properties.
**Invariant:** BOM must be stripped BEFORE parsing but preserved for fix-offset math (SourceCodeFixer re-adds it); `Object.freeze(this)` on the base makes accidental context mutation throw in strict mode; extend() freezing means two rules can never share a mutated context object.
**Probe:** `tests/lib/linter/vfile.js` (:21–77 all five constructor shapes incl. Uint8Array+BOM byte-slice assertions); `tests/lib/linter/file-context.js` (:30–126 freeze + extend semantics incl. override error :120).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "VFile stripUnicodeBOM FileContext extend physicalPath", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.vfile.VFile.constructor" });
```

## Verdict
Adopt the virtual/physical path pair and raw/stripped body duality; adopt prototype-chained frozen contexts for per-rule stamping; adapt BOM handling to your encodings; omit Uint8Array support if your linter is text-only.
