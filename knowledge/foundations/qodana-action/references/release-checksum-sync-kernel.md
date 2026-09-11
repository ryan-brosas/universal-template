<!-- capsule-v2 -->
# Release checksum-sync kernel — when a new CLI version ships, how do FOUR verification surfaces stay in lockstep?

**Source:** qodana-action Apache-2.0 `main@e0675fbe…` (pass 3 @ unchanged pin); Codebase Memory `qodana-action`. **Question:** This repo consumes qodana-cli binaries from Gradle, Maven-era configs, CircleCI, and the TS actions — what is the machine that propagates one upstream release into every checksum/version consumer, and what invariant does a porter break by syncing only one surface?

## update-cli.js: download → derive keys → rewrite four artifact classes in ONE scripted pass
**Path/Symbol:** `common/update-cli.js` whole-file (225L): `updateCliChecksums` (:88-105), `updateCircleCIChecksums` (:107-117), `updateChecksumsKtFile` (:119-153), `updateVersions` (:155-182), `replaceStringsInProject` (:184-190), `getLatestRelease` (:70-86), `downloadFile` (:20-44); data `plugin/src/main/kotlin/org/jetbrains/qodana/Checksums.kt` (generated, 25 version rows × 6 platform_arch keys at pin, "Do not modify it manually" :20); consumers `plugin/.../Qodana.kt:getChecksum` (:81-86) + `orb/commands/scan.yml` (:56-57).
**Signature:** `main()` sequence: read current version from cli.json → `getLatestRelease()` (tag_name minus leading `v`, :82) → `downloadFile(checksums.txt)` → `updateVersions(latest, current)` → `updateCliChecksums` → `updateCircleCIChecksums` → per-platform binary loop (windows gets `.exe`, :208) computing sha256 → `updateChecksumsKtFile`.
**Data Shape:** checksums.txt lines `"<sha256>  <filename>"` (TWO-space separator, :93); keys derived as `filename.split("_").slice(1).join("_").split(".")[0]` → `windows_x86_64|linux_arm64|darwin_…` (:96), gated by an explicit 6-key allowlist before writing into `cliJson.checksum`.

### Decisive source
```js
// updateVersions: cascading replacement, THREE passes, repo-wide sed
replaceStringsInProject(`${maj}.${min}.${patch}`, `${cMaj}.${cMin}.${cPatch}`);
replaceStringsInProject(`${maj}.${min}`,       `${cMaj}.${cMin}`);
replaceStringsInProject(`${maj}`,              `${cMaj}`);
// replaceStringsInProject :187 — excludes ONLY Checksums.kt (it carries history)
const command = `cd .. && find . -type f -not -path "./${checksumsKtPath}" -exec sed -i${isMacOS ? " ''" : ""} 's/${oldString}/${newString}/g' {} +`;
```
```js
// updateChecksumsKtFile: textual splice into generated Kotlin (:130-145)
const start = content.indexOf('val CHECKSUMS = mapOf(');
const end   = content.lastIndexOf(')') + 1;
updated = updated.replace(/\n\)$/, `,\n${newVersionBlock}\n)`);
```
```js
// updateCircleCIChecksums: POSITIONAL line surgery into the orb (:113)
circleCIConfigLines[55] = `        QODANA_SHA_256=${checksum}`;
```

**Flow:** fetch latest release tag → strip `v` → pull official checksums.txt → bump every version-looking string in the repo via the three-pass sed (full `x.y.z`, then `x.y`, then bare `x` — so task.json `QodanaScan@2026`, orb `CLI_DIRECTORY=/tmp/cache/qodana-cli/2026.2.0`, installer arg `v2026.2.0`, and DOCS all move together; `LC_ALL=C` pins byte-stable sorting, darwin needs `sed -i ''`) → rewrite cli.json checksum table from checksums.txt (allowlist-gated keys) and DELETE the downloaded file (consumed-on-write, `unlinkSync` :104) → download the linux x86_64 tarball, hash the EXTRACTED binary, and overwrite orb line index 55 with the new `QODANA_SHA_256=` → finally download all six binaries, hash each, and APPEND a fresh `"x.y.z" to mapOf(...)` block inside Checksums.kt before its closing paren.
**Invariant:** Four surfaces must move in ONE change — Gradle/Maven verify against the CHECKSUMS table, the orb pins its OWN sha copy inline, cli.json drives the TS tool-cache verification, and task.json/docs carry the version — skipping any one yields ASYMMETRIC verification failures (a Gradle user gets checksum mismatch while CI still installs fine). The Checksums.kt map grows monotonically (old rows retained forever) because released action versions must keep verifying OLD pinned CLIs; the sed therefore excludes exactly that file. The orb line-index write is positional: inserting any line above :55 (1-based) makes the script corrupt whatever sits there — regenerate, don't hand-edit, above that line. `lastIndexOf(')')` for the Kotlin splice assumes the map's close is the LAST paren in the file — a trailing comment containing `)` breaks the splice silently.
**Probe:** `grep -n 'circleCIConfigLines\[55\]' common/update-cli.js` → `113:`; `grep -cE '^    "[0-9]{4}\.[0-9]+\.[0-9]+" to mapOf\(' plugin/src/main/kotlin/org/jetbrains/qodana/Checksums.kt` → 25; `grep -n 'QODANA_SHA_256=' orb/commands/scan.yml` → `56:` (index-55 write = 1-based :56); `grep -n 'LC_ALL' common/update-cli.js` → `185:`; `grep -n 'substring(1)' common/update-cli.js` → `82:`; anchored at repo root.
**Coverage caveat:** update-cli.js has NO upstream test (release tooling); behavior pinned by the executed anchors above + graph spans (`updateCliChecksums` :88-105, `updateCircleCIChecksums` :107-117 resolved line-exact).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "updateCliChecksums checksums.txt latest release", limit: 5 });
```
(rank-1 `common.update-cli.updateCliChecksums` :88-105; sibling twin hits inside `vsts/QodanaScan/index.js` are compiled bundle output — ignore.)

## Verdict
Adopt the generated-checksum-table + single-script multi-surface propagation pattern for any repo that verifies one external binary from several ecosystems; adapt which surfaces exist (inline CI pin vs config table vs generated source). Omit the positional line-index write — regenerate the whole consumer file instead — unless you control the template. Never trim historical rows from the checksum map while any released consumer still resolves them.
