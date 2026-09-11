<!-- capsule-v2 -->
# Footer surface state machine — how do you arbitrate between a full custom footer, a status widget, and a plain status line as config and pets change?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What are the install/clear rules that keep footer ownership consistent across mode toggles?

## Surface arbitration
**Path/Symbol:** `index.ts:updateFooter` (:1185-1220), `installFooter` (:949-1151), `clearFooter` (:1153-1159), `setStatus/setStatusWidget` installed-latches (:1161-1183).
**Signature:** `updateFooter(ctx): void` — the single recompute point called by every event handler.
**Data Shape:** Three surfaces: full footer renderer (owns pet lines + usage + stats), belowEditor widget, key-value status line; each guarded by an `*Installed` boolean.

### Decisive source
```ts
petController.updateActivity(ctx, cfg);
const shouldRenderPet = petController.shouldRenderInFooter(cfg);

if (cfg.footer.mode === "replace" || shouldRenderPet) {
  setStatus(ctx, undefined); setStatusWidget(ctx, undefined);
  installFooter(ctx); return;                 // full footer owns everything
}
clearFooter(ctx); setStatus(ctx, undefined);   // non-TUI-grade modes shed the footer
if (cfg.footer.mode === "off") { setStatusWidget(ctx, undefined); return; }
setStatusWidget(ctx, [fast, usage].filter(Boolean).join(" | ") || undefined);

function setStatus(ctx, text) {
  if (!text && !statusInstalled) return;      // latch: never clear what isn't ours
  ctx.ui.setStatus(STATUS_KEY, text);
  statusInstalled = text !== undefined;
}
```
Install path is idempotent (`footerInstalled` early-return re-requests render instead of double-install :950-954); dispose detaches listeners, stops timers, flushes kitty images, and flips the latch (:959-968).

**Flow:** any state change (session/model/turn/settings/pet) → updateFooter → pick owning surface from footer.mode + pet visibility → tear down others via latched setters → install/update owner.
**Invariant:** Exactly one surface owns presentation at a time; latched setters make redundant set/clear calls no-ops so unrelated events don't clobber other extensions' status slots; the pet's presence ESCALATES presentation to the full footer regardless of footer.mode.
**Probe:** `tests/footer.test.ts` (mode transitions + pet-driven escalation through the composed default export).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "updateFooter installFooter clearFooter statusInstalled", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-recompute-point + latched install flags + pet-escalation rule. Adapt surface names to your host UI. Omit pi-specific footerData hooks.
