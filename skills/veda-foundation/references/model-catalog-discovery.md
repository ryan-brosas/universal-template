<!-- capsule-v2 -->
# Model-catalog discovery — how do you build a per-backend "what models can I use" command that is offline by default, probes live only where possible, and degrades with labeled warnings instead of throwing?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** How do you collect, for each installed CLI backend, its effective default (with resolution source), its aliases, and a bounded catalog of discoverable models — where some backends expose live discovery, some only private local files, and some nothing at all — without the listing command ever failing because a foreign tool misbehaved?

## Connected graph-selected seam
**Path/Symbol:** `src/agent/model-catalog.ts:collectBackend` (:462–593), `collectModels` (:599–623), `defaultProbe` (:342–356), `resolveDeps` (:371–379), `dedupe` (:390–399); DTOs `ModelsResult`/`BackendModelCatalog`/`CatalogModel` (:34–88); constants `ALL_BACKENDS` (:106), `DISPLAY_CAP=5` (:108), `REFRESH_TIMEOUT_MS=10_000` (:358).
**Signature:** `collectModels(config: ModelsConfig, globalConfig?: GlobalConfig, deps?: ModelCatalogDependencies): Promise<ModelsResult>`; `defaultProbe(command: string, args: string[], timeoutMs: number): Promise<string | undefined>`.
**Data Shape:** `ModelsResult { schemaVersion: 1; refreshed; backends: BackendModelCatalog[]; warnings[] }`. Per backend: `installed`, `defaultModel` (an `EffectiveModelResolution` carrying its own source tag), `aliases`, `models` (visible rows), `catalogSource ∈ {live, codex-cache, pi-config, droid-settings, curated, mixed, unavailable}`, `completeness ∈ {complete, partial, curated, unavailable}`, `totalCatalogModels`, `omittedCatalogModels`, `warnings[]`. Every row carries a per-row provenance `source` tag, so a mixed catalog is honest row-by-row. All I/O is injectable via `ModelCatalogDependencies { isInstalled?, readFile?, probeCodex?, probeAgy?, homeDir? }` — tests run the whole plane with fakes.

### Decisive source
```ts
// codex arm of collectBackend's switch — the soft-fallback ladder in full:
if (ctx.refresh) {
  const out = await deps.probeCodex();
  if (out !== undefined) {
    try {
      liveRows = parseCodexCatalog(JSON.parse(out));
    } catch {
      warnings.push('codex --refresh: could not parse live catalog; using cache');
    }
  } else {
    warnings.push('codex --refresh: probe failed; using cache');
  }
}
if (liveRows && liveRows.length > 0) {
  rows = liveRows.map(r => ({ ...r, source: 'live' as CatalogSource }));
  catalogSource = 'live';
  completeness = 'partial';
} else {
  const text = deps.readFile(join(deps.home, '.codex', 'models_cache.json'));
  if (text !== undefined) {
    try {
      rows = parseCodexCatalog(JSON.parse(text));
      catalogSource = rows.length > 0 ? 'codex-cache' : 'unavailable';
      ...
    } catch {
      warnings.push('codex: models_cache.json malformed; run with --refresh');
    }
  } else if (!ctx.refresh) {
    warnings.push('codex: no local cache; run with --refresh to fetch the live catalog');
  }
}
// defaultProbe — the live probe itself:
proc = Bun.spawn([command, ...args], { stdout: 'pipe', stderr: 'pipe' });
const timer = setTimeout(() => { try { proc?.kill(); } catch { /* noop */ } }, timeoutMs);
const stdout = proc.stdout;
if (typeof stdout === 'number') { clearTimeout(timer); return undefined; }
const text = await new Response(stdout).text();
await proc.exited;
clearTimeout(timer);
return text;   // any throw anywhere ⇒ catch ⇒ undefined ⇒ caller falls back
```

**Flow:** `collectModels`: scoped = `config.backend !== undefined`; backends = scoped ? `[backend]` : all five; unscoped + refresh emits one global warning ("live refresh applies to codex and agy; claude-code and droid have no live probe"); then per-backend `collectBackend` (sequential awaits). Per-backend ladder by capability: **codex** = live probe (`codex debug models`) → JSON → parser, else `~/.codex/models_cache.json`, else unavailable-with-warning; **claude-code** = static curated table always, refresh adds a "no live model discovery" note; **droid** = custom models from `~/.factory/settings.json` (whitelist parser) deduped over curated built-ins — full inventory when scoped, pre-collapsed family heads when unscoped; **pi** = user's own `~/.pi/agent/models.json`; **agy** = live probe (`agy models`) on refresh else curated table. Then `applyDisplayPolicy` (see `family-head-grouping.md`) caps/injects/orders, and the result always includes `defaultModel` from offline `resolveModelWithSource` even when the catalog is `unavailable`.
**Invariant:** no backend branch throws — every external read/probe is wrapped and degrades to a labeled warning plus an honest `catalogSource`/`completeness` tag; the default model is always resolvable offline (catalog availability never blocks execution); `detectBackends()` runs at most once per process (module-level `cachedDetect` memo); live probes are time-bounded (10s kill) and their failure is indistinguishable from "no data" at the call site (`string | undefined`).
**Probe:** `tests/agent/model-catalog.test.ts` (executed green at pin: 29 pass / 0 fail, 82 expect) — pins agy refresh fallback-to-curated with `/probe failed/i` warning, agy live success → `source:'live'` + `completeness:'complete'`, droid secret non-leak + alias-target-first ordering + customs-before-builtins, claude-code curated + `/no live model discovery/i` note, unscoped-refresh global note, pi cap/scoped-expansion/missing-config-`unavailable`/malformed-config-warning arms.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "collectBackend collectModels defaultProbe probeCodex probeAgy catalogSource", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape: a capability-table switch over backends where each arm owns its own source ladder (live probe → private local file → curated static → unavailable), per-row provenance tags, a two-axis honesty label (`catalogSource` × `completeness`), warning strings that tell the user the *remedy* ("run with --refresh"), fully injectable I/O dependencies, and a time-bounded spawn probe whose every failure path returns `undefined`. Adapt the backend list, file paths, curated tables, and the 10s/5-cap constants to your host. Omit nothing behavioral; do NOT copy the doc comment claiming probes "run concurrently" — the loop awaits sequentially (only two backends probe, so the delta is small, but port the code, not the comment). Keep the rule that the effective default is resolved independently of catalog success: a listing command must never make execution depend on discovery.
