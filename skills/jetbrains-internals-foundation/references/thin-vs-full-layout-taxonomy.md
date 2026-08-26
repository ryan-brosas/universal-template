<!-- capsule-v2 -->
# thin-vs-full-layout-taxonomy — why do air and mps break every full-install assumption?

**Source:** JetBrains installed distributions (proprietary), `air/` + `mps/` decisive instances. **Question:** Which install shapes lack the IDE manifest plane entirely, and what do they ship instead?

## Two non-standard layouts
**Path/Symbol:** `air/lib/app/` (Fleet-style runtime, NOT IntelliJ module layout): `bootstrap/`, `bin/{air,printenv}`, `libs/*.so` (skiko GTK renderer, jnidispatch), `keymaps/keymap.pdf` (PDF only — no XML keymap plane), `icons/{appicon,os-appicon}.png`, one squashed util jar (`util-zip-squashed-252.16432.jar`). `resources/jetbrainsd.tar.gz` = a native supervisor-daemon SEED (CORRECTION 2026-08-25: NOT the backend IDE — it is one GraalVM-native-image ELF, no JVM, no IDE jars; see fleet-jetbrainsd-native-daemon-seed). The remote backend is the fsdaemon download pinned by ship.json meta (see fleet-backend-platform-matrix). `mps/lib/` = 384 flat jars incl. `intellij.platform.monolith.jar` with EMPTY META-INF (no plugin.xml surface at top level) + `build.properties`/`build.number`/`build.txt` version files.
**Signature:** absence probes: no `product-info.json layout[]` (both), no `plugins/*/lib/modules/` v2 jars in air, no `bin/*64.vmoptions` product file in air.
**Data Shape:** air product-info.json HAS launch[] (single persona) but NO modules/fileExtensions/layout keys; mps has neither.

### Decisive source
```
$ ls air/lib/app
annotations-26.0.2.jar  bin  bootstrap  code-cache  fonts  icons  keymaps
fleet.dock.bootstrap-262.132.35.jar  fleet.util.modules-262.132.35.jar
libs  util-zip-squashed-252.16432.jar
$ ls mps | head
about.txt  bin  build.number  build.properties  build.txt  jbr  lib  license  plugins  product-info.json  readme.txt  samples.zip
$ python3 -c "import zipfile;print(zipfile.ZipFile('mps/lib/intellij.platform.monolith.jar').namelist()[:5])"
[]
```

**Flow:** air boots its own Fleet-lineage runtime from `bootstrap/`; the LOCAL supervisor is `jetbrainsd` (protocol dispatch + workspace/snapshot/update daemon, unpacked from resources), while IDE functionality stays with the fsdaemon artifact downloaded per platform — so porting questions about "the IDE backend" target the ship.json-pinned download, and questions about local supervision target jetbrainsd; mps is a legacy-monolith distribution: platform code present as one jar but manifest metadata lives in its own descriptor formats (DSL workbench, outside the IntelliJ-lang EP grammar mined elsewhere).
**Invariant:** for BOTH, every full-install capsule's probe pattern (`unzip -p <ide>/lib/…jar META-INF/...`) returns nothing — treat "no lib/product-backend.jar" as the fast discriminator of a non-standard layout BEFORE mining.
**Probe:** `ls air/lib/app && ls air/resources && ls mps/lib | wc -l` → app dirs shown above, `jetbrainsd.tar.gz`, `384`.
**Retrieve:** graph projects jetbrains-air (2,968 nodes) / jetbrains-mps (1,245) index no code symbols, but DO index loose config files as File+Variable nodes — JSON manifests are fully retrievable (`search_graph` label=Variable + `get_code_snippet` returns whole values); only jar-internal XML needs filesystem probes. Air's own plane now has owning capsules: fleet-bundle-catalog-signed-manifests, fleet-content-addressed-parts-layers, fleet-dock-modulepath-layer-lists, fleet-backend-platform-matrix.

## Verdict
Adopt the discriminator ladder: (1) has `product-backend.jar`+modules/ → full IDE; (2) has `lib/app/bootstrap`+jetbrainsd → thin client over remote backend; (3) monolith jar w/o META-INF surface → legacy platform. Omit mining air/mps under IDE-MANIFEST assumptions (plugin.xml/EP grammar) — that plane is genuinely absent here. UPDATE (2026-08-25 pass): air's OWN distribution kernel is rich and now mined — signed bundle catalog, content-addressed code-cache layers, dock module-path lists, backend platform matrix, per-component license SBOMs, JBR tuning plane; see the fleet-* capsules. The native control plane is ALSO mined: jetbrainsd seed tarball (`fleet-jetbrainsd-native-daemon-seed`), Rust launcher CLI (`fleet-rust-launcher-cli-plane`), shell-env capture binary (`fleet-shell-env-capture-binary`), windowing shims (`fleet-desktop-windowing-native-shims`) — the earlier "jetbrainsd = backend IDE" flow claim in this capsule was WRONG and has been corrected above (jetbrainsd is a native local supervisor; the IDE backend is the ship.json-pinned fsdaemon download). Remaining unmined: jetbrainsd snapshot/update protocol strings-only deep-dive; util-zip-squashed dedicated capsule; bundles.json cross-train diff when a second air build is indexed.
