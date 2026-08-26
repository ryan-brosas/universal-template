<!-- capsule-v2 -->
# Persist overlay mirroring — how do you keep a live in-memory controller state and its persisted config file from drifting when persistence is optional?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** Where must runtime-only fields (desired vs active toggle state) be mirrored into a config write, and what happens on disk when the user disabled persistence?

## Overlay-then-conditional-write
**Path/Symbol:** `index.ts:persist` (:204-216), cache slot `cachedConfig` (:180) + `refresh` (:195-198); consumer `setActive` (:227-237); sibling raw-writer `writePetConfig` (:218-225); session-start reconciliation (:1226-1231).
**Signature:** `function persist(nextConfig: ResolvedConfig): void`.
**Data Shape:** `persist` takes a freshly-resolved config, overlays LIVE controller state `{active, desiredActive}` from `FastController`, then conditionally writes `{...readRawConfig(configPath), active, desiredActive}` to disk. The in-memory overlay is UNCONDITIONAL; the disk write is gated on `nextConfig.persistState`.

### Decisive source
```ts
function persist(nextConfig: ResolvedConfig): void {
  cachedConfig = {                       // (1) memory mirror ALWAYS
    ...nextConfig,
    active: fastController.active,
    desiredActive: fastController.desiredActive,
  };
  if (!nextConfig.persistState) return;  // (2) disk write only if persisting
  writeConfig(nextConfig.configPath, {
    ...readRawConfig(nextConfig.configPath),
    active: fastController.active,       // (3) read-modify-write preserves unknown keys
    desiredActive: fastController.desiredActive,
  });
}
```

**Flow:** any state change (`/fast`, settings picker, model_select reconciliation) → refresh config from disk → mutate controller → `persist()` → `updateFooter`. On next session start, `resolveConfig` reads `active/desiredActive` back ONLY if they were written; `session_start` re-derives from flag + file and re-persists when the derived pair differs (:1226-1231).

**Invariant:** The cached resolved config and the controller are ONE source of truth after every mutation — forgetting step (1) makes the UI lie until some other path calls `refresh()`, while writing the file unconditionally would clobber a user's explicit "don't persist" choice. The disk write is read-modify-write so unrelated user keys survive. Note `applySettingToRawConfig` (config capsule) enforces the same gate at the descriptor layer — `fast.enabled` writes `active/desiredActive` into RAW config only when `persistState` is true; `persist()` is the imperative twin for non-settings mutations.

**Probe:** `tests/config.test.ts:239-250` — with `persistState:true`, applying a setting yields `{active:true, desiredActive:true, unknown:"preserved"}`; with `persistState:false` the result `.not.toHaveProperty("active")`. Round-trip through the composition root: `tests/fast.test.ts:174` "/fast toggles injection on" — `/fast` handler → setActive → persist → subsequent `before_provider_request` injects `service_tier:"priority"` without a restart. Coverage caveat: `persist()`'s own early-return branch has no dedicated unit test; pinned by source :210.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "persist writeSetting refresh cachedConfig", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-layer rule: mirror runtime state into the cached resolved view unconditionally, touch durable storage only behind the persistence gate, always via read-modify-write. Adapt which fields count as runtime-only. Omit pi-specific `ResolvedConfig` plumbing.
