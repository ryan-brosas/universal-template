<!-- capsule-v2 -->
# Logger static boot buffer — how do pre-boot logs get replayed after a custom logger arrives?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How can every `Logger.log()` call made before the app picks its logger be captured and re-emitted later, without changing any call site?

## WrapBuffer / attachBuffer / flush / localInstance / overrideLogger
**Path/Symbol:** `packages/common/services/logger.service.ts:WrapBuffer` (:96-112), `attachBuffer` (:296-298), `detachBuffer` (:304-306), `flush` (:284-290), `localInstance` getter (:122-132), `registerLocalInstanceRef` (:334-343), `overrideLogger` (:312-327).
**Signature:** `private static WrapBuffer: MethodDecorator` (replaces `descriptor.value`); `static flush(): void`; module singleton `DEFAULT_LOGGER = new ConsoleLogger()`.
**Data Shape:** `logBuffer: LogBufferRecord[] = { methodRef: originalFn.bind(this), arguments }[]`; `staticInstanceRef?: LoggerService = DEFAULT_LOGGER`; `isBufferAttached: boolean`.

### Decisive source
```ts
const originalFn = descriptor.value;
descriptor.value = function (...args: unknown[]) {
  if (Logger.isBufferAttached) {
    Logger.logBuffer.push({ methodRef: originalFn.bind(this), arguments: args });
    return;                                   // swallow the call entirely
  }
  return originalFn.call(this, ...args);
};

// flush — detach FIRST so replays go to the real logger, then drain in order:
static flush() {
  this.isBufferAttached = false;
  this.logBuffer.forEach(item => item.methodRef(...(item.arguments as [string])));
  this.logBuffer = [];
}
```

**Flow:** boot (`NestFactory.create` with `bufferLogs:true`, nest-factory.ts :325) → `attachBuffer()` → EVERY decorated method (instance log/warn/debug/verbose/fatal/error + all statics) records `(bound fn, raw args)` instead of printing → app resolves its real logger → `useLogger()`/`flushLogsOnOverride` triggers `Logger.flush()` (:nest-application-context.ts:296) → detach-then-drain replays each record against whatever logger is THEN installed.
**Invariant:** (1) Buffer stores the ORIGINAL function bound to its receiver plus RAW arguments — level filtering and context formatting are deferred, not decided at record time. (2) `isBufferAttached=false` happens BEFORE draining or replayed records would re-buffer forever. (3) The instance getter ladder: default logger ⇒ build a per-instance ConsoleLogger carrying THIS context + static logLevels; a Logger-subclass static ref ⇒ also per-instance; anything else ⇒ delegate straight to it. (4) `error(message, stack?, context?)`: only error() splices `this.context` AFTER an existing first param (`(optionalParams.length ? optionalParams : [undefined]).concat(this.context)` — the `[undefined]` placeholder RESERVES the stack slot); other levels just concat.
**Probe:** `packages/common/test/services/logger.service.spec.ts` ("when custom logger is being used" :347 calls custom `#log/#error` through the same path; stack-slot ordering asserted by "should print one error to the console with stacktrace" :82). Boot wiring pinned at `packages/core/nest-factory.ts:325` (`bufferLogs → attachBuffer`) + `packages/core/nest-application-context.ts:295-301`.
**Coverage caveat:** no dedicated spec asserts WrapBuffer/flush directly (buffer path exercised indirectly via factory options) — source-grounded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "Logger WrapBuffer logBuffer attachBuffer flush overrideLogger", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the decorate-all-methods static buffer for any "capture early, replay later" logging bootstrap; adapt the trigger (here: useLogger + autoFlushLogs flag); omit the extend-Logger ban unless you have the same subclassing hazard. Porting wrong: storing formatted output instead of (fn, args) — buffered lines never honor a logger configured later; flushing before detaching — infinite buffer growth.
