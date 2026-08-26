<!-- capsule-v2 -->
# Pet animation state ladder — how do you map agent lifecycle events to sprite states without stomping user previews or one-shot emotes?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What precedence order resolves the displayed pet state among runtime, flash, preview, and configured idle states?

## State precedence
**Path/Symbol:** `src/pet-footer-controller.ts:currentState` (:296-303), `currentAnimation` (:305-313), event mapping `agentStart/toolStart/toolEnd/agentEnd` (:493-515), flashes `playFlash/scheduleIdleEmote` (:361-390), load coalescing `refresh` (:416-491).
**Signature:** `currentState(ctx, cfg?): PetState`; `playFlash(ctx, state): void`.
**Data Shape:** Layers: preview (settings hover) > active flash (timed one-shot) > runtime (thinking/tool/failed) > configured idle.

### Decisive source
```ts
private currentState(ctx, cfg = this.getConfig(ctx)): PetState {
  if (this.petPreviewState) return this.petPreviewState;
  const now = Date.now();
  if (this.petFlashState && this.petFlashUntil !== undefined && now < this.petFlashUntil)
    return this.petFlashState;
  if (this.petFlashState) this.clearFlash();            // expired → lazily drop
  return this.petRuntimeState === "idle" ? cfg.pets.state : this.petRuntimeState;
}

toolEnd(ctx, toolCallId, isError): void {
  this.activeToolCallIds.delete(toolCallId);            // per-tool ledger, not boolean
  const cfg = this.getConfig(ctx);
  this.petRuntimeState = this.activeToolCallIds.size > 0 ? cfg.pets.toolState : cfg.pets.thinkingState;
  if (isError) this.playFlash(ctx, cfg.pets.failedToolState, cfg);   // one-shot over base
}
```
Idle emotes schedule at jittered intervals (`interval × [0.75,1.5)`) and only fire when ALL guard conditions hold (enabled, images supported, no tools running, no preview/flash/freeze). Load refresh uses the same single-flight+queued-slot shape as usage with `shouldApplyLoadResult()` re-validating slug/size/protocol key AFTER await (:445-449).

**Flow:** agent_start clears tool ledger → thinkingState; tool_start adds id → toolState; tool_end removes id (+failure flash overlay); agent_end → idle→configured state; settings preview temporarily overrides all.
**Invariant:** Tool concurrency is tracked as a SET of ids — parallel tools keep the running state until the LAST ends; flashes never mutate the underlying runtime state (they expire); animation restarts when state CHANGES (`currentAnimation` resets the clock on transition).
**Probe:** `tests/footer.test.ts` (state transitions via extension events) + `tests/pets.test.ts` (:13-24 frame timing helpers `animationFrameAt`/`nextAnimationFrameDelayMs` pinning the clock math).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "petRuntimeState playFlash currentState currentAnimation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-layer precedence with set-based tool tracking and expiring overlays. Adapt state names/timings. Omit Codex pet assets.
