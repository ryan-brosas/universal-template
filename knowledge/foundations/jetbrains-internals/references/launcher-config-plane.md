<!-- capsule-v2 -->
# launcher-config-plane — what do idea.properties and *.vmoptions actually control on disk, and what differs per product?

**Source:** JetBrains installed distributions (proprietary), all 10 full Linux installs; md5s below measured at pinned builds. **Question:** Which shipped launcher configs are shared platform contract vs product tuning, and which knobs matter to a porter?

## bin/idea.properties (defaults, commented) + bin/<product>64.vmoptions (active JVM flags)
**Path/Symbol:** `<ide>/bin/idea.properties` — every line ACTIVE is commented (`# idea.config.path=...`); it documents the override protocol: `${user.home}`, `${idea.home.path}` macros, property-to-property refs. `<ide>/bin/<product>64.vmoptions` — the live flag list; `jetbrains_client64.vmoptions` — separate flags for the thin-client persona (see multi-persona-launcher-matrix).
**Signature (idea.properties active keys):** `idea.max.intellisense.filesize=2500` (KiB cap for code assistance), `idea.max.content.load.filesize=20000`, `idea.cycle.buffer.size=1024`, `idea.no.launcher=false`, `idea.dynamic.classpath=false`, `idea.fatal.error.notification` + platform-specific Swing/GL blocks; path vars default to `$user.home/.<Product>/config|system`.
**Data Shape (vmoptions md5 across train):** clion==phpstorm `ca84c7ee…` byte-identical; webstorm==rider `4d94674c…`; pycharm/goland/rustrover/rubymine/datagrip/dataspell each unique → per-product heap identity, shared where products share resource profile.

### Decisive source
```properties
# bin/pycharm64.vmoptions — representative active flags
-Xms256m
-Xmx2048m
-XX:ReservedCodeCacheSize=512m
-XX:+HeapDumpOnOutOfMemoryError
-ea
-Dsun.io.useCanonCaches=false
-Djdk.http.auth.tunneling.disabledSchemes=""
-Djava.nio.file.spi.DefaultFileSystemProvider=com.intellij.platform.core.nio.fs.MultiRoutingFileSystemProvider
-Dawt.toolkit.name=auto
```
Heap ladder (Xms/Xmx): datagrip **750m/256m** (smallest), everything else Xmx=2048m with Xms 128m (web/clion/goland/rustrover/rubymine/phpstorm/rider) or 256m (pycharm/dataspell); CodeCache=512m cluster-wide.

**Flow:** launcher script reads vmoptions → JBR boots → PathClassLoader picks up `-Djava.system.class.loader=...PathClassLoader` from launch args (product-info.json) → idea.properties supplies DEFAULTS only; users override in `~/.<Product>/config/idea.properties` which wins by load order → `brokenPlugins.db` sits beside them as a versioned binary blocklist (magic `\x02\x00\x0fPY-262.9437.2…`, 230KB).
**Invariant:** shipped idea.properties contains NO uncommented path overrides — the file's job is to DOCUMENT the macro language, not to configure; actual config identity comes from `dataDirectoryName` in product-info.json. vmoptions differences ARE the product memory contract (datagrip's 750m ceiling is deliberate).
**Probe:** `md5sum */bin/*64.vmoptions | sort` → collision pairs (clion,phpstorm) and (webstorm,rider) exactly; `grep -c '^#' pycharm/bin/idea.properties` ≈ all non-blank lines commented.
**Retrieve:** not a graph seam: `head -20 <ide>/bin/idea.properties`; census via `for i in */; do echo "$i $(grep -oP '(?<=^-Xmx)\S+' $i/bin/${i%/}64.vmoptions)"; done`.

## Verdict
Adopt: ship a fully-commented properties file as macro documentation + a tiny per-product vmoptions as the ONLY active tuning; let user-dir files override by load order. Adapt macro names. Omit Windows/macOS launcher variants (not present in these Linux installs). Caveat: md5 identities are build-pinned evidence of the sharing pattern, not a stable API — re-hash on any build bump.
