<!-- capsule-v2 -->
# Background review loop — dual-threshold triggers, minimum-evidence floor, single-flight flag over fire-and-forget async

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How do you auto-save memories from a live agent conversation every N turns or tool calls — without re-triggering during a running review, without reviewing thin conversations, and without ever surfacing review failures to the user?

## setupBackgroundReview
**Path/Symbol:** `src/handlers/background-review.ts:setupBackgroundReview` (:117–247); prompt builders `buildSubprocessReviewPrompt` (:42–68) / `buildDirectReviewUserPrompt` (:70–94); notify predicates (:96–103).
**Signature:** `setupBackgroundReview(pi, store, projectStore, config, options?)`; options carry `dbManager`, `projectName: ProjectNameRef`, and `deps { runDirectReview, execChildPrompt, onReviewSettled }`.
**Data Shape:** counters in closure state: `turnsSinceReview`, `toolCallsSinceReview`, `userTurnCount`, `reviewInProgress`. Config knobs: `nudgeInterval` (turns), `nudgeToolCalls` (tool calls), `reviewRecentMessages` (0 = all), `reviewTransport`.

### Decisive source
```ts
const turnThresholdMet = turnsSinceReview >= config.nudgeInterval;
const toolCallThresholdMet = toolCallsSinceReview >= config.nudgeToolCalls;

if (!turnThresholdMet && !toolCallThresholdMet) return;   // EITHER counter fires
if (userTurnCount < 3) return;                            // lifetime evidence floor:
                                                          // never review a fresh chat
turnsSinceReview = 0;                                     // reset BOTH counters even if
toolCallsSinceReview = 0;                                 // only one crossed
reviewInProgress = true;

// … snapshot branch → collectMessageParts → require allParts.length >= 4 …
//    (below the floor: reviewInProgress = false; return — no review, no retry debt)

runReview()
  .catch(() => { /* Best-effort only */ })
  .finally(finishReview);      // finishReview resets reviewInProgress AND calls
                                // deps.onReviewSettled() — the ONLY awaitable seam
                                // for tests, since production callers never await
```

**Flow:** (1) `message_end` counts USER turns; (2) each `turn_end` increments the turn counter and scans assistant content blocks for `type === "toolCall"` to feed the second counter (counting failures degrade to turn-only); (3) either threshold plus the ≥3-user-turns floor starts a review; (4) the review tries the direct in-process completion (120 s timeout) and falls back to a subprocess on error or non-empty-fallback reason — but `fallbackReason === "empty"` means "nothing worth saving", a normal outcome that returns WITHOUT falling back; (5) notifications fire only when something was actually saved (`appliedCount > 0`, or stdout lacking "nothing to save").
**Invariant:** the single-flight boolean is checked BEFORE threshold evaluation, so overlapping reviews are impossible; counters reset at trigger time (not completion time) — a long review does not accumulate a second immediate trigger; the whole loop is invisible unless it saves something. Tool-call counting is best-effort inside try/catch: losing the count must not break the loop.
**Probe:** `tests/handlers/background-review.test.ts` — uses injected `deps.runDirectReview`/`execChildPrompt` and `onReviewSettled` to assert: tool-call threshold alone triggers, sub-floor user turns suppress, empty direct result skips subprocess fallback, errors fall back to subprocess, and `reviewInProgress` blocks concurrent runs. Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "setupBackgroundReview buildSubprocessReviewPrompt nudgeToolCalls reviewInProgress", limit: 5 })`

## Verdict
Adopt the learning-loop shape: OR-ed dual thresholds, lifetime evidence floor, pre-check single-flight flag, counters-reset-on-trigger, `.catch().finally()` fire-and-forget with a test-settled hook. Adapt thresholds/timeouts/prompt constants to the host. Pair with `session-flush-duality.md` (shared transport ladder, opposite timing contracts).
