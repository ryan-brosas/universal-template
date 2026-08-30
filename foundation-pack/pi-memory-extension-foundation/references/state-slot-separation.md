<!-- capsule-v2 -->
# Interrupt-state slot — how is an interrupted task carried across sessions without polluting knowledge?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must decide whether working state flows through the same pipeline as knowledge — this repo says NO, and the split has exact file/scan/refresh consequences.

## State slot (`state/current-task.md` handling)
**Path/Symbol:** `pi-memory.ts` state load in `session_start` (:260–263) and refresh (:340–343); clear command (:584–596); injection in `buildMemoryBlock` (:169–173, tier 1).
**Signature:** state path = `path.join(config.globalDir, "state", "current-task.md")`; content trimmed to `stateContent: string`.
**Data Shape:** Always read from the GLOBAL layer (never workspace); injected as the first section `### Current Task State`; cleared by writing empty string.

### Decisive source
```ts
// Load state (separate from regular memory — working context, not knowledge)
const statePath = path.join(config.globalDir, "state", "current-task.md");
const stateRaw = await tryReadFile(statePath);
const stateContent = stateRaw?.trim() ?? "";
```

**Flow:** session start → read global `state/current-task.md` into a SEPARATE cache field (outside the scanned files list) → inject as top section when non-empty → human runs `/memory:clear-task` after resolving the interruption (writes `""`, keeping the file).
**Invariant:** Working context is a DIFFERENT channel from knowledge: it lives outside the scan set (`scanDir` skips the reserved name `state`), is global-only by construction, and outranks every other tier at injection (kept fully even under budget pressure). Empty-after-trim ⇒ no section. Clearing writes empty rather than unlinking, so the slot always exists.
**Probe:** NO upstream tests exist. Deterministic probe this run pinned the exclusion side (`scanDir` never returns `state/current-task.md` — `/tmp/pime-probe/probe2.mts` GREEN) and the budget side (state string kept verbatim under a 1000-char total cap — `/tmp/pime-probe/probe.mts` P4 GREEN). Read/clear paths confirmed by direct source read.

## Get live surrounding code
**Retrieve:** graph BM25 has NO Function node matching `"current-task"` (the clear-handler is an anonymous closure), so resolve by content search instead:
```bash
codebase-memory-mcp cli search_code '{"project":"pi-memory-extension","pattern":"current-task.md"}'
```
(Executed pass-3 audit at pin f3b4377f: rank-1 `pi-memory.handler` **:587-595** = the `/memory:clear-task` closure itself, plus `MemoryCache` Interface :50-56 whose `stateContent` doc-comment :54 cites the file; Module-level hits :261/:304/:341 cover load/status/refresh sites.)

## Verdict
Adopt a separate, highest-priority volatile-slot channel for working/interrupt state distinct from curated knowledge. Adapt file location to host layout; keep trim-to-empty semantics and explicit-clear lifecycle. Omit nothing.
