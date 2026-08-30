<!-- capsule-v2 -->
# Plugin loader pipeline — how do you load external plugins without one bad plugin killing the host?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65ad6334de3e4e68dedc201d5fbb828c9fe`; Codebase Memory `opencode`. **Question:** How does opencode resolve, validate, and import every configured plugin while guaranteeing a single broken plugin never aborts the rest?

## Loader state machine
**Path/Symbol:** `packages/opencode/src/plugin/loader.ts` (`PluginLoader.resolve/load/attempt/loadExternal`, lines 86-236).
**Signature:** `resolve(plan, kind): Promise<{ok:true,value:Resolved} | {ok:false,stage:"missing"|"install"|"entry"|"compatibility",...}>`; `loadExternal<R>(input): Promise<R[]>`.
**Data Shape:** Input items are `ConfigPlugin.Origin[]` = `{ spec, source, scope }`; each becomes a normalized `Plan = { spec, options, deprecated }`. Output is `R[]` in input order with failed candidates silently dropped. The four failure stages (`install` → target resolution, `entry` → entrypoint detection, `missing` → package exists but no such entrypoint, `compatibility` → engines.opencode gate) plus `load` (dynamic import) each map to a distinct user-facing diagnostic.

### Decisive source
```ts
// loader.ts:208-236 — all attempts start in parallel, retries are sequential and file-only
export async function loadExternal<R = Loaded>(input: Input<R>): Promise<R[]> {
  const candidates = input.items.map((origin) => ({ origin, plan: plan(origin.spec) }))
  const list: Array<Promise<AttemptResult<R>>> = []
  for (const candidate of candidates) {
    list.push(attempt(candidate, input.kind, false, input.finish, input.missing, input.report))
  }
  const out = await Promise.all(list)
  if (input.wait) {
    let deps: Promise<void> | undefined
    for (let i = 0; i < candidates.length; i++) {
      const previous = out[i]
      if (previous?.value !== undefined) continue
      if (previous?.retry !== true) continue
      const candidate = candidates[i]
      if (!candidate || pluginSource(candidate.plan.spec) !== "file") continue
      deps ??= input.wait()
      await deps
      out[i] = await attempt(candidate, input.kind, true, input.finish, input.missing, input.report)
    }
  }
  const ready: R[] = []
  for (const item of out) if (item.value !== undefined) ready.push(item.value)
  return ready
}
```

**Flow:** plan(spec) → resolve (install→entry→compatibility, each stage returning early with its own error tag) → missing-entry branch lets callers salvage package metadata (themes from a TUI-less package) → load (dynamic import) → finish() adapts to caller shape → results collected in original order.
**Invariant:** Only *pre-import* file-plugin setup failures are retryable — exactly `stage==="install"` whose message includes `"missing package.json or index file"` (`isRetryableResolveError`). After a dynamic import has run, failures are permanent for the process because **Bun caches failed module resolution**, so `wait()`+retry can never fix them; npm plugins never wait or retry at all. Deprecated packages (`opencode-openai-codex-auth`, `opencode-copilot-auth`) are silently dropped before any report callback fires.
**Probe:** `packages/opencode/test/plugin/loader-shared.test.ts` — `it.live("retries failed file plugins once after wait and keeps order")` (:1137, asserts wait===1 and call order `[a,false],[b,false],[a,true],[b,true]`); `it.live("does not retry permanent file plugin entry errors")` (:1186, errors===[["entry",false]], wait===0); `it.live("does not wait or retry npm plugin failures")` (:1270).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "PluginLoader loadExternal plugin retry", limit: 10 });
```

## Verdict
Adopt the staged resolve/missing/error taxonomy, the parallel-first-attempt + shared-single-wait retry choreography, and the Bun-failed-import-is-permanent boundary. Adapt the `Report` callbacks to your logging/event surface. Omit Effect/Bun specifics (`Effect.promise(() => import(...))`) by substituting your runtime's dynamic import semantics — but re-derive whether YOUR bundler caches failed imports before keeping any retry-after-import path.
