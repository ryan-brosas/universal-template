<!-- capsule-v2 -->
# File-access policy ladder — how does a read-only file tool escalate to permission-gated when the path leaves the workspace?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a porter refine a static per-tool permission into a per-CALL decision based on WHERE the arguments point — with the client unable to bypass it?

## preprocessArgs resolves the path; evaluateToolCallPolicy upgrades policy outside workspace
**Path/Symbol:** `core/tools/policies/fileAccess.ts` whole (26 lines); shared shape in `core/tools/definitions/{readFile,readFileRange,ls,viewSubdirectory,createNewFile}.ts`; resolution in `core/util/pathResolver.ts` (84 lines); consumption in `core/core.ts:1051–1110` (`tools/evaluatePolicy`, `tools/preprocessArgs` handlers).
**Signature:** `evaluateFileAccessPolicy(basePolicy: ToolPolicy, isWithinWorkspace: boolean): ToolPolicy`; `resolveInputPath(ide: IDE, inputPath: string): Promise<ResolvedPath | null>` where `ResolvedPath = {uri, displayPath, isAbsolute, isWithinWorkspace}`.
**Data Shape:** ToolPolicy ∈ `"allowedWithoutPermission" | "allowedWithPermission" | "disabled"`; resolution result is smuggled from preprocessArgs to policy evaluation via `processedArgs.resolvedPath`.

### Decisive source
```ts
// If tool is disabled, keep it disabled
if (basePolicy === "disabled") return "disabled";
// Files within workspace use the base policy
if (isWithinWorkspace) return basePolicy;
// Files outside workspace always require permission for security
return "allowedWithPermission";
```

**Flow:** client sends `tools/preprocessArgs{toolName, args}` ⇒ core looks the tool up in loaded config and runs `preprocessArgs(args, {ide})` which stores a `ResolvedPath`; failure returns `{preprocessedArgs: undefined, errorReason}` (no throw). Client then sends `tools/evaluatePolicy{toolName, basePolicy, parsedArgs, processedArgs}` ⇒ core finds the tool and calls `evaluateToolCallPolicy(basePolicy, parsedArgs, processedArgs)`; unknown tool ⇒ `{policy: basePolicy}` unchanged. Path semantics (`resolveInputPath`): `file://` URIs verified directly; tilde/absolute paths (incl. Windows drive + `\\` network forms) converted to URI and checked; RELATIVE paths resolved against workspace dirs ⇒ `isWithinWorkspace: true` BY CONSTRUCTION; unresolvable ⇒ `null` ⇒ evaluator falls through to basePolicy (fail-open). Workspace membership requires prefix-match AND `ide.fileExists(uri)`.
**Invariant:** the permission refinement executes SERVER-SIDE only — `serializeTool` strips exactly these two fields from what clients see (pass-6 capsule), so a compromised GUI cannot self-approve; it can only send basePolicy, which the ladder may only ESCALATE (disabled stays sticky; outside-workspace always adds permission).
**Probe:** no direct vitest suite for fileAccess/pathResolver — coverage caveat: verified by whole-file source reads of all seven files + graph retrieval this pass; the sibling terminal ladder IS test-pinned (see terminal-command-policy-veto.md); port mirroring that test style.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "evaluateFileAccessPolicy resolveInputPath isWithinWorkspace", limit: 10 });
```

## Verdict
Adopt the two-phase protocol (preprocessArgs → evaluateToolCallPolicy) and the monotone escalation rule (only toward more restrictive); adapt path resolution to your URI scheme; omit the Windows/WSL special cases if your host is POSIX-only. Trap: relative-path resolution marking `isWithinWorkspace: true` by construction means symlink escapes are NOT caught here — membership is prefix+exists on the resolved URI.
