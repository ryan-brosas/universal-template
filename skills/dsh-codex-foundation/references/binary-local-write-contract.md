<!-- capsule-v2 -->
# Local byte-write contract — how do you publish bytes to the local filesystem under host sandbox modes with write-intent version gates?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** a tool wants to save binary output to the user's workspace, but the host may be read-only, workspace-confined, or fully open — where does the mode ladder and the "file changed since read" gate live?

## writeWorkspaceBytes → writeLocalBytes + checkedLocalTarget
**Path/Symbol:** `src/binary-fs.ts:167-182 writeWorkspaceBytes`, `:126-164 writeLocalBytes`, `:57-76 checkedLocalTarget`, `:78-81 resolveSandboxPolicy`, types `:11-34 FsBytesWriteOutcome/BinaryWritableFileSystem/SandboxPolicyView`.
**Signature:** `writeWorkspaceBytes(ctx, exec: ToolExecution, target: FsTarget, content: Uint8Array, expected?: FsWriteIntent): Promise<FsBytesWriteOutcome>`; outcome `{ operation:'create'|'update', version: FsVersion, bytes }`.
**Data Shape:** `SandboxPolicyView = { mode:'read-only'|'workspace-write'|'danger-full-access', workspaceRoot }`; intents `replaceIfVersion{version}` vs `createIfAbsent`; denial errors are typed `FsError` with codes `FS_SANDBOX_DENIED` / `FS_NOT_REGULAR_FILE` / `FS_STALE_VERSION` / `FS_NOT_OBSERVED` / `FS_IO_ERROR`.

### Decisive source
```ts
export async function writeWorkspaceBytes(ctx, exec, target, content, expected?) {
  const policy = resolveSandboxPolicy(ctx, exec)
  const protocol = new URL(ctx.fs.fileUrl(target)).protocol
  if (protocol === 'file:') return writeLocalBytes(ctx, exec, target, content, expected, policy)
  const writer = ctx.fs as Partial<BinaryWritableFileSystem>
  if (typeof writer.writeBytes !== 'function') {
    throw new Error(`the active ${protocol} filesystem cannot save binary output; update its provider or omit output_path`)
  }
  return writer.writeBytes(target, content, expected, exec.signal, policy)
}

async function checkedLocalTarget(ctx, target, policy, signal?) {
  if (ctx.fs.sandboxMode === undefined) return target
  if (policy === undefined) throw new Error('the active filesystem confines writes but its sandbox policy is unavailable')
  if (policy.mode === 'read-only')
    throw new FsError(`cannot write "${target.displayPath}": file access denied under read-only mode`, 'FS_SANDBOX_DENIED')
  if (policy.mode === 'danger-full-access') return target
  const fresh = await ctx.fs.resolve(target.displayPath, signal ? { signal } : undefined)
  const root = await ctx.fs.resolve(policy.workspaceRoot, ...)
  if (!ctx.fs.contains(root, fresh))
    throw new FsError(`cannot write "${target.displayPath}": file access denied under workspace-write mode`, 'FS_SANDBOX_DENIED')
  return fresh
}
```

**Flow:** caller (imagegen's publication step) → sandbox policy resolved per execution session from the host's `sandboxPolicy` service → target URL protocol decides local vs remote path → local: sandbox ladder resolves/validates the target BEFORE any lock or I/O; then inside the per-path lock (`binary-atomic-publish-lock.md`) stat gates run: non-regular files refuse; `replaceIfVersion` refuses when the file is gone or its version moved since read ("file changed since it was read"); `createIfAbsent` refuses when anything already exists ("cannot overwrite … without reading it first") → publish → post-write re-stat produces the create/update outcome with the new version.
**Invariant:** sandbox enforcement happens before locking and before touching bytes — an out-of-workspace path in workspace-write mode never even stats; a confining filesystem whose policy view is unavailable fails CLOSED rather than assuming access; the URL→process-path agreement assertion (`urlPath !== processPath` throws) catches symlink/mount drift between the two path views; intent semantics are strict — no implicit create-or-overwrite; the returned operation reflects observed pre-state, not the requested intent; remote (non-`file:`) targets require the host filesystem to actually implement binary `writeBytes`, failing with guidance naming both remedies (update provider / omit output_path) instead of silently corrupting text-only writers.
**Probe:** no dedicated test file exists for binary-fs.ts (glob over tests/ finds none) — recorded block. Boundary evidence: `tests/imagegen.spec.ts:244-254` drives the read-only denial through this plane and asserts the generated image survives with a bounded writeError; direct source read of :11-182 this pass confirms every branch above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.binary-fs\\.(writeWorkspaceBytes|writeLocalBytes|checkedLocalTarget|resolveSandboxPolicy)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 4, has_more false. Trace_path(inbound) for `writeWorkspaceBytes`: single graphed caller `dsh-codex.src.imagegen.execute` (imagegen.ts:41 calls it inside `imagegenTool`).

## Verdict
Adopt fail-closed policy ladders that check before locking, strict two-sided write intents, and capability-probing dispatch for non-local filesystems. Adapt mode names, error codes, and the policy-resolution seam to your host. Omit best-effort sandbox checks after mutation begins, or letting a text-mode remote writer receive binary payloads. Coverage: src/binary-fs.ts `no_recorded_issue` + `metadata_match`.
