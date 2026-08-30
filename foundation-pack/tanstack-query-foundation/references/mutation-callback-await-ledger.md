<!-- capsule-v2 -->
# Mutation.execute await ledger + error isolation — in what exact order do mutation callbacks run, and who owns their errors?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** With cache-config callbacks AND hook-level callbacks on success/error/settled, what runs first, what's awaited, and what happens when one throws?

## execute callback chain
**Path/Symbol:** `packages/query-core/src/mutation.ts:Mutation.execute` (:176–337).
**Signature:** `async execute(variables): Promise<TData>`; retryer built with `retry ?? 0` (mutations DON'T retry by default) and `canRun: () => this.#mutationCache.canRun(this)`.
**Data Shape:** state.context = onMutate result; restored flag from pre-existing pending state.

### Decisive source
```ts
const data = await retryer.start()
await this.#mutationCache.config.onSuccess?.(data, variables, this.state.context, ...)
await this.options.onSuccess?.(data, variables, this.state.context!, ...)
await this.#mutationCache.config.onSettled?.(data, null, ...)
await this.options.onSettled?.(data, null, ...)
this.#dispatch({ type: 'success', data })
return data
} catch (error) {
  try { await this.#mutationCache.config.onError?.(...) } catch (e) { void Promise.reject(e) }
  try { await this.options.onError?.(...) }          catch (e) { void Promise.reject(e) }
  try { await this.#mutationCache.config.onSettled?.(undefined, error, ...) } catch (e) { void Promise.reject(e) }
  try { await this.options.onSettled?.(undefined, error, ...) }               catch (e) { void Promise.reject(e) }
  this.#dispatch({ type: 'error', error })
  throw error
} finally {
  if (this.#retryer === retryer) this.#retryer = undefined
  this.#mutationCache.runNext(this)
}
```
and the restore path:
```ts
const restored = this.state.status === 'pending'
...
if (restored) {
  onContinue()                       // dehydrated-then-rehydrated mutation resumes
} else {
  this.#dispatch({ type: 'pending', variables, isPaused })
  if (this.#mutationCache.config.onMutate) await this.#mutationCache.config.onMutate(...)
  const context = await this.options.onMutate?.(...)
  if (context !== this.state.context) this.#dispatch({ type: 'pending', context, variables, isPaused })
}
```

**Flow:** pending dispatch (with onMutate context refinement as a SECOND pending dispatch when defined) → retryer.start → SUCCESS: config.onSuccess → options.onSuccess → config.onSettled → options.onSettled, ALL awaited, then success dispatched LAST; ERROR: each of four callbacks individually try-wrapped, throwaways converted to unhandled-rejection signals via `void Promise.reject(e)`; original error rethrown after state dispatch. finally: identity-guarded retryer drop + runNext for scope chaining.
**Invariant:** (1) user callbacks run BEFORE the terminal state dispatch — observers see 'success' only after onSuccess side effects complete (matters for invalidateQueries inside onSuccess); (2) error path guarantees every registered callback RUNS despite earlier ones throwing, while preserving the original error as the rejection reason; (3) mutation defaults retry 0 vs query default 3 — same retryer, opposite policy; (4) `context !== this.state.context` guard skips redundant dispatches when onMutate returns undefined.
**Probe:** `grep -n "void Promise.reject(e)" packages/query-core/src/mutation.ts` (:287/:298/:311/:322 exactly 4) and `grep -n "runNext(this)" packages/query-core/src/mutation.ts` (:335).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^execute$", limit: 5 });
```

## Verdict
Adopt the ledger order (config→hook, settled-last, dispatch-after) and the four-way isolation wrapper. Adapt which layers exist in your host. Omit restore/dehydration branch if unsupported. Direct tests: `__tests__/mutation.test.tsx`, `__tests__/mutationObserver.test.tsx` (mutate-callback routing lives in MutationObserver#notify :169–234).
