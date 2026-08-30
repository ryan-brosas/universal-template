<!-- capsule-v2 -->
# memory read-error taxonomy — which file-read failures should a memory loader swallow, and what must it do with actionable ones?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When an AGENT.md/rules read fails, how does the loader distinguish "expected absence" from "actionable breakage" without crashing startup or leaking paths into telemetry?

## handleMemoryFileReadError + safelyReadMemoryFileAsync: ENOENT/EISDIR silent, EACCES logged path-free
**Path/Symbol:** `src/utils/agentmd.ts`:`safelyReadMemoryFileAsync` (`:424-437`), `handleMemoryFileReadError` (`:402-416`).
**Signature:** `safelyReadMemoryFileAsync(filePath: string, type: MemoryType, includeBasePath?: string): Promise<{ info: MemoryFileInfo | null; includePaths: string[] }>`; `handleMemoryFileReadError(error: unknown, filePath: string): void`.
**Data Shape:** Returns `{ info: null, includePaths: [] }` on ANY failure — callers never see exceptions. Error class comes from `getErrnoCode(error)`.

### Decisive source
```ts
const code = getErrnoCode(error)
// ENOENT = file doesn't exist, EISDIR = is a directory — both expected
if (code === 'ENOENT' || code === 'EISDIR') {
  return
}
// Log permission errors (EACCES) as they're actionable
if (code === 'EACCES') {
  // Don't log the full file path to avoid PII/security issues
  logEvent('tengu_agent_md_permission_error', {
    is_access_error: 1,
    has_home_dir: filePath.includes(getClaudeConfigHomeDir()) ? 1 : 0,
  })
}
```

**Flow:** every candidate path (Managed/User AGENT.md, per-directory Project/Local files, rules dirs, AutoMem/TeamMem entrypoints) goes through one async reader → parse happens only on success → failures funnel to the classifier → expected-absence codes return silently so the root-to-CWD walk over ~dozens of nonexistent paths stays quiet; EACCES fires ONE boolean-shaped event that records only whether the denied path lives under the config home.
**Invariant:** The walk expects most candidates to be absent — absence must stay silent or telemetry drowns. But permission errors are surfaced because a user-configured file they can't read is a real misconfiguration worth one signal; the signal must be PATH-FREE (only a boolean for config-home membership), because full paths in telemetry leak usernames/project names. Any other errno propagates unhandled by design (the rules-dir wrapper catches EACCES separately at `:779-787` and returns `[]`). Note the asymmetry vs processMdRules: readdir-level errors ENOENT/EACCES/ENOTDIR return empty there too, but OTHER readdir errors rethrow — only read-file failures are always swallowed.
**Probe:** Coverage caveat: no direct upstream test on this host. Deterministic probe: `search_graph --project locoagent --name-pattern "^handleMemoryFileReadError$"` resolves line-exact; grep pins the two-code silent set at `src/utils/agentmd.ts:405` and the path-free EACCES event at `:409-415`; `processMdRules`' readdir gate at `:733-739`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "handleMemoryFileReadError getErrnoCode EACCES memory", limit: 10 });
```

## Verdict
Adopt the three-way taxonomy (silent expected-absence, path-free actionable signal, propagate-the-rest) and the null-result failure shape. Adapt event names and the config-home predicate to your host. Omit analytics plumbing if you have no sink. Caveat: source-grounded probes only — no runnable test exercised this path here.
