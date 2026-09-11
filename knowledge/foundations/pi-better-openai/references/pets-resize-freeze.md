<!-- capsule-v2 -->
# Resize-freeze choreography — how do you stop terminal image animation during a resize without torn frames or leaked placements?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What is the freeze window protocol between a resize event and the first post-resize render?

## Resize guard
**Path/Symbol:** `src/pet-footer-controller.ts:freezeForResize` (:267-282), `installResizeGuard` (:284-294), `isResizeFrozen` (:257-259), `PET_RESIZE_FREEZE_MS=120` (:18); footer-side size-key trigger `index.ts` :975-980; kitty reset inside the unfreeze timer :274-280.
**Signature:** `freezeForResize(ctx, now?): void`; `isResizeFrozen(now?): boolean`.
**Data Shape:** A deadline timestamp + armed one-shot unref'd timer; footer compares `${width}:${rows}` keys across renders.

### Decisive source
```ts
freezeForResize(ctx, now = Date.now()): void {
  this.petResizeFreezeUntil = now + PET_RESIZE_FREEZE_MS;
  this.queueKittyCleanup();       // batch-delete placements/images AFTER unfreeze
  this.stopAnimation();
  this.stopIdleEmotes();
  this.stopPendingRenderRequest();
  this.petResizeTimer = setTimeout(() => {
    this.petResizeFreezeUntil = 0;
    this.petKittyManager.resetForResize(this.pet);   // invalidate id ledger
    this.resetRenderCache();                          // stale-size lines dropped
    this.updateFooter(ctx);                           // first clean re-render
  }, PET_RESIZE_FREEZE_MS);
  this.petResizeTimer.unref?.();
}
// render(): const freezePetFrame = petController.isResizeFrozen(now);
// frozen renders emit PLACEHOLDER lines sized like the frame (no image payloads)
```

**Flow:** resize observed (stdout 'resize' listener AND footer width/rows key change) → freeze deadline set + all timers stopped + cleanup queued → frozen renders emit blank placeholders preserving layout height → 120ms later: reset kitty ids + render cache → single authoritative re-render.
**Invariant:** During the freeze NO image sequences are emitted at all (placeholders only) — this prevents interleaved stale-size kitty payloads that would paint outside the new viewport; queued deletions apply AFTER the terminal settles, not mid-resize.
**Probe:** `tests/footer.test.ts` (footer resize/freeze integration scenarios).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "freezeForResize installResizeGuard petPlaceholderLines", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt deadline+placeholder freeze with deferred kitty reset. Adapt freeze duration and resize detection to your TUI. Omit pi footer plumbing.
