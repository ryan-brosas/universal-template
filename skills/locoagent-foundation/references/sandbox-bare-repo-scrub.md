<!-- capsule-v2 -->
# Planted bare-repo scrub — the post-command sweep that completes the deny-or-scrub split

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** A sandboxed command can CREATE `HEAD`/`objects`/`refs`/`hooks`/`config` at cwd mid-run, turning cwd into a booby-trapped bare repo for the NEXT unsandboxed git call — how is that closed without breaking legitimate repos?

## Bare-repo scrub plane
**Path/Symbol:** `src/utils/sandbox/sandbox-adapter.ts` : `scrubBareGitRepoFiles` (:407-417), module list `bareGitRepoScrubPaths` (:400), wired into `cleanupAfterCommand` (:966-969); config-time counterpart in `convertToSandboxRuntimeConfig` (:270-283); consumer `src/utils/Shell.ts` :392.
**Signature:** `function scrubBareGitRepoFiles(): void` — synchronous `rmSync(p, { recursive: true })` per recorded path; `cleanupAfterCommand(): void` calls base cleanup then scrub.
**Data Shape:** `bareGitRepoScrubPaths: string[]` populated ONLY inside convertToSandboxRuntimeConfig (paths that did NOT exist at config time), cleared (`length = 0`) at each config rebuild and on reset.

### Decisive source
```ts
// Unconditionally denying these paths makes sandbox-runtime mount
// /dev/null at non-existent ones, which (a) leaves a 0-byte HEAD stub on
// the host and (b) breaks `git log HEAD` inside bwrap ("ambiguous argument").
// So: if a file exists, denyWrite (ro-bind in place, no stub). If not, scrub
// it post-command in scrubBareGitRepoFiles() — planted files are gone before
// unsandboxed git runs; inside the command, git is itself sandboxed.
```

**Flow:** At every config build, each of the five sentinel names under originalCwd (and cwd when different) goes to exactly ONE of two lists: exists → `denyWrite` (read-only bind preserves real repo files); missing → scrub list. After EVERY sandboxed command, `Shell.exec`'s result handler calls `cleanupAfterCommand()` which scrubs planted paths synchronously BEFORE any await — so callers awaiting `.result` observe a clean tree in the same microtask, and Claude's own UNSANDBOXED git calls (status, diff) never see a planted bare repo with an attacker `core.fsmonitor` config. ENOENT from rmSync is the expected common case and is swallowed.

**Invariant:** (1) The two lists are complementary per-path per-build: denying non-existent paths creates ghost 0-byte mount-point files (bwrap behavior, issue #29316); scrubbing existing files would destroy real repos. (2) Scrub must run SYNCHRONOUSLY in the result microtask — deferring it past an await reopens the TOCTOU window this exists to close. (3) The scrub list must be rebuilt whenever the config rebuilds (cwd may have changed); stale entries would delete files created legitimately later.

**Probe:** anchored at the locoagent repo root — `grep -n 'rmSync(p, { recursive: true })' src/utils/sandbox/sandbox-adapter.ts` → :411; `grep -n 'scrubbed planted bare-repo' src/utils/sandbox/sandbox-adapter.ts` → :412; `grep -n 'const bareGitRepoScrubPaths' src/utils/sandbox/sandbox-adapter.ts` → :400; `grep -n 'cleanupAfterCommand()' src/utils/Shell.ts` → :392; `grep -cn 'bareGitRepoScrubPaths.length = 0' src/utils/sandbox/sandbox-adapter.ts` → 2 (:270 config rebuild + :816 reset).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "scrubBareGitRepoFiles bareGitRepoScrubPaths cleanupAfterCommand", limit: 5 });
```

## Verdict
Adopt the deny-existing/scrub-missing pair as one mechanism — porting only half either leaves ghost HEAD stubs or destroys real repos. Adapt sentinel names to whatever makes YOUR git treat cwd as a repo. Omit the macOS no-op note's platform branch if your sandbox has no host-side mount-stub behavior. Coverage caveat: deterministic source probes only (issue #29316 documents upstream incident, not a runnable test).
