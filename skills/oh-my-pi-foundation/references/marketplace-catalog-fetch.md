<!-- capsule-v2 -->
# Marketplace catalog fetch — how do you classify "owner/repo" vs URL vs local path safely, and when may a clone be promoted into the cache?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** Adding a third-party marketplace means cloning untrusted repos and parsing untrusted catalogs — where do the safety checks sit so a bad catalog never poisons the registry?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/plugins/marketplace/fetcher.ts` — `classifySource` (:50-83), `parseMarketplaceCatalog` (:102-191), `CATALOG_RELATIVE_PATHS` (:199), `readMarketplaceCatalog` (:201-222), `cloneAndReadCatalog` (:288-303), `promoteCloneToCache` (:311-315); `marketplace/source-resolver.ts:resolvePluginSource` (:35-131); scheduling `plugins/marketplace-auto-update.ts` (49L whole).
**Signature:** `fetchMarketplace(source, cacheDir): Promise<{catalog, clonePath?}>`; `promoteCloneToCache(tmpDir, cacheDir, name): Promise<string>`; `classifySource(source): "github"|"git"|"url"|"local"` (throws on unrecognized).
**Data Shape:** catalog JSON `{name, owner:{name}, metadata?:{pluginRoot?}, plugins:[{name, source: "./rel" | {source:"github"|"url"|"git-subdir"|"npm", …}}]}`; catalog file tried at `.omp-plugin/marketplace.json` then `.claude-plugin/marketplace.json` (Claude-Code compatibility).

### Decisive source
```ts
// Rules are ordered; the first match wins. Protocol/pattern checks (rules 1-3)
// run before any path.isAbsolute() check so that SCP-style git@ URLs are
// never misclassified as local paths on Windows.
const WIN_ABS_RE = /^[A-Za-z]:[/\\]|^\\\\/;
...
// Clones to a temporary directory and reads the catalog. The caller is
// responsible for promoting the clone to its final cache location via
// `promoteCloneToCache` after any duplicate/drift checks pass.
```
**Flow:** classify (http(s).json→url, other http(s)/scp/ssh→git, owner/repo→github, ./|~/ + absolute→local) → local reads in place; github/git clone into `<cacheDir>/.tmp-clone-*` → parse+validate catalog → CALLER decides: addMarketplace promotes only after name-collision check; updateMarketplace only after catalog-name-drift guard ("Remove and re-add the marketplace to update"); failures rm the tmp clone. Catalog parsing validates required fields but SKIPS invalid plugin entries with a warn — one bad row never fails the whole marketplace. Auto-update (`scheduleMarketplaceAutoUpdate`) is fire-and-forget with modes off/notify/auto, dynamic-imports the manager to keep it out of the TUI startup graph, and swallows every error.
**Invariant:** promotion is the ONLY step that mutates the durable cache, and it happens strictly after all remote-derived validation passes; relative plugin sources must resolve inside the marketplace root (`pathIsWithin`, incl. git-subdir containment), and url-sourced marketplaces reject relative string sources outright (only marketplace.json was cached — no tree to resolve against).
**Probe:** direct-test seam: `test/marketplace/fixtures/valid-marketplace/…` consumed by fetcher/manager tests; anchor-grep at pin: `.omp-plugin/marketplace.json` fetcher.ts:199; graph evidence: `classifySource` :50-83 retrieved line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.extensibility.plugins.marketplace.fetcher.classifySource" });
```

## Verdict
Adopt: ordered classification with protocol-before-isAbsolute ordering; clone-to-temp/promote-later split gated on semantic checks; per-entry tolerant catalog parsing. Adapt: your catalog format and compat fallback paths. Omit: Claude-Code `.claude-plugin` naming if you have no compat audience.
