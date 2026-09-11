<!-- capsule-v2 -->
# base watch — how do sources normalize to one effect, and what forces a callback despite unchanged reads?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** What must a ported watch keep so ref/reactive/getter/array sources, deep traversal, immediate/once, and cleanup all behave identically?

## Source normalization + job gating in watch()
**Path/Symbol:** `packages/reactivity/src/watch.ts:watch` (:120-331), source ladder (:153-205), deep wrap (:207-211), `job` (:234-282), `traverse` (:333-369), `onWatcherCleanup` (:103-118), WatchErrorCodes (:31-35).
**Signature:** `watch(source: WatchSource | WatchSource[] | WatchEffect | object, cb?, options?: WatchOptions): WatchHandle` with `{immediate?, deep?: boolean|number, once?, scheduler?, call?}`.
**Data Shape:** INITIAL_WATCHER_VALUE sentinel `{}` distinguishes "never ran"; multi-source oldValues are an array of sentinels. cleanupMap: WeakMap<ReactiveEffect, (() => void)[]>; activeWatcher module global.

### Decisive source
```ts
// forceTrigger: shallow refs + reactive objects fire even when the READ set is unchanged
if (isRef(source)) { getter = () => source.value; forceTrigger = isShallow(source) }
else if (isReactive(source)) { getter = () => reactiveGetter(source); forceTrigger = true }
else if (isArray(source)) { isMultiSource = true
  forceTrigger = source.some(s => isReactive(s) || isShallow(s)); getter = () => source.map(/* per-source read */) }
// job gate: dirty check first (scheduler-driven flushes skip clean effects)
const job = (immediateFirstRun?) => {
  if (!(effect.flags & ACTIVE) || (!effect.dirty && !immediateFirstRun)) return
  if (cb) {
    const newValue = effect.run()
    if (immediateFirstRun || deep || forceTrigger || hasChanged(newValue, oldValue)) { /* cleanup -> cb */ }
  } else effect.run()   // watchEffect path
}
```

**Flow:** source kind → getter + forceTrigger flag → `deep:true` wraps baseGetter with depth-limited traverse (numeric deep = maxDepth; seen-Map keyed by object+depth prevents cycles) → ReactiveEffect created with scheduler=job → initial run seeds oldValue (or immediate fires cb with undefined old) → later triggers run job which re-reads via effect.run() and compares.
**Invariant:** A reactive OBJECT source always calls its callback on trigger (deep or not — forceTrigger=true) because mutation identity is unknowable; once-wrapping stops the handle AFTER the callback returns; watcher cleanups run before each re-run AND at stop (onStop hook). The `call` option exists solely so runtime-core can route errors to app-level handlers without re-implementing watch.
**Probe:** `packages/runtime-core/__tests__/apiWatch.spec.ts:276` (`watching multiple sources` — vals/oldVals arrays pinned) + reactivity `watch.spec.ts:239` (`once option should be ignored by simple watch`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "watch traverse getter", limit: 10 });
```

## Verdict
Adopt the normalization table and forceTrigger semantics verbatim. Adapt scheduler/call plumbing to your host's flush+error systems. Omit augmentJob/onWarn internals unless embedding in a Vue-compatible runtime.
