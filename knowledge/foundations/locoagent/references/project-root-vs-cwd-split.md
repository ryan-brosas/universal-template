<!-- capsule-v2 -->
# project-root-vs-cwd split — why does a worktree jump move the working directory but not the project?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When an agent can enter a throwaway git worktree mid-session, which paths must follow it and which must stay anchored — and where is that line enforced?

## getProjectRoot vs getOriginalCwd vs getCwdState: three cwd slots with different mutability
**Path/Symbol:** `src/bootstrap/state.ts`:`originalCwd` (`:46`), `projectRoot` comment (`:47-50`), `getProjectRoot` (`:511-513`), `setProjectRoot` guard (`:519-525`), `getOriginalCwd`/`setOriginalCwd` (`:500-517`), `getCwdState`/`setCwdState` (`:527-533`), NFC resolution at init (`:261-276`).
**Signature:** `getOriginalCwd(): string`; `getProjectRoot(): string`; `getCwdState(): string`; setters `setOriginalCwd(cwd)`, `setProjectRoot(cwd)` (startup-only), `setCwdState(cwd)`; all normalize `.normalize('NFC')`.
**Data Shape:** Three strings: `originalCwd` (realpath+NFC resolved at first state touch), `projectRoot` (stable identity root), `cwd` (live working dir). Initializer defends each step: `typeof process !== 'undefined'`, `typeof process.cwd === 'function'`, `typeof realpathSync === 'function'`.

### Decisive source
```ts
// :261-276 — symlink + Unicode-form resolution, with a fallback per failure class
let resolvedCwd = ''
if (typeof process !== 'undefined' && typeof process.cwd === 'function'
    && typeof realpathSync === 'function') {
  const rawCwd = cwd()
  try {
    resolvedCwd = realpathSync(rawCwd).normalize('NFC')   // match shell.ts setCwd
  } catch {
    // File Provider EPERM on CloudStorage mounts (lstat per path component).
    resolvedCwd = rawCwd.normalize('NFC')                 // degrade to raw, still NFC
  }
}
// :47-50 — the contract comment
// Stable project root - set once at startup (including by --worktree flag),
// never updated by mid-session EnterWorktreeTool.
// Use for project identity (history, skills, sessions) not file operations.
// :519-521 — enforcement comment on the setter
// Only for --worktree startup flag. Mid-session EnterWorktreeTool must NOT
// call this — skills/history should stay anchored to where the session started.
```

**Flow:** process start → realpath+NFC resolution (EPERM on CloudStorage mounts degrades to raw-but-NFC so state construction never throws) → all three slots seeded identically → mid-session EnterWorktreeTool updates ONLY `cwd` (via shell setCwd semantics) → history/skills/session lookup keeps reading `projectRoot`, file operations read live `cwd`.
**Invariant:** Project identity (transcript location, skills discovery, session history) must NOT follow a mid-session worktree jump — only file operations do. The split is enforced socially (guard comments naming the forbidden caller) plus by normalization discipline: every setter re-normalizes NFC so mixed Unicode forms of the same path never fork cache keys or transcript dirs. Symlink resolution happens ONCE at startup, matching how shell.ts sanitizes session-storage paths.
**Probe:** Deterministic pins: `grep -n "never updated by mid-session" src/bootstrap/state.ts` → `48:`; `grep -n 'Mid-session EnterWorktreeTool must NOT' src/bootstrap/state.ts` → `520:`; `grep -nF ".normalize('NFC')" src/bootstrap/state.ts | wc -l` → `5` (init ×1 + three setters + originalCwd setter); `grep -n 'CloudStorage mounts' src/bootstrap/state.ts` → `273:`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getProjectRoot setProjectRoot worktree stable project root", limit: 10 });
```

## Verdict
Adopt the three-slot split (identity root / launch dir / live cwd) for any agent that can change directories or enter worktrees — skills and history keyed on the stable root, I/O on the live one. Adapt the NFC policy to your platform's Unicode exposure. Omit the CloudStorage-specific EPERM fallback if your FS layer already guards realpath.
