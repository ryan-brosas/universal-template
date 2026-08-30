<!-- capsule-v2 -->
# Nested-memory attachment walk — when the agent opens a file deep in a subtree, how do the right AGENT.md files and scoped rules ride along as attachments?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you lazily attach hierarchical memory (nested AGENT.md + glob-scoped conditional rules) for an arbitrary target file without re-loading or mis-scoping anything?

## Four-phase lazy attachment pipeline

**Path/Symbol:** `src/utils/attachments.ts`:`getNestedMemoryAttachmentsForFile` (`:1792-1862`), `getDirectoriesToProcess` (`:1656-1687`); consumers at `src/utils/attachments.ts` (`:1878`, `:2183`).
**Signature:** `getNestedMemoryAttachmentsForFile(filePath, toolUseContext, appState): Promise<Attachment[]>`; `getDirectoriesToProcess(targetPath, originalCwd): { nestedDirs: string[]; cwdLevelDirs: string[] }`.
**Data Shape:** One shared mutable `processedPaths: Set<string>` threads through every phase; outputs are `Attachment[]` built by `memoryFilesToAttachments`. Dir partition: `nestedDirs` = CWD→target (only dirs INSIDE originalCwd), `cwdLevelDirs` = filesystem-root→CWD.

### Decisive source
```ts
try {
  if (!pathInAllowedWorkingPath(filePath, appState.toolPermissionContext)) return []
  const processedPaths = new Set<string>()
  // Phase 1: Managed + User conditional rules first (global scope wins)
  // Phase 2: getDirectoriesToProcess partitions CWD→target vs root→CWD
  for (const dir of nestedDirs) {
    const memoryFiles = (await getMemoryFilesForNestedDirectory(dir, filePath, processedPaths))
      .filter(f => !skipProjectLevel || (f.type !== 'Project' && f.type !== 'Local'))
    attachments.push(...memoryFilesToAttachments(memoryFiles, toolUseContext, filePath))
  }
  for (const dir of cwdLevelDirs) {
    // Only CONDITIONAL rules — unconditional rules were already loaded eagerly
    const conditionalRules = (await getConditionalRulesForCwdLevelDirectory(dir, filePath, processedPaths))
      .filter(f => !skipProjectLevel || (f.type !== 'Project' && f.type !== 'Local'))
    ...
  }
} catch (error) { logError(error) }   // fail-open: no attachments on error
```

**Flow:** sandbox gate (`pathInAllowedWorkingPath`) → managed+user conditional rules → walk nested dirs shallowest-first loading each dir's full stack (AGENT.md + unconditional + conditional rules) → sweep above-CWD dirs for conditional rules ONLY (their unconditional content is already in context from eager startup load) → feature-flag filter (`tengu_paper_halyard`) can drop Project/Local classes per phase. Called from TWO trigger points: IDE file-open selection and a second consumer at `:2183`.
**Invariant:** The `processedPaths` set spans ALL phases so no file attaches twice across layers; the CWD-level loop must request conditional-rules-ONLY or above-CWD unconditional AGENT.md files would duplicate the eager load. The dir walk stops at `originalCwd` for full stacks but continues to the FS ROOT for conditionals because a root-level rule with matching globs still scopes to the opened file. Failures are logged and swallowed — attachment generation must never break the main flow. Order is attention priority: global (managed/user) → nearest (CWD→target).
**Probe:** No direct test covers this function (coverage caveat — source-grounded; sibling agentmd seams share the gap). Deterministic probe: grep pins the sandbox gate at `src/utils/attachments.ts:1801` and the phase comments; `search_graph --name-pattern "^getNestedMemoryAttachmentsForFile$"` resolves `locoagent.src.utils.attachments.getNestedMemoryAttachmentsForFile`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "nested memory attachments directory walk conditional rules", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the phase split (full stacks inside CWD, conditionals-only above it), the cross-phase dedupe set, the sandbox gate, and fail-open error posture. Adapt the dir-partition boundary and attachment envelope to your host. Omit nothing from the conditional-only rule for above-CWD dirs — requesting full stacks there reintroduces duplicates of the eager load.
