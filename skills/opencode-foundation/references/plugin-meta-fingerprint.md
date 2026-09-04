<!-- capsule-v2 -->
# Plugin meta fingerprinting — how do you detect "this plugin changed since last load" across processes?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How does opencode persist per-plugin load state and classify each load as first/updated/same, safely under concurrent processes?

## Fingerprint store
**Path/Symbol:** `packages/opencode/src/plugin/meta.ts` (`touchMany`, `next`, `fingerprint`, lines 108-159).
**Signature:** `touchMany(items: Touch[]): Promise<Array<{state:"first"|"updated"|"same", entry: Entry}>>` with `Touch = {spec,target,id}`.
**Data Shape:** Store = JSON map keyed by plugin id at `OPENCODE_PLUGIN_META_FILE` or `<state>/plugin-meta.json`. Entry keeps identity core (`id/source/spec/target` + `modified` mtime for file source OR `requested`/`version` for npm) plus counters (`first_time`, `last_time`, `time_changed`, `load_count`) and optional themes. Fingerprint = `target|modified` (file) or `target|requested|version` (npm).

### Decisive source
```ts
// meta.ts:124-140 — monotonic fields with fingerprint-gated time_changed
function next(prev: Entry | undefined, core: Core, now: number): { state: State; entry: Entry } {
  const entry: Entry = {
    ...core,
    first_time: prev?.first_time ?? now,
    last_time: now,
    time_changed: prev?.time_changed ?? now,
    load_count: (prev?.load_count ?? 0) + 1,
    fingerprint: fingerprint(core),
    themes: prev?.themes,
  }
  const state: State = !prev ? "first" : prev.fingerprint === entry.fingerprint ? "same" : "updated"
  if (state === "updated") entry.time_changed = now
  return { state, entry }
}
```

**Flow:** build all rows (stat mtimes / read installed package.json versions) OUTSIDE the lock → `Flock.withLock("plugin-meta:"+file)` serializes against other processes → re-read store inside the lock → apply each touch → single writeJson of the whole store → return states. `setTheme`/`list` take the same lock; reads that fail to parse yield `{}` so a corrupt file heals on next touch.
**Invariant:** The lock is keyed on the STORE FILE PATH (`lock(file)`), not the plugin id — every mutation of a given store serializes globally, which is what makes read-modify-write safe across processes. Counters are advance-only; `themes` survive fingerprint changes because they're copied from prev. File plugins fingerprint on **mtime**, not content — touching a plugin file without editing it still counts as "updated" (test bumps utimes by +10s to prove it). npm plugins fingerprint on requested-range + resolved version, so a range that re-resolves to the same version stays "same".
**Probe:** `packages/opencode/test/plugin/meta.test.ts` — `"tracks file plugin loads and changes"` (:30, first→same→updated via utimes bump), `"tracks npm plugin versions"` (:69), and the cross-process one: `"serializes concurrent metadata updates across processes"` (:102, spawns real workers through `fixture/plugin-meta-worker.ts`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "PluginMeta touchMany fingerprint plugin metadata", limit: 8 });
```

## Verdict
Adopt fingerprint-based change classification, lock-keyed-on-file serialization, and stat-before-lock row building. Adapt the fingerprint inputs (content hash instead of mtime if your toolchain has coarse mtimes) and storage medium. Omit theme bookkeeping unless porting TUI themes.
