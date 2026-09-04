<!-- capsule-v2 -->
# agenda-task-location-containment — how do you confine user-supplied cwd/resource paths to a workspace root without symlink escapes?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** What checks make an arbitrary user path safe to use as a task's cwd or resource reference, including directories that are symlinks to outside the workspace?

## Global tasks own no filesystem; workspace paths pass containment THEN realpath walk-up
**Path/Symbol:** `sdk/packages/core/src/tasks/task-location.ts` (`normalizeAgendaTaskLocation` :72-125; `normalizeWorkspacePath` :51-69; `assertNoSymlinkEscape` :31-49; `isContained` :23-29).
**Signature:** `normalizeAgendaTaskLocation(input: {scope, workspaceRoot?, cwd?, resourcePaths?}): {workspaceRoot?, cwd?, resourcePaths[]}` — THROWS on every violation (callers catch and fold into parse results).
**Data Shape:** Global scope returns `{resourcePaths: []}` and tolerates NO filesystem anchoring. Workspace scope yields resolved absolute workspaceRoot/cwd plus workspace-relative POSIX resourcePaths deduped on the relative form.

### Decisive source
```ts
function assertNoSymlinkEscape(workspaceRoot: string, candidate: string, field: string): void {
	if (!existsSync(workspaceRoot)) return;
	const canonicalRoot = realpathSync(workspaceRoot);
	let existing = candidate;
	while (!existsSync(existing)) {          // walk UP to nearest existing ancestor:
		const parent = dirname(existing);    // catches symlinked dirs that don't exist
		if (parent === existing) break;      // yet as leaf paths
		existing = parent;
	}
	if (!existsSync(existing)) return;
	if (!isContained(canonicalRoot, realpathSync(existing))) {
		throw new Error(`${field} escapes the workspace through a symbolic link`);
	}
}
// normalizeWorkspacePath(root, value, field, allowRoot):
//   containment gate (!isContained || (!allowRoot && candidate === root)) throws;
//   cwd passes allowRoot=TRUE (cwd may BE the root), resourcePaths FALSE.
// Resource pre-checks BEFORE containment: isAbsolute(resourcePath)
//   || resourcePath.split(/[\\/]+/u).includes("..")  → rejected outright.
```

**Flow:** global scope ⇒ throw if ANY of workspaceRoot/cwd/non-empty resources present, return empty ⇒ workspace scope ⇒ resolve root (required) ⇒ cwd normalized with allowRoot=true ⇒ per resource: trim (empty throws) → reject absolute/`..`-segment → containment+root-exclusion gate → symlink walk-up check → dedupe by relative form.
**Invariant:** A global task can never touch the filesystem; a workspace task's every consumed path resolves to a real location whose canonical form stays inside the canonical workspace root — string-level containment alone is insufficient because `..`-free relative paths can still escape through a symlinked ancestor directory.
**Probe:** `grep -cF 'escapes the workspace through a symbolic link' sdk/packages/core/src/tasks/task-location.ts` → 1 (:47). Direct-test coverage caveat: NO dedicated `task-location.test.ts` exists (graph census of `tasks/` = 15 files); behavior is pinned indirectly via `task-spec-parser.test.ts` "rejects global file references and workspace traversal" and `task-spec-parser.test.ts` "rejects a workspace task directory that escapes through a symlink" (store-level ensureSpecsDir twin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.task-location.normalizeAgendaTaskLocation" });
// observed: Function lines 72-125 verbatim, byte-equal to the checkout read
```

## Verdict
Adopt the three-layer ladder (string pre-checks → lexical containment with allowRoot asymmetry → realpath walk-up against canonical root) and the global-tasks-own-nothing rule. Adapt path separators and error copy. Omit Cline's agenda scope types. Coverage: no_recorded_issue @ gen 2026-08-24T16:12:41Z; dedicated-suite absence recorded as caveat above; runner-BLOCKED honestly.
