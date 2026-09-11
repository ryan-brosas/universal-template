<!-- capsule-v2 -->
# Build-tool plugin twins (Gradle/Maven/orb) — how does the same installer contract express itself across Gradle tasks, Maven mojos, and a CircleCI orb?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** What is shared and what differs when embedding qodana into JVM builds vs CircleCI?

## Installer.setup verify-or-redownload + TeeOutputStream error mining + ci.skip orb
**Path/Symbol:** Gradle `plugin/src/main/kotlin/org/jetbrains/qodana/Qodana.kt:Installer` (whole class incl. companion), `QodanaPlugin.kt` (extension conventions + task registration, gradle>=6.6 guard), `tasks/QodanaScanTask.kt` (@UntrackedTask Exec subclass); Maven `maven/src/main/kotlin/org/jetbrains/qodana/maven/QodanaScanMojo.kt` (ProcessBuilder variant); CircleCI `orb/commands/scan.yml` (bash inline); checksum data `plugin/.../Checksums.kt` (generated versioned map).
**Signature:** `Installer().setup(path: File, version: String = getLatestVersion()): String` (absolute path).
**Data Shape:** CHECKSUMS keyed `version → {platform_arch → sha256}` — same shape as common/cli.json but multi-version.

### Decisive source
```kotlin
if (path.exists()) {
    try {
        if (!useNightly) verifyChecksum(path, getChecksum(version))
        return path.absolutePath                    // cached binary still valid
    } catch (e: IOException) {
        log.warning("Checksum verification failed. Redownloading the binary.")
    }
    path.delete()                                   // corrupt cache ⇒ redownload
}
download(downloadURL, path)
if (!useNightly) verifyChecksum(path, getChecksum(version))
```
Gradle task failure mining:
```kotlin
standardOutput = TeeOutputStream(System.out, os)   // stream to console AND buffer
runCatching { super.exec() }.exceptionOrNull()?.let {
    val message = os.toString().lines().find { line ->
        line.startsWith("Inspection run is terminating")
    } ?: "Qodana finished with failure. Check logs and Qodana report for more details."
    throw TaskExecutionException(this, GradleException(message, it))
}
```
Orb install block: curl jb.gg installer pinned `v2026.2.0`, then `echo "$QODANA_SHA_256 $CLI_DIRECTORY/qodana" | sha256sum -c`, `NONINTERACTIVE=1` exec, restore/save cache over BOTH cache-dir and the CLI dir.

**Flow:** setup(): existing binary? verify (unless nightly) → valid ⇒ reuse; corrupt ⇒ delete+redownload+reverify → returns executable path. Task/Mojo assemble identical arg skeletons (`scan --project-dir --results-dir --cache-dir [args…])`, pin PATH/HOME env from the PARENT process (protects against Gradle/Maven env sanitization), mark env QODANA_ENV=qodana, capture output to mine the "Inspection run is terminating" line for a human-meaningful failure message (Maven twin uses redirectErrorStream + BufferedReader with the SAME sentinel prefix). Plugin registration wires provider-conventions so extension overrides flow lazily; the orb achieves the whole contract in bash with primary/additional cache keys mirroring action.yaml defaults.
**Invariant:** The verify-or-redownload loop must attempt reuse BEFORE downloading and must re-verify AFTER download; nightly bypasses BOTH checks. Error-message mining keys on the exact upstream log prefix "Inspection run is terminating" — change it and every build-tool integration degrades to generic messages silently.
**Probe:** `plugin/src/test/kotlin/.../tasks/QodanaScanTaskTest.kt` (incl. 'task loads from the configuration cache' :87-99 per graph) exercises the task wiring; Installer/orb bodies untested upstream (coverage caveat; ranges cited).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "Installer setup verifyChecksum QodanaScanTask", limit: 8 });
```

## Verdict
Adopt verify-or-redownload caching + output-teeing sentinel mining for any wrapper that shells out to an analyzer; adapt per build ecosystem (Exec task vs Mojo vs bash step); omit the orb's hardcoded sha256 pinning style in favor of generated tables once you have >1 version.
