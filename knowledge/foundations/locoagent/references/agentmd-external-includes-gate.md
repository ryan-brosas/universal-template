<!-- capsule-v2 -->
# external @include approval gate — how do out-of-tree memory includes get blocked until the user explicitly approves them?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** A project's AGENT.md can `@~/attacker/notes.md` — how does a layered memory loader keep untrusted instruction files from silently pulling arbitrary out-of-tree files into model context?

## getExternalAgentMdIncludes + shouldShowAgentMdExternalIncludesWarning: detect, warn once, remember approval
**Path/Symbol:** `src/utils/agentmd.ts`:`getExternalAgentMdIncludes` (`:1404-1414`), `hasExternalAgentMdIncludes` (`:1416-1418`), `shouldShowAgentMdExternalIncludesWarning` (`:1420-1430`), with the boundary check `pathInOriginalCwd` (`:245-247`) and the include-side enforcement in `processMemoryFile` (`:666-670`).
**Signature:** `getExternalAgentMdIncludes(files: MemoryFileInfo[]): { path: string; parent: string }[]`; `shouldShowAgentMdExternalIncludesWarning(): Promise<boolean>`.
**Data Shape:** "External" = an included file resolving OUTSIDE `getOriginalCwd()` (`pathInWorkingPath(path, cwd)`). Approval lives as two persistent project-config booleans: `hasClaudeMdExternalIncludesApproved` and `hasClaudeMdExternalIncludesWarningShown`.

### Decisive source
```ts
// detection — only USER-type files can be external, and only via @include (parent set)
if (file.type !== 'User' && file.parent && !pathInOriginalCwd(file.path)) {
  externals.push({ path: file.path, parent: file.parent })
}
```
```ts
// warning decision
if (config.hasClaudeMdExternalIncludesApproved ||
    config.hasClaudeMdExternalIncludesWarningShown) return false
return hasExternalAgentMdIncludes(await getMemoryFiles(true))  // forceIncludeExternal=true
```
and inside `processMemoryFile`:
```ts
const isExternal = !pathInOriginalCwd(resolvedIncludePath)
if (isExternal && !includeExternal) continue        // blocked unless allowed
```

**Flow:** every recursive include resolves its absolute path → if outside original CWD and the caller didn't pass `includeExternal`, the include is DROPPED mid-walk (never parsed) → a UI-level check re-runs discovery with `getMemoryFiles(true)` to see what WOULD have loaded, shows one approval dialog unless already approved or already warned, and persists the user's answer into project config.
**Invariant:** The default-deny boundary is enforced at RESOLUTION time (`processMemoryFile`), not merely at display time — the warning layer only decides whether to PROMPT; it cannot itself be the enforcement point. Detection is deliberately NARROW: type must be `User` AND have a `parent` — top-level User files are trusted by definition, so only include-derived files count. The `force=true` variant must NOT fire InstructionsLoaded hooks (see agentmd-memory-loading's cache capsule); it exists solely for this audit. Warning-once semantics: after either boolean is set the prompt never re-shows, so the approval state is sticky across sessions.
**Probe:** Coverage caveat: no direct upstream test on this host. Deterministic probe: `trace_path --function-name locoagent.src.utils.agentmd.getExternalAgentMdIncludes --direction both` shows callers in status/settings UI surfaces (callers_total 8); grep pins the type+parent filter at `src/utils/agentmd.ts:1409`, the sticky-config early-return at `:1422-1427`, and the drop-at-resolution guard at `:667-669`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getExternalAgentMdIncludes hasClaudeMdExternalIncludesApproved pathInOriginalCwd", limit: 10 });
```

## Verdict
Adopt resolve-time default-deny for out-of-tree includes plus a separate sticky approve-once prompt keyed on two persisted config booleans. Adapt the trust root (original CWD vs your sandbox root) and config keys. Omit the telemetry around the dialog. Caveat: source-grounded probes only — no runnable test exercised the dialog flow here.
