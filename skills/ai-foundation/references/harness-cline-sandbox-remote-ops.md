<!-- capsule-v2 -->
# Cline sandbox remote ops — how do you implement built-in file/shell tools when the model's workspace is in a sandbox but the runtime runs on the host?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When every file operation must cross the sandbox boundary as a shell command or SandboxSession call, how do you keep path containment sound against traversal, symlinks, and writes to not-yet-existing paths?

## Two-tier containment with in-sandbox canonical resolution
**Path/Symbol:** `packages/harness-cline/src/cline-remote-ops.ts` — `assertWorkspacePath` (:73–79), `assertReadablePath` (:81–92), `resolveExistingSandboxPath` (:131–160), `resolveWritableSandboxPath` (:183–215), `readFile`/`writeFile`/`editFile` (:218–271), `bash` (:279–304), `grep`/`glob`/`ls` (:306–419).
**Signature:** `createClineRemoteOps({sandbox, workDir, readableRoots?}): ClineRemoteOps` with `resolvePath/readFile/writeFile/editFile/bash/grep/glob/ls`.
**Data Shape:** `workDir` = absolute sandbox path of the session workspace; `readableRoots` = extra read-only roots (the skills dir materialized in sandbox HOME); all shell commands run through `sandbox.run({command, workingDirectory: workDir})` with interpolated values quoted by the shared `shellQuote`.

### Decisive source
```ts
// cline-remote-ops.ts:73–92 — logical check: writes stay in the workspace,
// reads may also enter readable roots
const assertWorkspacePath = (inputPath: string): string => {
  const normalized = path.posix.normalize(inputPath);
  if (!isInsidePath({ parent: normalizedWorkDir, candidate: normalized })) {
    throw new Error(`Cline path escapes the workspace: ${inputPath}`);
  }
  return normalized;
};
const assertReadablePath = (inputPath: string): string => {
  const normalized = path.posix.normalize(inputPath);
  if (
    !isInsidePath({ parent: normalizedWorkDir, candidate: normalized }) &&
    !readableRoots.some(parent =>
      isInsidePath({ parent, candidate: normalized }),
    )
  ) {
    throw new Error(`Cline path escapes the readable roots: ${inputPath}`);
  }
  return normalized;
};
```
```sh
# cline-remote-ops.ts:183–215 (abridged) — writable resolution walks UP to the
# closest existing ancestor and realpaths IT, catching dangling symlinks and
# new writes whose parent escapes, before any I/O happens
if [ -e "$target" ] || [ -L "$target" ]; then resolved=$(realpath "$target"); ...
dir=$(dirname "$target"); base=$(basename "$target"); missing="$base"
while [ ! -e "$dir" ] && [ ! -L "$dir" ]; do parent=$(dirname "$dir"); ... missing="$(basename "$dir")/$missing"; dir="$parent"; done
resolved_dir=$(realpath "$dir"); printf '%s/%s\n' "$resolved_dir" "$missing"
```
The same one-liner family uses sentinel markers on stdout plus distinct exit codes (`__CLINE_REALPATH_NOT_FOUND__` exit 2, `__CLINE_REALPATH_FAILED__` exit 3) so a failed resolution is distinguishable from a path whose last line merely looks like an error.

**Flow:** every op first resolves the LOGICAL path (posix normalize + containment assert) → then resolves the CANONICAL path inside the sandbox via the sentinel one-liner → re-asserts containment on the canonical result (a symlink inside the workspace that points out fails here) → only then performs the SandboxSession I/O. `editFile` = read + first-occurrence `indexOf` replace + full rewrite through `writeFile`. `bash` converts the seconds timeout to ms through an AbortController merged with the caller signal. `grep`/`glob`/`ls` are shell pipelines (`grep -rn --binary-files=without-match … | head -n limit`; `find -type f` filtered client-side by `path.matchesGlob`, case-insensitive sorted, limited; `ls -1Ap` with type-indicator stripping).
**Invariant:** no sandbox I/O happens before BOTH containment checks pass (logical AND canonical); reads are strictly a superset of writes (workspace ⊆ readable set); a dangling symlink or a new write under an escaping ancestor is rejected even though the target does not exist yet; skills live in sandbox HOME (a readable root), never in the workspace, so the model can read them but never write them.
**Probe:** `packages/harness-cline/src/cline-remote-ops.test.ts` :112–135 ("rejects absolute, traversal, sibling-session, and prefix escapes" — including the `/work/evil` prefix-of-`/work/evil-twin` case), :202–236 (readable root allows reads but rejects edits), :238–300 (symlink resolving outside rejected; new write whose closest existing ancestor escapes rejected; dangling-symlink write rejected; in-workspace symlink canonicalized), :318–350 (bash runs in work dir, aborts on timeout), :402–419 (grep does not follow symlinks discovered during recursive search).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createClineRemoteOps assertWorkspacePath resolveWritableSandboxPath __CLINE_REALPATH_NOT_FOUND__", limit: 10 });
```

## Verdict
Adopt the two-check (logical + canonical) containment pattern and the sentinel-marker shell one-liners for any dialect whose tools must operate on a remote/sandboxed filesystem; adapt the readable-roots list to whatever extra materialization your dialect does (skills, config); omit client-side glob filtering only if your sandbox shell has a trustworthy native matcher — the source deliberately filters `find` output in JS because sandbox shells vary. Coverage caveat: none — this plane is fully test-pinned.
