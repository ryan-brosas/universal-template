<!-- capsule-v2 -->
# Pi host mirror + VFS — how do you let an in-process runtime's own fs-based resource loading see a sandboxed workspace without copying the whole project to the host?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When a dialect runtime executes on the host but its working directory must be the SANDBOX path (so its system prompt and resource loading resolve inside the sandbox), what filesystem indirection keeps that true without mirroring hundreds of thousands of files?

## Scoped mirror + global fs mount on a collision-free path
**Path/Symbol:** `packages/harness-pi/src/pi-session.ts` — host layout + VFS mount (:296–385), resource-loader lockdown (:468–510); `packages/harness-pi/src/pi-workspace-vfs.ts` — `PiWorkspaceVfs` (:397–437), `mountedRoots` (:52), longest-prefix routing (`findMountedRoot`); `packages/harness-pi/src/pi-workspace-mirror.ts` — `PI_CONFIG_DIRS` (:32), `syncHostWorkspaceFromSandbox` (:292).
**Signature:** `workspaceVfs.mount(backingRoot: string, mountPoint: string)` / `unmount()`; `syncHostWorkspaceFromSandbox({sandbox, sandboxWorkDir, hostWorkDir})`.
**Data Shape:** host root `<tmpdir>/ai-sdk-harness/pi/<safeSessionId>/{workspace,agent,sessions}` where `safeSessionId` replaces `[\/: ]` (timestamp session ids must not become directory trees); the VFS is a process-global `node:fs` monkey-patch (sync, callback, and promises APIs) with a `mountedRoots` map; the mirror copies ONLY `.pi/`, `.agents/`, and root-level `AGENTS.md`/`AGENTS.MD`.

### Decisive source
```ts
// pi-session.ts:300–385 (abridged) — the mount point is the sandbox workDir,
// which does not exist on the host, so the redirect can never shadow real files
const safeSessionId = input.sessionId.replace(/[\/: ]/g, '-');
const hostRoot = path.join(tmpdir(), 'ai-sdk-harness', 'pi', safeSessionId);
const hostWorkDir = path.join(hostRoot, 'workspace');
...
// Snapshot sandbox state into the host mirror BEFORE the VFS goes live so
// Pi sees the workspace as soon as it boots.
await syncHostWorkspaceFromSandbox({ sandbox: toolSafeSandboxSession,
  sandboxWorkDir: input.sessionWorkDir, hostWorkDir });
// Mount only the workspace: ... The agent and session directories stay on the
// real host filesystem — they are host-only Pi state (auth, model registry,
// session journal) that must never surface in the sandbox or the workspace mirror.
const workspaceVfs = new PiWorkspaceVfs();
workspaceVfs.mount(hostWorkDir, sessionWorkDir);
```
```ts
// pi-workspace-mirror.ts:1–33 (abridged) — why the mirror is scoped
/*
 * Pi runs on the host with its working directory pointed at the local mirror,
 * but the only thing it reads from that directory is its own resource
 * configuration: the `.pi` and `.agents` directories ... and the root-level
 * agent context files (`AGENTS.md`). The model never reads workspace source
 * through the host — file reads, directory listings, and greps all run as
 * tools against the sandbox. Mirroring the whole sandbox workspace to the
 * host would therefore copy files Pi never looks at ... For a real project
 * that has been cloned and had its dependencies installed (hundreds of
 * thousands of files under `node_modules`) that makes session startup take
 * hours. The mirror is consequently scoped to exactly the paths Pi's
 * resource loader consults.
 */
const PI_CONFIG_DIRS = ['.pi', '.agents'] as const;
```

**Flow:** createPiSession builds the host mirror dirs → snapshots the SCOPED config paths from the sandbox (pure-bash traversal with per-component `readlink` resolution, symlink-cycle detection, symlink targets copied as real files because a mirrored symlink would dangle; no `find -L` — not all sandbox shells support it) → mounts the VFS → boots Pi with `cwd = sessionWorkDir` (the sandbox path) while DefaultResourceLoader runs with `noExtensions/noThemes/noPromptTemplates` so a host developer's personal Pi extensions can never execute in the server process; skills are filtered to workspace project skills + harness-provided skills → every turn re-syncs the scoped mirror before prompting (pi-session.ts :1123) → stop/suspend/destroy unmount and `rm -rf` the host root.
**Invariant:** the VFS patches stay installed while ANY mount exists and are restored only after the final unmount (multi-instance safe via longest-prefix routing; overlapping mount points forbidden); rename across mount boundaries throws; only the workspace is ever mounted — auth/model/session state stays host-only; the mirror never reads out-of-scope files (enumeration is scoped, stale mirrored files are removed, up-to-date content skips writes).
**Probe:** `packages/harness-pi/src/pi-workspace-vfs.test.ts` :28–90 (redirects sync+promises APIs against the logical mount, leaves non-mount paths untouched, restores patches after the LAST unmount, concurrent mounts with longest-prefix matching); `packages/harness-pi/src/pi-workspace-mirror.test.ts` :86–453 (scoped enumeration "never the full workspace" :360, symlinked config dirs resolved :209, symlinked ancestor of the work dir :266, cycle rejection :331, stale-file removal :408, skip-when-up-to-date :438); pi-session.test.ts :380–401 ("keeps filesystem extensions and other resources disabled by default").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "PiWorkspaceVfs mountedRoots syncHostWorkspaceFromSandbox PI_CONFIG_DIRS", limit: 10 });
```

## Verdict
Adopt the collision-free-mount-point trick (mount at a path that cannot exist on the host) plus the scoped-resource mirror for any in-process runtime whose own loader touches the workspace; adapt the scoped path list to whatever your runtime's resource loader consults; omit full-workspace mirroring entirely — the model's file access goes through sandbox-backed tools, never through the host fs. Coverage caveat: none — both planes are fully test-pinned.
