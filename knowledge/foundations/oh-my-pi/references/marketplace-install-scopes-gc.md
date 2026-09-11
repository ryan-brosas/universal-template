<!-- capsule-v2 -->
# Marketplace install, scopes & cache GC — how do two install scopes share one cache directory without deleting a copy the other still uses?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** The same plugin id can be installed user- AND project-scoped against one shared plugin cache — what ordering prevents an upgrade in one scope from destroying the other's files?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/plugins/marketplace/manager.ts:MarketplaceManager.installPlugin` (:241-369), `uninstallPlugin` (:446-515), `#registerRuntimePlugin` (:827-847), `#runtimePackagePath` (:806-814), scope helpers (:766-775); GC primitive `registry.ts:collectReferencedPaths` (:184-192); atomic writes `registry.ts:atomicWriteJson` (:43-70); version ladder `#resolvePluginVersion` (:417-443).
**Signature:** `installPlugin(name, marketplace, options?: {force?, scope?: "user"|"project"}): Promise<InstalledPluginEntry>`; registries: marketplaces.json (v1) + installed_plugins.json (v2, `{plugins: Record<"name@marketplace", entry[]>}`), each written via tmp+rename with Windows EPERM unlink-fallback.
**Data Shape:** id = `` `${name}@${marketplace}` `` (both segments `[a-z0-9]([a-z0-9.-]*[a-z0-9])?`, ≤64; id ≤128); cache dir `<cacheDir>/<marketplace>___<plugin>___<version>`; runtime view = symlink `<root>/node_modules/<pkgName>` → cached copy + `omp-plugins.lock.json` row.

### Decisive source
```ts
// Only now clean up old entries — new cache succeeded, so it is safe to remove old ones.
const prunedReg = removeInstalledPlugin(await readInstalledPluginsRegistry(registryPath), pluginId);
await writeInstalledPluginsRegistry(registryPath, prunedReg);
// Read both registries AFTER removal — only delete paths no longer referenced by either.
const [userReg, projectReg] = await Promise.all([...]);
const referenced = collectReferencedPaths(userReg, projectReg);
for (const entry of existing) {
	if (entry.installPath !== cachePath && !referenced.has(entry.installPath)) {
		await fs.rm(entry.installPath, { recursive: true, force: true });
	}
}
...
const wasDisabled = existing?.some(e => e.enabled === false); // disabled stays disabled after upgrade
```
**Flow:** find marketplace + catalog entry → installed-check (needs force) → resolvePluginSource → version ladder (catalog > manifest .claude-plugin/plugin.json|plugin.json|package.json > source sha[:7] > "0.0.0") → cachePlugin staged rename → embedded `.lsp.json`/`.dap.json` written with path-escape checks → registry prune → BOTH-registries referenced-set GC → re-add entry preserving enabled=false → remove stale runtime symlinks for renamed packages → `#registerRuntimePlugin` symlinks (junction on win32) + lockfile row → `#clearCache()` invalidates discovery. Uninstall/setEnabled share the scope-disambiguation ladder: present in both scopes without explicit scope → error demanding `--scope`.
**Invariant:** disk deletion is decided ONLY from the post-write union of both registries (`collectReferencedPaths`); new content is fully staged before any old state is removed; runtime package names are validated and containment-checked (`relative.startsWith("..")` → throw) before becoming symlink paths. Registry reads tolerate ANY numeric version (forward-compatible) but reject malformed shapes to empty-with-warn.
**Probe:** direct-test seam: `test/marketplace/cache.test.ts` orphan sweep (:164-218) pins the keep-only-referenced rule at the cache layer; anchor-greps at pin: `const wasDisabled = existing?.some(e => e.enabled === false);` marketplace/manager.ts:344, `!version.includes("..")` cache.ts:28.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.extensibility.plugins.marketplace.manager.MarketplaceManager.installPlugin" });
```

## Verdict
Adopt: reference-counted GC by re-reading all scopes AFTER the removal write; stage-then-clobber for cache copies; carry enabled-state across upgrades; require explicit scope on ambiguity. Adapt: your registry shapes; keep parsePluginId-style validated ids. Omit: Claude-Code v2-shape compatibility notes if not interoperating.
