<!-- capsule-v2 -->
# Plugin install transaction — how do you install third-party npm/git packages so a failed validation leaves zero trace?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** Installing a plugin runs a real package manager and then LOADS its code; if that load fails, what must be restored so the rejected package, manifest edit, AND lockfile pin are all gone?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/plugins/manager.ts:PluginManager.install` (:439-649), helpers `#snapshotInstalledPackage` (:325-343), `#rollbackFailedInstall` (:356-387), `#cleanupSnapshot` (:345-354), `#validateInstalledExtensions` (:389-415).
**Signature:** `install(specString, options?: InstallOptions): Promise<InstalledPlugin>` — spec may carry feature brackets (`pkg[feat]`).
**Data Shape:** rollback inputs captured up-front: `packageJsonBefore: string`, `bunLockBefore: string | null` (null = absent before → remove on rollback), `PluginPackageSnapshot { actualName, packagePath, backupRoot(mkdtemp), backupPath }`; `actualName: string | undefined` hoisted OUT of the try so the catch can clean the right node_modules entry even on mid-flight throws.

### Decisive source
```ts
// Snapshot bun's lockfile ... Every step below — `bun install`, `bun update`,
// feature/extension validation, runtime-config save — must either complete
// entirely or leave the lockfile pointing at its pre-install state.
let bunLockBefore: string | null;
try { bunLockBefore = await Bun.file(bunLockPath).text(); }
catch (err) { if (!isEnoent(err)) throw err; bunLockBefore = null; }
// Drain stdout+stderr concurrently with proc.exited. Awaiting exited before
// reading either pipe risks a >64 KiB OS-pipe-buffer deadlock ...
const [installExit, , installStderr] = await Promise.all([
	installProc.exited,
	new Response(installProc.stdout).text(),
	new Response(installProc.stderr).text(),
]);
...
await this.#validateInstalledExtensions(installedPlugin); // actually loadExtensions() the declared entries
```
**Flow:** parse spec → validate (npm vs git validators) → dryRun short-circuit → capture manifest text + lockfile text + depsBefore + node_modules backup copy → remove stale dep edge when a git ref changes (bun treats old-ref→new-ref replacement as a self-edge DependencyLoop) → `bun install <spec>` with concurrent pipe drain → resolve actualName (git: new-key diff of package.json deps, fallback repo-identity match) → git reinstall only: refreshBunGitCache + `bun update <name>` → read installed package.json → feature selection/validation → **loadExtensions() as validation** → runtime-config save → return. Catch: restore manifest, restore-or-remove bun.lock, rm node_modules tree, cp backup back; rollback failure is APPENDED (`${message}\nRollback failed: …`). Finally: rm temp backup.
**Invariant:** three artifacts move together — plugins/package.json, bun.lock, node_modules/<name> — plus the omp-plugins.lock.json entry; validation executes the plugin's factory, so a throwing extension rejects the whole install. Legacy twin `installer.ts:installPlugin` (:33-87) has NO config/git/rollback — kept for the simple npm path only.
**Probe:** direct tests: `test/plugin-install-validation.test.ts` "rejects and rolls back an install when the extension factory throws" (:129), "restores bun.lock when a git reinstall fails validation (#3069 follow-up)" (:396), "removes bun.lock on rollback when it did not exist before install" (:480); anchor-greps at pin: `const [installExit, , installStderr] = await Promise.all([` manager.ts:510.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.extensibility.plugins.manager.PluginManager.install" });
```

## Verdict
Adopt: snapshot-all-three-artifacts-before-mutating; execute-the-code-as-validation; restore-or-remove ternary for files that may not have existed; append rollback failure to the original error instead of masking it. Adapt: your package manager of process.spawn equivalent — keep the drain-concurrent-with-exit pattern. Omit: bun-specific pm cache/DependencyLoop workarounds unless you also drive bun.
