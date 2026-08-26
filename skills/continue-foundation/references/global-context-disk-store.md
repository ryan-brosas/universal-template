<!-- capsule-v2 -->
# Disk-backed global store — how do you persist cross-process settings when the file may be corrupt?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** Where does cross-process mutable agent state live, and what happens on a corrupted or missing store file?

## Stateless whole-file read-modify-write with a corruption salvage ladder
**Path/Symbol:** `core/util/GlobalContext.ts` (whole file, 185 lines): `update` (63–116), `get` (118–144), `getSharedConfig` (146–159), `updateSelectedModel` (170–184); callers `core/core.ts:448–466`, `core/config/profile/doLoadConfig.ts:174–189`.
**Signature:** `update<T extends keyof GlobalContextType>(key: T, value: GlobalContextType[T]): void` ; `get<T>(key): GlobalContextType[T] | undefined` ; `getSharedConfig(): SharedConfigSchema` ; `updateSelectedModel(profileId, role, title): GlobalContextModelSelections`.
**Data Shape:** one JSON file at `getGlobalContextFilePath()`; keys include `selectedModelsByProfileId: Record<profileId, Record<role, title|null>>`, `shownDeprecatedProviderWarnings: Record<providerTitle, boolean>`, `sharedConfig`, `lastSelectedProfileForWorkspace`. The class holds NO fields — every operation touches disk.

### Decisive source
```ts
// update(): missing file => write ONLY this key (partial object); corrupt file =>
// regex-salvage sharedConfig from raw text, unlink, recreate with salvaged + new key
if (!fs.existsSync(filepath)) {
  fs.writeFileSync(filepath, JSON.stringify({ [key]: value }, null, 2));
} else { /* read; on parse error: */ }
const match = data.match(/"sharedConfig"\s*:\s*({[^}]*})/);
const salvagedSharedConfig = salvageSharedConfig(JSON.parse(match[1]));
fs.unlinkSync(filepath);
fs.writeFileSync(filepath, JSON.stringify({ ...salvaged, [key]: value }, null, 2));

// get(): corrupt file is DELETED and reads as undefined
} catch (e) { console.warn("Error parsing global context, deleting corrupted file");
  try { fs.unlinkSync(filepath); } catch {} return undefined; }

// getSharedConfig(): failed validation repairs the stored value in place
const salvagedConfig = salvageSharedConfig(sharedConfig);
this.update("sharedConfig", salvagedConfig);
return salvagedConfig;
```

**Flow:** every write = read file → parse → assign ONE key → rewrite whole file. Protocol handlers in core.ts pair write-then-reload: `config/updateSharedConfig` (:448–454) and `config/updateSelectedModel` (:456–466) both call the store then `configHandler.reloadConfig(...)`. Deprecation toasts (doLoadConfig:174–189) read `shownDeprecatedProviderWarnings`, toast a deprecated provider only if its title flag is unset, then persist `true` forever.
**Invariant:** instances are stateless and interchangeable (a fresh `new GlobalContext()` per config load sees the same data); a damaged file never wedges the runtime — it degrades to undefined/salvaged values and self-repairs on the next read of `sharedConfig`; but there is NO locking, so concurrent processes are last-writer-wins at whole-key granularity.
**Probe:** direct tests: none for GlobalContext itself at this pin (recorded caveat). Source-pinned observables: `updateSelectedModel("p1", "chat", "gpt")` on an empty store yields `{ p1: { chat: "gpt" } }` and preserves sibling profiles via spread-merge; `getSharedConfig()` returns the salvaged object it just wrote back.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "GlobalContext selectedModelsByProfileId update", limit: 10 });
await mcp.codebase_memory.search_code({ project: "continue", pattern: "updateSelectedModel", file_pattern: "*.ts", limit: 8 });
// graph gap: trace_path inbound for updateSelectedModel shows callers_total 0 — dispatch is dynamic
// (this.globalContext inside core.ts message-handler closures); search_code finds core.ts:456–463.
```

## Verdict
Adopt the stateless-disk-store shape (any process can read/write without warm-up), the partial-first-write behavior, delete-on-corrupt reads, salvage-and-writeback for security-sensitive keys, and write-then-reload pairing by callers; adapt the key set and salvage regex to your schema; omit the naive `"sharedConfig"\s*:\s*({[^}]*})` extraction if your nested objects can contain `}` (it only works because SharedConfigSchema fields are flat). Trap: no cross-process lock — do not copy where multi-writer consistency matters.
