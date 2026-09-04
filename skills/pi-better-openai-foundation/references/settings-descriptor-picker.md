<!-- capsule-v2 -->
# Descriptor-driven settings picker — how do you build a searchable multi-section settings UI where each write triggers the right side effects?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** How are settings sections/items generated from declarative descriptors, and what invalidation does each write fan out?

## Settings machinery
**Path/Symbol:** `index.ts:settingsItemsFromDescriptors` (:567-583), `settingsSubmenu` (:359-528), `writeSetting` (:780-810), section builders (:654-778).
**Signature:** `settingsItemsFromDescriptors(descriptors, cfg, overrides?): SettingsPickerItem[]`; `writeSetting(ctx, id, rawValue): void`.
**Data Shape:** Item = `{id, label, currentValue, values?, description?, submenu?}`; descriptors carry `currentValue(cfg)` closures so items always reflect LIVE config.

### Decisive source
```ts
function writeSetting(ctx, id, rawValue): void {
  const cfg = refresh(ctx);                       // re-read from disk FIRST
  const nextRawConfig = applySettingToRawConfig(current, id, rawValue, {...});
  const petKey = id.startsWith("pets.") ? id.slice(5) : undefined;
  if (petKey) {
    if (petKey === "enabled" || petKey === "sizeCells" || petKey === "slug")
      petController.invalidateLoadKey();          // asset identity changed → reload
    if (petKey === "placement" || petKey === "sizeCells" || petKey === "slug")
      petController.resetRenderCache();           // geometry changed → rerender
    if (petKey === "idleEmotes" || petKey === "idleEmoteIntervalMs")
      petController.stopIdleEmotes();             // timer params changed → reschedule
  }
  writeConfig(cfg.configPath, nextRawConfig);
  const next = refresh(ctx);
  if (id.startsWith("usage.")) usageController.restartAfterSettingsChange(ctx, next);
  updateFooter(ctx);
}
```
Submenu picker behavior: type-to-search filter, clamped selection across refiltering, ←→/Enter/Space cycle-or-open-submenu, nested submenu stack restoring the parent selection index on close (:397-428); pet preview hooks ride `onSelection/onClose/renderExtra` (:735-763).

**Flow:** descriptor list (+per-id overrides e.g. live pet slugs) → picker renders current cfg via closures → user writes route through ONE choke point (`writeSetting`) that maps id-prefixes to precise invalidations, persists raw config, then refreshes dependents.
**Invariant:** Every mutation goes through read-modify-write of the RAW config preserving unknown fields; invalidation is keyed by WHICH field changed — not a blanket reset; UI values always come from fresh `resolveConfig` (closures), never stale snapshots.
**Probe:** `tests/config.test.ts` (applySettingToRawConfig semantics) + `tests/footer.test.ts` (picker-driven updates).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "settingsItemsFromDescriptors writeSetting applySettingToRawConfig", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt descriptor-driven items + single write choke point with field-keyed invalidation. Adapt descriptor schema to your settings domain. Omit the pi-tui component specifics.
