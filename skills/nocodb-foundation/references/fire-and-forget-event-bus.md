<!-- capsule-v2 -->
# Fire-and-forget event bus — how do you let one throwing webhook listener take down the process, and then prevent it?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What does the void-returning emit() hide about listener error propagation, and what is the minimal fix?

## Discarded-promise catch-all
**Path/Symbol:** `packages/nocodb/src/modules/event-emitter/fallback-event-emitter.ts:FallbackEventEmitter.emit` (:14–29); interface `event-emitter.interface.ts`; module wiring `event-emitter.module.ts` (@Global, provide 'IEventEmitter' → FallbackEventEmitter); twin `nestjs-event-emitter.ts` (same 4-method shape over EventEmitter2).
**Signature:** `emit(event: string, data: any): void`; `on(event, listener): () => void` (returns unsubscribe); `removeListener(event, listener)`, `removeAllListeners(event?)`.
**Data Shape:** Emittery instance; single payload arg per event; on() returns an OFF closure.

### Decisive source
```ts
// `emit` is fire-and-forget (returns void), but `Emittery.emit` returns a
// promise that rejects if ANY listener rejects (it does
// `await Promise.all(listeners)`). Discarding that promise means a single
// throwing listener — e.g. `checkLimit` raising `Forbidden` inside the
// `HANDLE_WEBHOOK` handler — surfaces as an `unhandledRejection` that takes
// the whole process down. Attach a catch so one misbehaving listener can
// never crash the server; listeners that need their own error context still
// wrap their own bodies.
this.emitter.emit(event, data).catch((e) => {
  this.logger.error(
    `Unhandled error in '${event}' event listener: ${e?.message ?? e}`,
    e?.stack,
  );
});
```
(:15–:28)

**Flow:** any service emits domain events through the 'IEventEmitter' token → FallbackEventEmitter serializes each listener's promise via Emittery's internal Promise.all → one rejection would reject the WHOLE emit chain; the .catch converts process-fatal unhandledRejection into a logged error naming the event.
**Invariant:** emit() keeps its synchronous void signature (call sites never await), so the catch must live INSIDE the emitter, not at call sites. The Nestjs twin delegates to EventEmitter2's own fire-and-forget semantics but must keep the identical 4-method surface — the DI factory swaps implementations without touching consumers. removeAllListeners maps to Emittery.clearListeners(event).
**Probe:** `cd packages/nocodb && grep -c "\.catch(" src/modules/event-emitter/fallback-event-emitter.ts` (=1) and `grep -c "Emittery" src/modules/event-emitter/fallback-event-emitter.ts` (=4: import/type/ctor/comment×2 counted by substring).
**Direct test:** none upstream for modules/event-emitter/ — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "FallbackEventEmitter Emittery IEventEmitter emit catch", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the in-emitter catch-all + unsubscribe-returning on(); adapt logging transport; omit only if your bus already isolates listener failures. Coverage caveat: grep-pinned only.
