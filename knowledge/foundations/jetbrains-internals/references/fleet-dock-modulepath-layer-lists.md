<!-- capsule-v2 -->
# Fleet dock module-path layer lists — how does a JPMS app boot when even its classpath is content-addressed?

**Source:** JetBrains Fleet install `air` 262.132.35 (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-air` (`lib/app/bootstrap/fleet.dock.*.module.path.txt`, `exports.txt`, `desktopExports.txt`: no_recorded_issue; freshness not_tracked — plain text lists). **Question:** How does the desktop "dock" app receive its exact module graph without any launcher script listing jar paths?

## Connected graph-selected seam
**Path/Symbol:** `lib/app/bootstrap/fleet.dock.{api,bootstrap,desktop,runtime}.module.path.txt` (2.7K / 1.7K / 73K / 32K) + `lib/app/bootstrap/exports.txt` vs `desktopExports.txt`.
**Signature:** each .txt = repeated line PAIRS: `<sha256>/<jar-name>` newline `<base64 serializedModuleDescriptor>`; each exports file = one `--add-opens|--add-exports|--add-reads <module>/<package>=<target>` per line.
**Data Shape:** four disjoint layers compose the dock app: `api` (smallest, contracts only), `bootstrap`, `runtime`, and `desktop` (largest by far — all AWT/Skiko surface lives there). Entries include first-party modules (`fleet.dock.api-262.132.35.jar` → module `fleet.dock.api`) AND third-party ones (`jna-5.17.0.jar` → module `com.sun.jna`), each with its own inline descriptor.

### Decisive source
```text
$ head -4 lib/app/bootstrap/fleet.dock.api.module.path.txt
7bcb9fd489f8ecc3c1adb786ba99101a24884ce47aaac68e5dd05a8289b252ce/fleet.dock.api-262.132.35.jar
yv66vgAAAD0ADgEAC21vZHVsZS1pbmZvBwAB...   <- base64 module-info.class for fleet.dock.api
855d82964d62c9def04c1fbca7a0dc5d1e672ff8d094462a1ec59dd3685300c1/jna-5.17.0.jar
yv66vgAAAD0AFAEAC21vZHVsZUluZm8...        <- com.sun.jna@5.17.0

$ cat lib/app/bootstrap/desktopExports.txt   # delta vs exports.txt
--add-opens=java.base/java.lang=ALL-UNNAMED
--add-opens=java.base/java.lang=util.zip.squashed
--add-opens=java.base/jdk.internal.module=fleet.util.modules
--add-opens=java.base/java.util=fleet.modules.jvm
--add-reads=org.bouncycastle.pg=java.logging
--add-exports=java.base/sun.nio.ch=fleet.util.core
+ --add-exports=java.desktop/sun.java2d=ALL-UNNAMED     \ desktop-only tail:
+ --add-exports=java.desktop/sun.awt=ALL-UNNAMED         \ opens sun.* for the
+ --add-opens=java.desktop/java.awt=ALL-UNNAMED          \ noria HTML renderer
+ --add-exports=java.desktop/sun.font=fleet.noria.html
+ --add-exports=java.desktop/sun.awt=fleet.noria.html
```

**Flow:** dock boot reads the four lists → resolves each `<hash>/<jar>` against `lib/app/code-cache/<hash>/` (the same store every other payload uses) → verifies bytes → reconstructs the module path from the inline descriptors → applies the exports ladder as JVM args → launches. Headless boots use `exports.txt`; `desktopExports.txt` is byte-identical for its first five lines then appends exactly five `java.desktop` grants (`sun.java2d`, `sun.awt` ×2, open `java.awt`, `sun.font` → `fleet.noria.html`) for the HTML renderer.
**Invariant:** the descriptor list is authoritative — a jar present in code-cache but absent from the four lists is dead weight; a listed hash missing from the cache is a hard boot failure. The exports ladder exists precisely because strong encapsulation would otherwise block the platform-internals access the UI needs.
**Probe:** from install root: `wc -l lib/app/bootstrap/fleet.dock.*.module.path.txt | sort -k2` → api 9, bootstrap 7, desktop 163, runtime 71 (line PAIRS `<hash-jar>`+`<descriptor>`, so ~half that many jars per layer); `diff lib/app/bootstrap/exports.txt lib/app/bootstrap/desktopExports.txt` → only the appended five `java.desktop` lines (both files lack a trailing newline); `sed -n 2p lib/app/bootstrap/fleet.dock.api.module.path.txt | base64 -d | od -A n -t x1 -N 4` → `ca fe ba be`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-air", label: "File", file_pattern: "module.path", detail: "ids", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-air", qualified_name: "jetbrains-air.lib.app.bootstrap.fleet.dock.api.module.path.txt.__file__" });
```

## Verdict
Adopt: ship the module graph as data (hash+descriptor pairs) so the same immutable cache feeds every process role; keep JPMS override ladders as small per-persona files. Adapt: your layer names and renderer internals. Omit: noria/Skiko rendering specifics. Companion seams: fleet-content-addressed-parts-layers (the store these hashes resolve into), fleet-bundle-catalog-signed-manifests (catalog side).
