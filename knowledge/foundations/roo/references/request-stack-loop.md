<!-- capsule-v2 -->
# Stack-driven request loop — how do you drive multi-turn requests without call-stack recursion, and what happens when the context window overflows?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** A porter's recursive turn function blows the stack on deep subtask chains and dies on context-window errors — what does roo's loop do instead?

## Explicit StackItem stack + policy constants + global rate-slot reservation
**Path/Symbol:** `src/core/task/Task.ts` (`recursivelyMakeRooRequests`; constants at file head: `MAX_EXPONENTIAL_BACKOFF_SECONDS=600`, `FORCED_CONTEXT_REDUCTION_PERCENT=75`, `MAX_CONTEXT_WINDOW_RETRIES=3`).
**Signature:** stack starts with ONE item `{userContent, includeFileDetails, retryAttempt: 0}`; popped per turn; subtasks/delegations push new items.
**Data Shape:** Abort checks fire at the TOP of every iteration; rate limiting is honored BEFORE the spinner appears; `Task.lastGlobalApiRequestTime` (static) reserves the global provider slot EARLY so subsequent requests — including subtask requests — still honor the same rate-limit window.

### Decisive source
```ts
// The stack starts with one item: userContent, includeFileDetails, retryAttempt 0 — popped per turn.
// FORCED_CONTEXT_REDUCTION_PERCENT = 75  → keep 75% of context, remove 25% on context-window errors
// MAX_CONTEXT_WINDOW_RETRIES = 3         → then give up
// checkContextWindowExceededError drives the condense/retry ladder.
```

**Flow:** pop a stack item per turn → stream the assistant response → tool calls may push follow-up work as new items (subtask delegation included) → on context-window exceeded errors: shrink context by removing 25%, retry, up to 3 attempts, integrating the condense path — no unbounded recursion anywhere.
**Invariant:** Turn sequencing must live in an explicit data structure (stack), never the JS call stack, so depth is bounded only by memory; rate-limit slot reservation must be GLOBAL and EARLY so parent and subtask requests serialize through one clock.
**Probe:** No isolated spec at this HEAD — coverage caveat; deterministic probes: constant declarations verbatim at Task.ts head; behavior cross-pinned by `src/core/task/__tests__/Task.spec.ts` harvests.

## Get live surrounding code
**Retrieve:** (drift note 2026-08-24 pass 7: multi-token query regressed to total:0 — repaired to search_code, live-resolved)
```bash
codebase-memory-mcp cli search_code '{"project":"Roo-Code","pattern":"FORCED_CONTEXT_REDUCTION_PERCENT"}'
# Variable row src/core/task/Task.ts 134 + Method Task.handleContextWindowExceededError rows at 3739;3787
```

## Verdict
Adopt the explicit-stack loop, the 75%/3-retry overflow policy shape, and early global slot reservation. Adapt constants to your providers' reality. Omit condense integration if you have no summarization path. Coverage caveat noted above.
