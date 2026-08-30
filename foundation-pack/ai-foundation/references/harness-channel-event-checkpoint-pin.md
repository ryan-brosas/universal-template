<!-- capsule-v2 -->
# SandboxChannel event checkpoint — how can a consumer suspend AT an already-dispatched boundary event?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The default suspend cursor means "everything delivered" — but a slice wants to resume from a boundary event it ALREADY consumed (e.g. finish-step), replaying the tail. How is that pinned without changing the event payload or leaking across bundle copies?

## Symbol.for checkpoint property with token-guarded unpin
**Path/Symbol:** `packages/harness/src/utils/sandbox-channel.ts` — symbol + type (:78–89), `pinSandboxChannelEventCheckpoint` (:91–100), stamping in `attachEventCheckpoint` (:500–518), pin consumption in `suspend` (:304, :313–315).
**Signature:** `pinSandboxChannelEventCheckpoint(event: unknown): (() => void) | undefined`.
**Data Shape:** non-enumerable own property `[Symbol.for('vercel.ai.harness.sandboxChannelEventCheckpoint')] = { pin(): () => void }`; channel-side `pinnedSuspensionCursor: { eventId: number; token: object } | undefined`.

### Decisive source
```ts
// sandbox-channel.ts:78 — WHY Symbol.for
// The agent and utilities entrypoints bundle this module separately. A global
// symbol lets the agent recognize metadata attached by the channel's bundle
// copy, while the non-enumerable property leaves protocol payloads unchanged.
const sandboxChannelEventCheckpointSymbol = Symbol.for(
  'vercel.ai.harness.sandboxChannelEventCheckpoint',
);
...
private attachEventCheckpoint({ event, eventId }) {
  if (!Object.isExtensible(options.event)) return;      // frozen payloads skipped
  Object.defineProperty(options.event, sandboxChannelEventCheckpointSymbol, {
    value: { pin: () => {
      const token = {};
      this.pinnedSuspensionCursor = { eventId: options.eventId, token };
      return () => {                                    // unpin only MY OWN pin
        if (this.pinnedSuspensionCursor?.token === token)
          this.pinnedSuspensionCursor = undefined;
      };
    }},                                                  // enumerable:false default
  });
}
```

**Flow:** every validated inbound frame carrying a numeric `seq` gets stamped → a consumer holding a boundary event (e.g. finish-step) calls its `pin()` → suspend() then resolves to THAT eventId even though later events (seq 2,3…) were already dispatched → next process resumes with that cursor and replays the dispatched tail exactly once → releasing the checkpoint returns suspension to the latest cursor.
**Invariant:** Stamping must be invisible to JSON serialization and schema validation (non-enumerable, set AFTER validation succeeds); unpin is token-guarded so multiple concurrent pins resolve latest-wins without one consumer clearing another's; frozen/non-extensible events are silently unstamped; `Symbol.for` (not `Symbol`) because producer and reader may be DIFFERENT BUNDLES of the same module.
**Probe:** direct tests `packages/harness/src/utils/sandbox-channel.test.ts:165–190` ("suspends from a pinned event even after later events were dispatched" — suspend resolves **1** while lastSeenEventId is 3), :192–213 ("returns to the latest cursor after releasing a checkpoint" — after release, suspend resolves 2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "pinSandboxChannelEventCheckpoint attachEventCheckpoint", limit: 5 });
// verified live @9d9a73f — pinSandboxChannelEventCheckpoint :91-100 rank#1; SandboxChannel.attachEventCheckpoint :500-518
```

## Verdict
Adopt global-symbol metadata stamping for cross-bundle event annotation where payloads must stay wire-clean; adapt the pin/unpin API to host lifecycle (upstream pairs it with turn-boundary checkpoints in run-prompt); omit if your slices always resume from "everything delivered". Caveat: none — both pin behaviors unit-pinned.
