<!-- capsule-v2 -->
# Human-in-the-loop mistake breaker — what should an agent do when the model keeps making mistakes, and how does subtask delegation feed the same guard?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** A porter's loop aborts at N consecutive mistakes — why does roo ask the human instead, and where does delegation validation report its failures?

## Escalate with a guidance channel; reset on the human's answer
**Path/Symbol:** `src/core/task/Task.ts:2483-2495` (limit check + `mistake_limit_reached` ask); per-tool counters `consecutiveMistakeCountForApplyDiff` / `ForEditFile` Maps; delegation side in `src/core/tools/NewTaskTool.ts` (`delegateParentAndOpenChild`).
**Signature:** counter reaches `consecutiveMistakeLimit` → blocking `ask("mistake_limit_reached", …)`; user response kinds decide recovery.
**Data Shape:** Mistakes = failed tool parses + tool errors; per-tool refinement maps track applyDiff/editconsecutive counts separately so one flaky tool doesn't mask another's pattern.

### Decisive source
```ts
if (this.consecutiveMistakeLimit > 0 && this.consecutiveMistakeCount >= this.consecutiveMistakeLimit) {
	// NOT abort — ASK THE HUMAN. If the user responds with guidance
	// (messageResponse), the text is injected via formatResponse.tooManyMistakes
	// (+ images) and the counter RESETS: the human's explanation becomes the
	// recovery fuel.
}
```

**Flow:** mistake → increment (per-tool map when applicable) → limit reached → ask the human with the mistake context → guidance text re-enters the conversation as `tooManyMistakes` framing and the counter resets — turning a failure ceiling into a collaboration point. Delegation path: `new_task` validates mode/messages/todos (todos can be REQUIRED via settings, parsed from markdown checklists) and reports validation failures through the SAME mistake counter before ever delegating; success = parent parks by id, child becomes sole active task, returns immediately ("no pause/unpause, no waiting"). Settings namespace uses `Package.name` so stable/nightly variants don't collide.
**Invariant:** A runaway-loop ceiling must escalate to the human WITH a channel to inject guidance, and must reset on that guidance — otherwise the agent stays bricked after recovering. Delegation parameter validation must consume the same accountability mechanism as ordinary tools.
**Probe:** Cross-pinned by `src/core/task/__tests__/Task.spec.ts` harvests; deterministic probe: ask-kind string `mistake_limit_reached` at Task.ts:2485. Coverage caveat: no isolated spec for the ladder itself at this HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "consecutiveMistakeLimit mistake_limit_reached delegateParentAndOpenChild", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt escalate-and-reset semantics and shared-counter delegation validation. Adapt message framing keys. Omit per-tool maps if you have only one failure class. Coverage caveat noted above.
