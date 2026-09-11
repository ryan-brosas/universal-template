<!-- capsule-v2 -->
# V2 projection background-deferral ladder

## Source / Question
**Source:** teable `apps/nestjs-backend/src/features/v2/v2-record-history.service.ts` (652L, whole-file read pass 19) + `packages/v2/core/src/ports/ExecutionContext.ts` :117–160, :202–208.
**Question:** How do v2 history writes leave the request path WITHOUT leaking the request's transaction or its async context?

## Path / Symbol
`scheduleRecordHistoryRun(context, task, eventType)` (:44–62) → `withoutTransaction(context)` → `scheduleExecutionContextBackgroundTask(backgroundContext, ...)`.

## Signature
```ts
const scheduleRecordHistoryRun = (
  context: IExecutionContext,
  task: (backgroundContext: IExecutionContext) => Promise<void>,
  eventType: string
): void;   // fire-and-forget; handle() returns ok(undefined) immediately
```

## Data Shape
Background context = shallow copy with `transaction` and `transactions` DELETED. The scheduler ladder on IExecutionContext:
1. `context.scheduleBackgroundTask?.(task)` — injected scheduler (tests use this to capture+flush deterministically)
2. `setTimeout(task, 0)` with `.unref()`
3. `setImmediate` with `.unref()`
4. `queueMicrotask`
5. fall back to inline `void task()` — never drop the write

## Decisive source
```ts
const backgroundContext = withoutTransaction(context);   // strips tx so the INSERT
                                                          // cannot join/join-break the request tx
...
} catch (error) {
  recordHistoryProjectionLogger.error(`Error handling ${eventType} record history projection: ...`);
}                                                         // swallow: history failure NEVER fails the op
```
(:49–61)

## Flow / Invariant
1. **Deferral is contract, not optimization**: all three projections' `handle()` return ok BEFORE the insert runs; the direct spec asserts `expect(db.insertInto).not.toHaveBeenCalled()` at handle-time and only after `flushScheduled(scheduled)` — 3 such assertions in the spec.
2. **Transaction stripping is load-bearing**: a background task running after commit that reused the request tx handle would either fail (tx closed) or, worse, run inside an unrelated later transaction. `withoutTransaction` deletes BOTH `transaction` and scoped `transactions`.
3. **Actor attribution must come from the event snapshot**: every writer uses `context.actorId.toString()` captured at EVENT time — three copies of the comment "CLS (AsyncLocalStorage) is read at drain time, which runs in an unrelated request's async context, so it would attribute history to the wrong user" (:304–307, :411–414, :525–528). Porters who "simplify" this to CLS introduce cross-user attribution bugs under load.
4. **Error swallowing is deliberate**: history is best-effort telemetry of cell changes; a failed insert logs and moves on.
5. **The unref'd timer ladder** means Node won't be held alive by pending history writes at shutdown — graceful degradation over durability.

## Probe (direct tests)
Anchored at repo root:
```bash
grep -c withoutTransaction apps/nestjs-backend/src/features/v2/v2-record-history.service.ts            # → 2
grep -c 'unrelated' apps/nestjs-backend/src/features/v2/v2-record-history.service.ts                  # → 3
grep -cF 'not.toHaveBeenCalled' apps/nestjs-backend/src/features/v2/v2-record-history.service.spec.ts # → 3
grep -c 'unref' packages/v2/core/src/ports/ExecutionContext.ts                                        # → 6 (4 call sites incl. type decl)
```

## Retrieve
```bash
codebase-memory-mcp cli search_code '{"project":"teable","pattern":"scheduleRecordHistoryRun","limit":3}'
# → Function .../v2-record-history.service.ts 44-62 (+ both projection .handle sites)
```

## Verdict
**adopt** — the pattern (strip-tx background deferral + snapshot actor + swallow-and-log) ports to any projection/outbox-style side-write that must never extend request latency or couple to request transactions.
