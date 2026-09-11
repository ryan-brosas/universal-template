<!-- capsule-v2 -->
# IDE mutation confinement — how do you force file writes through an IDE and prove nothing was written behind its back?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you confine agent-supplied paths to a project root (including symlink escape attempts), pre-plan which files a patch will touch, and then AUDIT the turn for out-of-IDE mutations?

## Path confinement + mutation plan + provenance audit
**Path/Symbol:** `src/pi-extension/acp-mcp-bridge.ts` (`normalizeProjectPath` :1181-1203, `parsePatchTargets` :1205-1387, `buildMutationPlan` :1432-1478, `executeMutationComposite` :902, `confineToolArgs` :966) + `src/acp/ide-inspection.ts` (`collectChangedFiles` :88, `mergeInspectFiles` :129, `computeMutationViolations` :155-158) + `src/acp/session.ts` `touchedFilePaths`.
**Signature:** `export function normalizeProjectPath(projectRoot: string, input: string, mutation: boolean): { path: string }`; `export function parsePatchTargets(patch: string): PatchTarget[]`; `export function buildMutationPlan(tool: BridgeTool, args: Record<string, unknown>, projectRoot: string): MutationPlan`; `export function computeMutationViolations(changed: string[], ideApplied: string[]): string[]`.
**Data Shape:** `PatchTarget = { kind:'add'|'update'|'delete'|'move', source?: string, destination: string }`; `MutationPlan = { preOpen: string[]; mutationArgs: Record<string,unknown>; postOpen: string[] }` (repo-relative slash paths). Applied-paths travel over IPC as `{ type: 'mutations_applied', paths: string[] }` into `AcpMcpBridge.#appliedMutations` (exposed as `appliedMutationPaths`).

### Decisive source
```ts
// normalizeProjectPath — mutation:true walks symlinks of the nearest EXISTING ancestor
const candidate = isAbsolute(raw) ? raw : resolve(root, raw)
if (!isInside(root, candidate)) throw new Error(`IDE path escapes project root: ${input}`)
if (mutation) {
  const realRoot = tryRealpath(root)
  if (realRoot !== undefined) {
    const existingAncestor = nearestExistingAncestor(candidate)
    if (existingAncestor !== undefined) {
      const real = tryRealpath(existingAncestor)
      if (real !== undefined && !isInside(realRoot, real)) {
        throw new Error(`IDE mutation path escapes project root through symlink: ${input}`)
      }
    }
  }
}
```

**Flow:** every bridged tool call under ide-mode ≠ off goes `prepareToolArguments` → mutation remote names (`apply_patch|rename_refactoring|reformat_file|create_new_file`) route to `executeMutationComposite`: plan targets from the patch text (unified-diff `---/+++` headers AND Codex V4A `*** Begin Patch / Update|Add|Delete File: / Move to:` sections; quoted-header `\t \n \r \b \f \v \a \" \\` and octal unescaping; `/dev/null` decides add-vs-delete; dedupe by `kind:source:destination`), normalize+confine each target, call `open_file_in_editor` on preOpen paths BEFORE the mutation call, fire `mutations_applied` IPC with affectedPaths, open created files AFTER (post-open failure annotates `mutationSucceeded:true, postOpenError` rather than failing). Non-mutation tools get args confined in place. Post-turn the ADAPTER side runs `enforceIdeMutationProvenance`: changed set = git status porcelain `-z --untracked-files=all` merged with turn-touched tool paths (extraFiles take precedence at the 200-file cap), minus paths the bridge recorded applied this turn → violations become an agent_message_chunk naming the re-apply tools plus `_meta.piAcp.mutationViolations`. A parallel `tool_call` hook blocks direct bypass via `fabric_exec` code containing `schema.commit(` or `pi.write(`/`pi.edit(`.
**Invariant:** confinement is deny-by-throw (never silent rewrite); the provenance snapshot is taken BEFORE `session.prompt` (`ideMutationsBefore`) so only THIS turn's IDE applications offset THIS turn's changes; `session.touchedFilePaths.clear()` runs after each end_turn so stale paths never mask later violations.
**Probe:** `npx tsx --test test/unit/gate-hardening.test.ts test/unit/ide-inspection.test.ts` (patch-target parsing incl. V4A/octal/symlink cases; violation math).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "normalizeProjectPath buildMutationPlan computeMutationViolations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt throw-don't-rewrite path confinement with the existing-ancestor realpath walk (a plain root realpath check misses not-yet-existing files), the two-dialect patch-target parser, pre/post-open choreography, and before-snapshot provenance auditing. Adapt PATH_KEYS/RESULT_PATH_KEYS key vocabularies and the blocked-bypass regex to your host's tool names. Omit IntelliJ-specific capability names. Direct tests executed green at the pin (gate-hardening suite included).
