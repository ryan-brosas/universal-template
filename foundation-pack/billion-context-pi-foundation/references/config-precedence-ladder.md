<!-- capsule-v2 -->
# Config precedence ladder — how do env, factory config, live host state, and user JSON compose without one silently beating another?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** In what order must layered configuration resolve, and which keys are user-overridable at runtime?

## Token limit: env > adapter > live window > fallback. User acp.json: wins EXCEPT kernel-safety keys
**Path/Symbol:** `src/config.ts`: `resolveConfig` (:48-65), `AdapterConfig` (:7-43); `src/user-config.ts`: `loadUserConfig` (:22-42), `applyUserConfig` (:60-70).
**Signature:** `resolveConfig(adapter, liveContextLimit) -> Config` with `FALLBACK_LIMIT = 150_000`; `applyUserConfig(adapter, user)` re-pins `coreOverrides`/`protectedTools`/`preserveRecentMessages` from the FACTORY after spreading user keys.
**Data Shape:** user files: global `~/.<CONFIG_DIR>/acp.json` then project `<cwd>/.<CONFIG_DIR>/acp.json` (project wins); unknown keys filtered by a KNOWN allowlist set.

### Decisive source
```ts
// config.ts:52-59 — the ladder:
const limit =
  !Number.isNaN(envLimitNum) && envLimitNum > 0 ? envLimitNum        // ACP_MODEL_CONTEXT_LIMIT
  : adapter.modelContextLimit && adapter.modelContextLimit > 0 ? adapter.modelContextLimit
  : liveContextLimit > 0 ? liveContextLimit                          // ctx.getContextUsage()
  : FALLBACK_LIMIT;                                                  // 150k
```

```ts
// user-config.ts:63-68 — what the user may NOT override:
// coreOverrides / protectedTools / preserveRecentMessages are not overridable
// from acp.json (keep them from the factory config).
```

**Flow:** session_start loads both user files (missing → skip; bad JSON → warn-and-continue; NEVER throw) → merge onto the factory adapter via spread with the three safety keys re-applied AFTER the spread → every turn `configFor(ctx)` recomputes the token limit because "ctx.model.contextWindow can be stale or unset for some providers" (runtime.ts:134-141 prefers pi's reported contextWindow). Live limit is read per-turn, not cached.
**Invariant:** (1) explicit env beats code defaults; a live value beats nothing but never beats explicit configuration. (2) A fixed allowlist of user-settable keys keeps kernel invariants (protected tools, recent-message preservation) out of user reach. (3) User-config load failures degrade to factory defaults — configuration errors can't take down the extension.
**Probe:** `tests/config.test.ts` + `tests/user-config.test.ts` suites cover resolution and merge behavior (see tests/config.test.ts, tests/user-config.test.ts).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "resolveConfig loadUserConfig applyUserConfig AdapterConfig", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-rung ladder and the re-pin-after-spread pattern for any tool with layered config. Adapt key names/fallback size. Omit the specific KNOWN key set (product data).
