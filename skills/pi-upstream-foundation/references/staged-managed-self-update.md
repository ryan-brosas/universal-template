<!-- capsule-v2 -->
# Staged immutable managed update — how do you replace a live installation without ever leaving a broken one active?

**Source:** pi (earendil-works/pi) Apache-2.0 `main@4af9d21d`; Codebase Memory `pi-upstream`. **Question:** What is the full stage → verify → atomically-activate pipeline for in-place self-update, and which ordering rules keep a failed or concurrent update from corrupting the running install?

## Lock → clean staging → download → npm ci → smoke-verify → rename into releases → pointer flip
**Path/Symbol:** `packages/coding-agent/src/package-manager-cli.ts` — `runManagedSelfUpdate` (:171–221), `verifyManagedRelease` (:105–124), `activateManagedRelease` (:126–135), `cleanupManagedStaging` (:137–148), `cleanupManagedInstall` (:150–169); call-site `handlePackageCommand` :1037–1051.
**Signature:** `async function runManagedSelfUpdate(managedRoot: string, version: string): Promise<void>`; `function verifyManagedRelease(releaseDir: string, expectedVersion: string): void`; `function activateManagedRelease(managedRoot: string, version: string): void`.
**Data Shape:** layout under root: `releases/<semver>/` (immutable per-version trees), `staging/update-*` (mkdtemp work dirs), marker `managed-install.json`, pointer file `current-version` containing `${version}\n`. Version validated against `/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/` before any I/O. Artifacts fetched from `${PI_INSTALLER_API_BASE || https://pi.dev/api/installer/releases}/<encodeURIComponent(version)>/{package.json,package-lock.json}` (trailing-slash-stripped base).

### Decisive source
```ts
releaseLock = await lockfile.lock(join(managedRoot, "update"), { realpath: false });
...
if (error instanceof Error && "code" in error && error.code === "ELOCKED") {
    throw new Error("Another managed Pi update is already running.");
}
...
stageDir = mkdtempSync(join(stagingRoot, "update-"));
// ... write package.json + package-lock.json, then:
await runManagedNpmCi(stageDir);            // npm ci --ignore-scripts --min-release-age=0 --omit=dev ...
verifyManagedRelease(stageDir, version);
renameSync(stageDir, releaseDir);           // atomic promote: staging -> releases/<version>
activateManagedRelease(managedRoot, version); // tmp write + rename of current-version
```

**Flow:** semver gate on the TARGET version → exclusive lock at `<root>/update` (`proper-lockfile`, ELOCKED ⇒ friendly "Another managed Pi update is already running." exit 1) → sweep stale `staging/update-*` and stale locks left by crashed updaters → **already-downloaded shortcut**: if `releases/<version>` exists, only re-run `verifyManagedRelease` + flip pointer (no refetch) → else fetch both manifest artifacts in PARALLEL, `npm ci` them in the stage dir with `--ignore-scripts` (lifecycle scripts never run during update) and `--min-release-age=0`, SMOKE-TEST the staged binary (`node_modules/.bin/<app> --version` must equal expected exactly) BEFORE promotion, `renameSync` stage→`releases/<version>` (atomic same-fs promote), THEN rewrite `current-version` via temp-file+rename. `finally`: rm stage dir + release lock. Startup hygiene: `main.ts:576` calls exported `cleanupManagedInstall()` right after the Windows quarantine cleanup — it re-classifies, takes the same lock non-fatally, and sweeps abandoned staging; every failure inside the managed branch is caught at the call site (:1044–1048) printing the error and setting `exitCode=1` WITHOUT touching the active release.
**Invariant:** the ACTIVE tree is never mutated in place — all build risk lands in `staging/`, promotion is a single `renameSync`, and activation order is strictly verify-BEFORE-promote, promote-BEFORE-pointer-flip. A crash at ANY earlier point leaves the previous `current-version` intact and bootable (test :678 pins this for an npm failure mid-update). Concurrency is excluded by the `update` lock (test :638). The launcher resolves the running release by reading `current-version`, so pointer writes must be atomic (temp+rename) or a crash can strand a half-written pointer. `--force` is rejected for managed installs (:1024) because repair = rerun the installer, not reinstall over a live tree.
**Probe:** deterministic (anchored at `packages/coding-agent/`): `grep -n 'ELOCKED' src/package-manager-cli.ts` → `180:`; `grep -n 'Another managed Pi update is already running' src/package-manager-cli.ts test/package-command-paths.test.ts` → `src:181:` + `test:656:`; `grep -n 'renameSync(stageDir, releaseDir)' src/package-manager-cli.ts` → `215:`; `grep -c 'verifyManagedRelease(' src/package-manager-cli.ts` → `3` (def :105 + pre-existing shortcut :199 + staged :214); `grep -n 'current-version.tmp' src/package-manager-cli.ts` → `128:`; `grep -n 'min-release-age' src/package-manager-cli.ts test/package-command-paths.test.ts` → `src:93:` only; `grep -n 'ignore-scripts' src/package-manager-cli.ts test/package-command-paths.test.ts` → `src:92:` + `test:629:`; `grep -n 'cleanupManagedInstall' src/main.ts src/package-manager-cli.ts` → `main:67:`+`main:576:`+`cli:150:`; `sed -n '573,577p' src/main.ts` shows `cleanupManagedInstall();` after the win32 quarantine block. Direct tests: `test/package-command-paths.test.ts` :609 happy path (pointer content, releases dir exists, prior release's `active.txt` untouched, staging EMPTY after, recorded npm args contain `ci --ignore-scripts`, success message `Updated pi from <old> to <new>`), :638 concurrency rejection, :661 forced-reinstall rejection (fetch NEVER called), :678 failed-update keeps old release active.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "runManagedSelfUpdate managed install staging lock", limit: 4 });
```
// verified live @4af9d21d post re-index: rank#1 runManagedSelfUpdate :171–221 line-exact (total:78).

## Verdict
Adopt the whole choreography — external lock keyed to ONE well-known path, mkdtemp staging under the managed root, parallel artifact fetch, no-scripts dependency install, executable smoke test before promotion, single-rename promote, atomic pointer flip last, startup best-effort staging GC. Adapt artifact source URLs, package-manager flags, and the smoke-test command to your product. Omit pi.dev endpoints and the release-announcement publisher side; nothing here requires them.
