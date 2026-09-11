<!-- capsule-v2 -->
# Managed-install classification — how does a running Pi know it was installed by the installer (and why must inherited launcher env never misclassify)?

**Source:** pi (earendil-works/pi) Apache-2.0 `main@4af9d21d`; Codebase Memory `pi-upstream`. **Question:** Before choosing a self-update strategy, what exactly decides "this process is an installer-managed Pi", and which single leg of the check stops a source checkout launched *from* managed Pi from being destroyed by a managed update?

## Env + marker + package-dir-inside-releases gate
**Path/Symbol:** `packages/coding-agent/src/package-manager-cli.ts` — `getActiveManagedInstallRoot` (:54–79); consumed at `handlePackageCommand` update case (`:1023` force rejection, `:1037` managed branch) and `cleanupManagedInstall` (:150–169, called from `main.ts:576`).
**Signature:** `function getActiveManagedInstallRoot(): string | undefined`.
**Data Shape:** inputs: env `PI_MANAGED_INSTALL_ROOT` (trimmed; unset/empty ⇒ `undefined` immediately); marker file `<root>/managed-install.json` parsed as `{ kind?: unknown; layout?: unknown; schemaVersion?: unknown }`. ALL THREE fields required exact: `kind === "pi-managed-install"`, `schemaVersion === 1`, `layout === "releases-v1"`. Output: resolved absolute managed root, or `undefined` (= fall through to npm/pnpm self-update path).

### Decisive source
```ts
const configuredRoot = process.env.PI_MANAGED_INSTALL_ROOT?.trim();
if (!configuredRoot) return undefined;
const managedRoot = resolve(configuredRoot);
const releasesDir = canonicalizePath(join(managedRoot, "releases"));
// The launcher environment is inherited by child processes. Do not classify a
// source checkout or another Pi installation launched from managed Pi as managed.
if (getCwdRelativePath(canonicalizePath(getPackageDir()), releasesDir) === undefined) return undefined;
...
if (marker.kind !== "pi-managed-install" || marker.schemaVersion !== 1 || marker.layout !== "releases-v1") {
    throw new Error();
}
} catch {
    throw new Error(`Managed install marker is missing or invalid: ${markerPath}`);
}
```

**Flow:** env unset ⇒ non-managed (silent) → env set ⇒ resolve root, canonicalize `<root>/releases` → LEG-GUARD: the running package dir must sit INSIDE that releases tree (`getCwdRelativePath(...) === undefined` means outside ⇒ return `undefined`) → read+parse marker → any missing/corrupt/mismatched field THROWS `Managed install marker is missing or invalid: <path>`. Call-site consequences: `undefined` ⇒ classic npm/pnpm self-update ladder (Windows method check :1055); defined ⇒ `--force` rejected BEFORE any version-check fetch (:1024–1032) and the staged-release updater runs (:1043).
**Invariant:** classification is THREE-legged — env var AND well-formed marker AND package-dir-inside-releases. A child process inherits `PI_MANAGED_INSTALL_ROOT`, so env alone would make a dev checkout or a nested different-Pi install look managed and let an update overwrite foreign installations; the package-dir containment leg is the anti-inheritance guard and MUST NOT be dropped when porting. Invalid-marker-with-env-set fails LOUD (throw), never silently downgrades to npm self-update.
**Probe:** deterministic (anchored at `packages/coding-agent/`): `grep -n 'PI_MANAGED_INSTALL_ROOT' src/package-manager-cli.ts test/package-command-paths.test.ts` → `src/package-manager-cli.ts:55:` + tests `91:`/`705:`; `grep -n 'pi-managed-install' src/package-manager-cli.ts test/package-command-paths.test.ts` → `src:71:` + `test:55:`/`test:703:`; `grep -n 'getCwdRelativePath(canonicalizePath(getPackageDir())' src/package-manager-cli.ts` → `62:`. Direct tests: `test/package-command-paths.test.ts:695` "keeps npm self-updates non-managed when the managed environment is inherited" (inherited env + valid marker + OUTSIDE package dir ⇒ npm path runs, `fetchMock` called once, no managed artifacts touched).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "getActiveManagedInstallRoot marker classification releases", limit: 3 });
```
// verified live @4af9d21d post re-index: rank#1 getActiveManagedInstallRoot :54–79 line-exact (total:11).

## Verdict
Adopt the three-legged classification gate and the loud-invalid-marker behavior — they are what makes "managed vs npm" safe under arbitrary nesting and inheritance. Adapt the root layout (`releases/`, marker filename/schema triple) to your installer's contract, keeping schema-version gating inside validation. Omit pi.dev installer URLs and the pi-specific package-dir helper; substitute your own install-root probe with the same containment semantics.
