<!-- capsule-v2 -->
# Pinned-CLI provisioning with checksum gate and nightly bypass — how do you ship a vendored binary safely but let QA escape the pin?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** An action downloads its own executable at run time — how do you guarantee integrity for stable releases without breaking nightly testing? (Mismatch-posture divergence re-verified line-exact at `e0675fbe`, pass 4.)

## cli.json checksum table + version-scoped tool cache + use-installed-cli escape hatch
**Path/Symbol:** `common/cli.json` (whole file: `{version, checksum{platform_arch}}`), `common/qodana.ts:getQodanaSha256` (:46-63 throws on unknown combo), `getQodanaUrl` (:121-135 throws outside SUPPORTED_PLATFORMS/ARCHS, zip-vs-tar.gz by platform), `getNightlyTag`/`getLatestNightlyTag` (:84-116), installers `scan/src/utils.ts:installCli` (:315-342) / `gitlab/src/utils.ts:installCli` (:222-250) / `vsts/src/utils.ts:installCli` (:154-175); opt-out `verifyInstalledCli` (scan :302-313, vsts :142-152) and GitLab's `getCliVersion` probe (:210-220).
**Signature:** `getQodanaUrl(arch, platform, nightlyTag='')`; `installCli(nightlyVersion)`; `prepareAgent(args, nightlyVersion='', useInstalledCli=false)`.
**Data Shape:** cli.json is generated at release time; `VERSION = version` from it; checksum keyed `windows|linux|darwin × x86_64|arm64`.

### Decisive source
```ts
const temp = await tc.downloadTool(getQodanaUrl(arch, platform, nightlyTag))
if (!nightlyVersion) {
  const expectedChecksum = getQodanaSha256(arch, platform)
  const actualChecksum = sha256sum(temp)
  if (expectedChecksum !== actualChecksum) {
    core.setFailed(getQodanaSha256MismatchMessage(expectedChecksum, actualChecksum))
  }
}
core.addPath(await tc.cacheDir(extractRoot, EXECUTABLE, nightlyVersion ? `nightly-${nightlyVersion}` : VERSION))
```
The nightly tag ladder: `'' → stable v${version}`; `'2026.2' → 'v2026.2-nightly'`; `'latest' → first `-nightly` suffix match from the GitHub releases API (throws if none — "to save QA time").

**Flow:** prepareAgent branches: `useInstalledCli` → probe `<cli> --version`, warn the resolved version, loud error if absent; else download → verify sha256 ONLY when version is NOT nightly → extract per-platform → cacheDir under the exact version (or `nightly-{v}`) → addPath. The SHAPE repeats across adapters but the MISMATCH POSTURE DIVERGES (pass-4 correction of this capsule's earlier "all three repeat this shape" claim): gitlab `installCli` (:222-250) THROWS on mismatch — provisioning aborts before extraction; scan (:315-342) calls `core.setFailed(...)` WITHOUT return and continues to extract/cache the corrupted binary; vsts (:154-175) calls its `setFailed` likewise and continues. Tool-cache labels diverge too: scan caches as `nightly-${nightlyVersion}` | VERSION via @actions/tool-cache; vsts always labels VERSION; gitlab has no tool cache at all — it extracts into `${os.tmpdir()}/qodana-cli` and appends that to `process.env.PATH` manually. After install, every adapter except GitLab also runs the image pre-pull when NOT native/skip-pull (`qodana pull` with filtered args — see pull-args-filtering); GitLab's getInputs forces native mode instead.
**Invariant:** Checksum verification must be SKIPPED exactly when a nightly tag is present — nightlies are mutable by definition and a strict check would brick QA. Unknown platform/arch combos must THROW loudly in both `getQodanaSha256` and `getQodanaUrl` rather than silently downloading something wrong. A porter MUST choose a mismatch posture explicitly: abort-before-use (gitlab) is the safe default; record-and-continue (scan/vsts) trades a poisoned tool cache for a clearer "the run itself failed" signal at end-of-job — never copy it silently.
**Probe:** `scan/__tests__/project.test.ts` :90-107 downloads ALL SIX archives (3 platforms × 2 arches, common/qodana.ts:30-31) from the URL builder and asserts each sha256 against cli.json (the live end-to-end checksum test; previously mispinned :66-87 — that window holds the orb/version doc tests); common tests pin `getNativeModePrefix` separately. Installer-level tests don't exist for adapters (coverage caveat recorded). Pass-4 window: common 62 + scan 11 suites re-executed green at `e0675fbe` (gitlab/vsts suites don't cover installers either).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "getQodanaUrl getQodanaSha256 checksum downloadTool", limit: 8 });
```

## Verdict
Adopt the three-way contract: generated checksum table keyed platform×arch, verify-except-nightly rule, version-scoped tool caching; adapt per-host extraction/PATH plumbing; omit the GitHub-API nightly discovery if your host has no release channel (keep the explicit-tag form).
