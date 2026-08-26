<!-- capsule-v2 -->
# Report artifact publication triples — how do you hand a whole results directory to three artifact stores that share nothing?

**Source:** qodana-action Apache-2.0 `main@e0675fbe…`; Codebase Memory `qodana-action`. **Question:** One tool emits a results directory; GitHub wants a zip artifact, Azure wants container artifacts plus SARIF for its Scans tab, GitLab wants files inside the project dir. What is shared and what diverges?

## Shared zip kernel + three publication postures
**Path/Symbol:** zip kernel `common/qodana.ts:getFilePathsRecursively` (:404-418), `createZipFromFolder` (:420-431), `compressFolder` (:438-451); publishers `scan/src/utils.ts:uploadArtifacts` (:369-385), `vsts/src/utils.ts:uploadArtifacts` (:207-223) + `uploadSarif` (:230-242), `gitlab/src/utils.ts:uploadArtifacts` (:415-429).
**Signature:** `compressFolder(srcDir, destFile): Promise<void>`; `uploadArtifacts(resultsDir, artifactName, execute)` (gitlab twin takes only `resultsDir`).
**Data Shape:** archive = sibling of resultsDir (`path.join(path.dirname(resultsDir), `${artifactName}.zip`)`), DEFLATE stream, every entry `unixPermissions: '777'`.

### Decisive source
```ts
// common/qodana.ts — kernel
const relative = filePath.replace(absRoot, '')      // first-occurrence strip → '/x'-style keys
zip.file(relative, fs.createReadStream(filePath), { unixPermissions: '777' })
await mkdir(path.dirname(destFile), {recursive: true})
zip.generateNodeStream({streamFiles: true, compression: 'DEFLATE'})
  .pipe(fs.createWriteStream(destFile))
// vsts/src/utils.ts — the rename nobody expects
const qodanaSarif = path.join(parentDir, 'qodana.sarif')
tl.cp(path.join(resultsDir, 'qodana.sarif.json'), qodanaSarif)
tl.uploadArtifact('CodeAnalysisLogs', qodanaSarif, 'CodeAnalysisLogs')
// gitlab/src/utils.ts — no zip at all
fs.cpSync(resultsDir, path.join(ciProjectDir, resultDir), {recursive: true})  // RESULTS_DIR override, default '.qodana/results'
```

**Flow:** scan: execute-gate → compress → `artifact.uploadArtifact(artifactName, [archive], workingDir)` → catch-all `core.warning('Failed to upload report – …')`. vsts: identical zip but `tl.uploadArtifact('Qodana', archivePath, artifactName)` with the CONTAINER name hardcoded to `'Qodana'`; separately (called AFTER the publish fan in main :67) uploadSarif copies `qodana.sarif.json` to a sibling literally named `qodana.sarif` (extension dropped!) and uploads it as `CodeAnalysisLogs`, the convention Azure's code-analysis Scans tab consumes. gitlab: plain recursive cpSync into `$CI_PROJECT_DIR/.qodana/results` so the job's `artifacts:paths` picks it up; warns and skips when CI_PROJECT_DIR is absent.
**Invariant:** Every publisher is execute-gated and warn-don't-fail — an artifact failure must never flip a scan verdict that already published results. The zip entries keep absolute-style '/name' keys via first-occurrence replace and 0777 permissions so extraction restores executability; the Azure SARIF rename is load-bearing (the platform expects extension-less `qodana.sarif` under CodeAnalysisLogs) — renaming it back "for consistency" breaks the Scans tab.
**Probe:** EXECUTED at pin: all four jest suites green (common 62 / scan 11 / gitlab 2 / vsts 2); no upstream test drives any uploadArtifacts/uploadSarif/compressFolder variant (fs+network-heavy) — pinned by ranges + byte-exact anchors above (coverage caveat). Deterministic anchor check: `grep -n "unixPermissions: '777'" common/qodana.ts` → :427.
**Coverage caveat:** check_index_coverage ×5 cited paths = no_recorded_issue + metadata_match.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "uploadArtifacts compressFolder createZipFromFolder archive report", limit: 6 });
```
(rank-1 `common.qodana.compressFolder` :438-451; the `vsts.QodanaScan.*` rows are webpack BUILD OUTPUT — never cite.)

## Verdict
Adopt one compression kernel feeding per-host publishers, the execute-gate + warn-don't-fail posture, and sibling-placement naming; adapt the store call and any platform-magic names (Azure's CodeAnalysisLogs + extension-less sarif rename, GitLab's in-project results dir); omit JSZip's 0777 blanket only if your consumers preserve modes themselves.
