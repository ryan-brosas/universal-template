<!-- capsule-v2 -->
# fleet-jetbrainsd-native-daemon-seed — how does the Fleet thin client seed its LOCAL supervisor daemon without a JVM?

**Source:** JetBrains installed distributions (proprietary) air build `262.132.35`, pin `?@?` (no .git; installed product). Codebase Memory `jetbrains-air` (2,968 nodes, gen 2026-08-24T14:00:27Z). **Question:** What exactly is `resources/jetbrainsd.tar.gz`, and what contract does the unpacked daemon expose that a porter must reproduce?

## The installer-seeded native app-daemon
**Path/Symbol:** `resources/jetbrainsd.tar.gz` → `jetbrainsd/bin/{jetbrainsd,libjnidispatch.so,VERSION}` + `jetbrainsd/licenses/**` (86 entries total). **Signature:** ELF 64-bit LSB pie executable, x86-64, dynamically linked, stripped — 86,444,072 B; `bin/VERSION` = `0.8.5538` (version line INDEPENDENT of build 262.132.35).
**Data Shape:** single-binary tarball: 4 bin entries + 81 license entries + root dir. License plane INSIDE the payload: `third-party-libraries.json` = flat list of 54 rows sharing the install-level schema `{name, version, url, license, licenseUrl}` (first row: "7-Zip", LGPL 2.1) + `third-party-libraries.spdx.json` = SPDX-2.3 doc, `SPDXRef-DOCUMENT`, name "jetbrainsd", 38 packages.

### Decisive source
\`\`\`text
$ file jetbrainsd/bin/jetbrainsd
ELF 64-bit LSB pie executable ... stripped
$ cat jetbrainsd/bin/VERSION
0.8.5538
$ ldd jetbrainsd/bin/jetbrainsd   # glibc-only footprint
linux-vdso.so.1 / libpthread.so.0 / libdl.so.2 / librt.so.1 / libc.so.6 / ld-linux-x86-64.so.2
$ strings jetbrainsd/bin/jetbrainsd | grep -c 'JETBRAINS_DAEMON_[A-Z_]'   # env vocabulary
16 distinct vars (strings table shows two with a trailing 'H' artifact)
BUNDLES/CACHE/DATA/LOG/SOCKET _DIRECTORY, DELAY_SERVER,
STARTUP_TIMEOUT_MS, STARTUP_STATUS_POLL_TIMEOUT_MS,
UPDATE_HOST, UPDATE_QUERY, UPDATE_INITIAL_DELAY_SECONDS,
SNAPSHOT_BASE_PATH, PREFER_SNAPSHOT_VERSION,
OS_URI_SCHEME_HANDLER, URL_HANDLER_LAUNCHER, SSH_ASKPASS_MIRROR_PROMPT
"Adding jetbrains:// protocol handler to mimeapps.list"
"jetbrainsd is already the handler for jetbrains:// protocol. Skipping re-registering"
"$XDG_CONFIG_HOME/JetBrains/IjentDeploy/env.sh"  "$XDG_CONFIG_HOME/JetBrains/ToolboxSshDeploy/env.sh"
fleet/kernel/rete/Query  rhizomedb/Datom  com_jetbrains_app_daemon_endpoints_{authn,ijent,intellij,remDev,ssh,system,test,workspaces}
\`\`\`

**Flow:** installer ships tarball → daemon unpacks/runs from its data dirs → registers jetbrains:// URI scheme into mimeapps.list (idempotent re-check) → supervises workspaces/snapshots (SNAPSHOT_BASE_PATH, PREFER_SNAPSHOT_VERSION gates ijent snapshot vs release) → self-updates on UPDATE_HOST/UPDATE_QUERY after UPDATE_INITIAL_DELAY_SECONDS → per-domain endpoints (authn/ijent/intellij/remDev/ssh/system/test/workspaces) compiled INTO the image.
**Invariant:** the payload carries NO JVM and NO IDE jars — it is a GraalVM native-image of Kotlin fleet code (rete query kernel + rhizomedb CRDT store visible in symbols); the remote IDE backend stays the separately-downloaded fsdaemon pinned by ship.json meta (`fleet-backend-platform-matrix`). Do not conflate the two daemons.
**Probe:** \`tar -tzf resources/jetbrainsd.tar.gz | wc -l\` → \`86\`; \`cmp lib/app/libs/libjnidispatch.so <unpacked>/jetbrainsd/bin/libjnidispatch.so && echo IDENTICAL\` → \`IDENTICAL\` (one provenance, two ride-alongs).

## Get live surrounding code
**Retrieve:** binary seam has no graph nodes — negative retrieval IS the evidence:
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-air", query: "jetbrainsd", limit: 5 });
// → total: 0 ; check_index_coverage("resources/jetbrainsd.tar.gz") → no_recorded_issue / freshness not_tracked
\`\`\`

## Verdict
Adopt the pattern: seed a native supervisor as a versioned single-file tarball with its license plane embedded and an idempotent OS-integration step; drive it entirely by a namespaced env vocabulary. Adapt directory names and the jetbrains:// scheme to your product. Omit the GraalVM/Kotlin internals, JetBrains update host, and ijent SSH backend specifics (proprietary, strings-only here). Coverage caveat: no graph nodes (binary ignored-suffix plane); claims rest on executed probes over the pinned install.
