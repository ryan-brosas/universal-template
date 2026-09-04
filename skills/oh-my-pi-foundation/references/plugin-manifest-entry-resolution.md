<!-- capsule-v2 -->
# Manifest entry resolution — when a plugin declares `extensions: ["./dist/missing.ts"]`, why must that fail instead of loading an index?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** Entry points come from package.json manifests, directory conventions, or feature blocks — what precedence avoids silently loading the wrong file?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/plugins/loader.ts:resolvePluginManifestEntries` (:401-445), `resolveManifestEntryFiles` (:363-378), `readDeclaredManifestEntries` (:260-295), `resolveDirectoryEntries` (:308-344), `findDirectoryIndex` (:235-241); consumers: install validation (manager.ts :389-415) and `getAllPlugin*Paths` (:470-521).
**Signature:** `resolvePluginManifestEntries(plugin, key: "tools"|"hooks"|"commands"|"extensions"): Array<{ entry: string; resolvedPath: string | null }>` — one record PER DECLARED ENTRY, `resolvedPath: null` = declared but missing.
**Data Shape:** module extensions `[".ts",".js",".mjs",".cjs"]`; `.d.ts`-family excluded via `DECLARATION_FILE_RE`; features: `{ [name]: { default?, extensions?, tools?, hooks?, commands? } }` with `enabledFeatures === null` meaning "manifest default:true entries".

### Decisive source
```ts
function readDeclaredManifestEntries(dir) {
	// ... parse <dir>/package.json omp|pi .extensions
	return { declared: true, files };   // declared=true is AUTHORITATIVE:
}
// callers must not fall back to index/scan, so a missing declared file surfaces
// as a missing entry instead of silently loading a stale index
...
const expandDirectory = key === "extensions";   // ONLY extensions may fan out over
												// sub-directories; `tools: "."` must still
												// resolve plain ./index.ts
```
**Flow:** per manifest key: base entries first, then enabled-feature entries (explicit list ∩ manifest.features) OR `default:true` entries when selection is null → each entry resolves file→itself, directory→(extensions only: declared-manifest → direct index → one-level children scan; other keys: direct index only) → unresolvable entry yields `{entry, resolvedPath: null}` instead of being dropped.
**Invariant:** two consumers exploit the same records differently — install-time validation THROWS on any null ("declared extension entry not found on disk"), while runtime path getters filter nulls out; a manifest that lists ANY extensions suppresses every fallback so decoy `index.ts` files can't mask a broken build. Feature validation at install (`Unknown feature "x" … Available: …`) keeps stored selections honest before they ever reach this resolver.
**Probe:** direct-test seam: `test/plugin-install-validation.test.ts` "rejects an install whose manifest declares a missing extension entry" (:347-394, expects `/dist\/missing\.ts/`); anchor-grep at pin: `const expandDirectory = key === "extensions";` loader.ts:408.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.extensibility.plugins.loader.resolvePluginManifestEntries" });
```

## Verdict
Adopt: declared-over-convention precedence with explicit missing-entry reporting rather than silent skips; scope directory-expansion to the ONE manifest key whose ecosystem convention supports it. Adapt: your manifest field names; keep the {entry, resolvedPath|null} record shape so validation and runtime share one resolver. Omit: pi `extensions/<name>/index.ts` history notes.
