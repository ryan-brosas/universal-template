<!-- capsule-v2 -->
# Evidence-first video doctrine — why does the pipeline refuse to "reenact" a task, and what capture rules follow?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What contract keeps an explanatory video honest evidence instead of fabricated footage?

## Record-what-happened, never reenact; Input.* only; explicit-consent gate on video processing
**Path/Symbol:** `skills/cdp/interaction-skills/make-video.md` (doctrine, :1-64 + editorial contract :105-124); enforcement split across `recording.ts:classify` (only real Input.*/Page.* wire calls become beats) and `video.ts:initRecording`'s `--require-explicit` (:552-554); SKILL.md restates the rule (`skills/cdp/SKILL.md:110`).
**Signature:** doctrine, enforced at three chokepoints: `classify` ignores `Runtime.evaluate` side effects; `initRecording(recording, requireExplicit)` throws `BriefError('not an explicit recording; ...')` when `meta.auto === true`; export refuses without `--reviewed`.
**Data Shape:** evidence per beat = JSONL event + frame(s) captured DURING the task; `beforeFrame` gives pre-action state for click pairs.

### Decisive source
```md
Use captured browser frames as evidence. Never reenact a finished task or
fabricate cleaner footage. This workflow compacts a long action trace; it does
not accelerate a screen recording.
```
```md
Arbitrary page-side `Runtime.evaluate` expressions such as `element.click()`
cannot be interpreted as user actions and therefore are not recorded as action
beats.
```

**Flow:** start recording BEFORE browser work → perform the task with REAL input calls → stop only after verifying the outcome → init with `--require-explicit` (a post-task `recordings --latest` is usable only after checking its timestamps/pages match the task; otherwise say the work was not captured) → author brief → review → export.
**Invariant:** (1) An unclassifiable action is a GAP in the video, never a prompt to stage footage — the compiler's job is COMPACTION (choose beats, pace cards), not generation. (2) Explanations of wrong turns are allowed exactly once each as Observed→Mistake→Correction cards; failures that teach nothing are cut. (3) Narration is sticky-by-design (≤7 words, cadence-gated) because screenshots carry the story. (4) The consent gate is task-scoped: a natural request to record/demo opts in THAT task only; ordinary work stays unrecorded.
**Probe:** direct tests pin the mechanical half (typing hidden unless revealed — video.test.ts :70-83). Doctrine itself is doc-pinned: `grep -n "reenact" skills/cdp/interaction-skills/make-video.md skills/cdp/SKILL.md`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "classify", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the doctrine verbatim for any "show your work" artifact from an agent: record reality, compact honestly, gate processing behind explicit consent and human review; adapt card style/budgets; omit nothing — dropping the reenactment ban turns an evidence tool into a fabrication tool.
