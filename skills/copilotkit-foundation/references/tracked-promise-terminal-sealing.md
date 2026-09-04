<!-- capsule-v2 -->
# ObservableTrackedPromise & terminal sealing — how do you wait for handler promises whose rejections the handler never caught?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** Before sending a delivery terminal, you must wait for every in-flight Thread operation — but a promise nobody `.catch`-ed would crash the process. How is unobserved rejection detected without unhandled-rejection noise?

## Rejection-consumption-tracking Promise subclass
**Path/Symbol:** `packages/channels-intelligence/src/delivery-transport.ts:ObservableTrackedPromise` (:219-260), `ClaimedChannelDelivery.trackOperation` (:477-515), `sealAndWaitForTrackedOperations` (:579-589), fields `trackedOperations`/`unobservedOperationFailures`/`trackedOperationsSealed` (:268-273).
**Signature:** `trackOperation<T>(operation: () => Promise<T>): Promise<T>`; subclass overrides `then`/`catch`/`finally`, pins `Symbol.species` to `Promise`.
**Data Shape:** internal bookkeeping = `Set<Promise>` (live ops) + `Map<Promise, unknown>` (rejections no consumer has observed).

### Decisive source
```typescript
class ObservableTrackedPromise<T> extends Promise<T> {
  static get [Symbol.species](): PromiseConstructor { return Promise; }
  constructor(private readonly operation: Promise<T>,
              private readonly observeRejection: () => void) {
    super((resolve, reject) => operation.then(resolve, reject));
    void Promise.prototype.then.call(this, undefined, () => undefined); // swallow internally
  }
  override then(onfulfilled?, onrejected?) {
    if (onrejected) this.observeRejection();   // a consumer IS handling it
    return new ObservableTrackedPromise(this.operation.then(onfulfilled, onrejected), this.observeRejection);
  }
  // catch/finally mirror this ...
}

// trackOperation wires it up:
let rejectionObserved = false;
void tracked.then(() => this.trackedOperations.delete(tracked),
  (error) => { this.trackedOperations.delete(tracked);
    if (!rejectionObserved) this.unobservedOperationFailures.set(tracked, error); });
try { void operation().then(resolveTracked, rejectTracked); }
catch (error) { rejectTracked(error); }        // sync throw becomes rejection
return new ObservableTrackedPromise(tracked, () => {
  rejectionObserved = true;
  this.unobservedOperationFailures.delete(tracked);
});

private async sealAndWaitForTrackedOperations(throwOnFailure: boolean): Promise<void> {
  this.trackedOperationsSealed = true;
  while (this.trackedOperations.size > 0) await Promise.allSettled(this.trackedOperations);
  const failure = this.unobservedOperationFailures.values().next().value;
  this.unobservedOperationFailures.clear();
  if (throwOnFailure && failure !== undefined) throw failure;
}
```

**Flow:** every public Thread operation registers through `trackOperation` → live ops sit in the set until settle → the subclass's internal pre-swallow keeps unhandled rejections from firing while `then/catch/finally` calls mark the rejection OBSERVED and delete it from the failure map → `terminal()` seals registration (`ChannelDeliveryOperationsClosedError` for late arrivals), drains with `allSettled` in a loop (ops may register ops), then rethrows the FIRST unobserved failure only when the terminal status is `"complete"`.
**Invariant:** Failure semantics: a failed operation does not block a `failed`/`uncertain` terminal, but MUST block a `complete` terminal — otherwise a delivery reports success over a broken handler run. Sealing turns late operations into typed errors instead of silent races.
**Probe:** `packages/channels-intelligence/src/delivery-transport.test.ts` :1264 "still sends a failed terminal when complete terminal fails"; :1136 "commits irreversible work exactly once...". Deterministic anchor `grep -n "unobservedOperationFailures" packages/channels-intelligence/src/delivery-transport.ts | head -2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "ObservableTrackedPromise trackOperation sealAndWaitForTrackedOperations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the observation-tracking wrapper for any "await all children before finalizing" barrier. Adapt the sealing error type to your domain. Omit the species pin and chained promises lose the tracking behavior.
