<!-- capsule-v2 -->
# pr-merge-detection-ladder — how can a feature know a merge actually happened, and that THIS viewer performed it?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** What is the reliable post-merge evidence chain when GitHub swaps the conversation DOM after the confirm click?

## Observe-early → await-click → await-badge ladder
**Path/Symbol:** `source/github-events/on-pr-merge.ts:waitForPrMerge` (:7–23, whole file).
**Signature:** `waitForPrMerge(signal: AbortSignal): Promise<void>`.
**Data Shape:** resolves only when both stages complete; throws if the run signal aborted mid-ladder.

### Decisive source
```ts
// It must start listening early or else the animation ID will be generated incorrectly (ancestor)
// WARNING: Be very careful about the value of ancestor if you refactor this code
const mergeEvent = new Promise(resolve => {
	// `emphasis` excludes merge commit icons added by `mark-merge-commits-in-list`
	observe('.TimelineItem-badge.color-fg-on-emphasis .octicon-git-merge', resolve, {ancestor: 4});
});

await oneEvent(confirmMergeButton, 'click', {signal});
// It won't resolve once the signal is aborted
await mergeEvent;

if (signal.aborted) {
	throw new Error('The code shouldn’t have reached this point');
}
```

**Flow:** start observing the timeline merge badge IMMEDIATELY (before any user action) with a pinned `{ancestor: 4}` hop count → await exactly one click on the merge-confirm button (abortable via signal) → await the badge observation, which fires only after GitHub renders the merged state → final aborted check converts any impossible path into a loud throw.
**Invariant:** (1) observation must precede the click — after merge the subtree is replaced and the animation-ID ancestor chain would be computed wrong; the `ancestor: 4` value is load-bearing and comment-pinned; (2) the `color-fg-on-emphasis` qualifier EXCLUDES fake badges injected by the `mark-merge-commits-in-list` feature; (3) resolving on the badge (not the click) scopes the event to the person who performed the merge — bystanders watching the page never see it; (4) an aborted signal must not leave the promise hanging silently — the explicit throw documents the unreachable path.
**Probe:** no direct unit test exists for this file (browser-timeline-bound; standing caveat). Executed pins: `grep 'ancestor: 4|oneEvent\(|shouldn’t have reached' source/github-events/on-pr-merge.ts` → lines 12, 15, 21.
**Consumer evidence:** live `trace_path inbound waitForPrMerge` → closing-remarks.init, pr-branch-auto-delete.init, suggest-commit-title-limit.init (three features need post-merge follow-ups).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "waitForPrMerge", direction: "inbound" });
// callers_total: 3 → features.closing-remarks / pr-branch-auto-delete / suggest-commit-title-limit
```
Executed 2026-08-26 @ pin 3187161.

## Verdict
Adopt the observe-before-action evidence ladder for any destructive/one-shot UI flow whose DOM gets replaced on completion: pin the observer's ancestor count in code + comment, qualify selectors to exclude your own injected UI, and convert unreachable states into throws. Adapt selectors and the badge semantics to your host. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no upstream direct test — deterministic source pins stand in.
