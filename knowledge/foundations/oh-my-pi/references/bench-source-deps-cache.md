<!-- capsule-v2 -->
# Linux source-mount deps cache — running a TS workspace in containers with zero rebuild and zero outbound network

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you run your host's TypeScript workspace inside task containers so that source edits apply immediately (no rebuild) while `node_modules` binaries match the container arch — and only rebuild the deps tree when the lockfile world actually changes?

## Manifest-hash stamp + skeleton bun-install + node_modules shadow mounts
**Path/Symbol:** `packages/metaharness/src/runner.ts` — `prepareSourceDeps` (1094-1177), `sourceManifestFiles`/`sourceDepsStamp` (1064-1086), `workspacePackageDirs` (1050-1062), `repoBunVersion` (1031-1039), `dockerServerArch` (1041-1048), mount plan `writeComposeOverlay`/`buildMountsJson` (1183-1220).
**Signature:** `function prepareSourceDeps(cfg: Config): SourceMount` where `SourceMount = { arch: "arm64"|"x64"; depsDir: string; nodeModules: string[] }`.
**Data Shape:** cache at `<jobsDir>/_bench/_deps/linux-<arch>/` holding a manifests-only skeleton of the workspace plus installed production `node_modules` and the image's linux `bin/bun`. Stamp = sha256 over `bun@<version>` + every manifest's relative path and bytes (`package.json`, `bun.lock`, optional `bunfig.toml`, all `patches/*`, each workspace member's `package.json`).

### Decisive source
```ts
if (current !== stamp) {
    // copy ONLY the manifest files into the skeleton, then:
    // --ignore-scripts: the skeleton has manifests only, so lifecycle scripts
    // (root `prepare` → gen:tool-views) would fail; patchedDependencies still apply.
    const script = 'mkdir -p /deps/bin && cp "$(command -v bun)" /deps/bin/bun && cd /deps && bun install --production --omit=optional --ignore-scripts';
    spawnSync("docker", ["run", "--rm", "--platform", `linux/${...}`, "-v", `${depsDir}:/deps`, `oven/bun:${bunVersion}`, "sh", "-c", script], ...);
    fs.writeFileSync(stampFile, `${stamp}\n`);
}
// Shadow-mount every node_modules visible in the host tree (they hold darwin
// binaries) with the skeleton's linux one; both sides of each mount must exist.
for (const dir of pkgDirs) {
    const rel = path.join(dir, "node_modules");
    if (!inHost && !inDeps) continue;
    if (!inDeps) fs.mkdirSync(path.join(depsDir, rel), { recursive: true });
    if (!inHost) fs.mkdirSync(path.join(REPO_ROOT, rel), { recursive: true });
    nodeModules.push(rel);
}
```

**Flow:** detect target arch (docker server arch, or arm64 under apple-container) → hash the full manifest world + pinned bun version → stamp match ⇒ reuse cache; mismatch ⇒ wipe, copy manifests only, run `bun install --production --ignore-scripts` INSIDE `oven/bun:<version>` for the target platform (also captures that image's linux `bun` into `bin/`), write the stamp → build the mount plan: repo bind-mounted read-only at `/opt/omp/src`, every host `node_modules` shadow-mounted from the linux tree (creating either side if missing so both mount endpoints exist), linux bun mounted at `/opt/omp/bin` → docker path emits a compose overlay file; apple-container path emits `--mounts` JSON.
**Invariant:** the cache invalidates on manifest/lockfile/bun-version changes ONLY — TS edits never invalidate it because sources are bind-mounted live, not copied; installs run inside a container matching the DAEMON's native arch (emulated containers get an arch-mismatch failure by design); lifecycle scripts are skipped (skeleton can't run them) but patch overrides still apply. Stale `.node` natives load silently in workspace mode — rebuild natives separately when Rust changes.
**Probe:** no direct unit test drives `prepareSourceDeps` (needs docker); the env-contract half IS test-pinned — `packages/metaharness/test/runner.test.ts:66-94` asserts `OMP_BENCH_INSTALL=source`, `OMP_BENCH_SOURCE_DIR=/opt/omp/src`, `OMP_BENCH_SOURCE_BUN=/opt/omp/bin/bun`, `OMP_BENCH_SOURCE_ARCH=arm64` and their omission for local/binary installs. Coverage caveat stated accordingly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "prepareSourceDeps SourceMount sourceDepsStamp workspacePackageDirs node_modules shadow", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern for any "host workspace → ephemeral containers" harness: manifest-world content hash as cache key, skeleton install inside the TARGET platform image, per-package-dir shadow mounts with existence normalization. Adapt paths, package manager, and the overlay-vs-mounts emission to your executor; omit the apple-container specifics. Env contract directly tested; docker flow recorded as source-grounded with the caveat above.
