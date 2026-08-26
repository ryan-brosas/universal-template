<!-- capsule-v2 -->
# Abortable semaphore — how do waiters leave a FIFO concurrency gate when aborted while queued?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the contract for a counted semaphore whose queue entries can be cancelled by an AbortSignal?

## Connected graph-selected seam
**Path/Symbol:** `src/agents/semaphore.ts` — `Semaphore.acquire` (:16-39), `#releaseFunction` (:41-56).
**Signature:** `acquire(signal?: AbortSignal)` → `Promise<() => void>` (the release function); constructor rejects non-positive/non-integer limits.
**Data Shape:** `#active: number`, FIFO `#waiters[]` of `{ resolve, reject, signal, abortHandler }`; pre-aborted signals reject IMMEDIATELY with "Operation aborted" without enqueueing.

### Decisive source
```ts
  #releaseFunction(): () => void {
    let released = false;
    return () => {
      if (released) return;                 // idempotent release
      released = true;
      const waiter = this.#waiters.shift();
      if (waiter) {
        if (waiter.signal && waiter.abortHandler) {
          waiter.signal.removeEventListener("abort", waiter.abortHandler);
        }
        waiter.resolve(this.#releaseFunction());   // permit HANDS OFF to next
        return;
      }
      this.#active--;
    };
  }
```

**Flow:** acquire under the limit resolves synchronously; otherwise the caller enqueues with an optional abort handler that splices ITSELF out of the queue and rejects. Release is permit-PASSING, not counter-decrement-then-wake: if anyone waits, the SAME slot transfers to the head waiter (whose listener is removed first so it can never double-fire), keeping `#active` untouched; only with an empty queue does `#active` decrement. Each release function is single-use via its `released` latch.
**Invariant:** a queued-then-aborted waiter can NEVER later be granted (self-splice + listener removal); double-release is inert; FIFO order preserved; aborting an already-acquired call does nothing — cancellation is the CALLER's job after acquire returns.
**Probe:** no dedicated upstream test file (`tests/` has no semaphore suite — consumers are exercised via agent-manager tests). Deterministic source pins: :17-18 pre-aborted fast-reject, :31-33 self-splice on abort, :42-44 idempotence latch. Coverage caveat stated honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "Semaphore acquire release waiters abort", limit: 5, fields: ["signature", "name", "file"] });
```
