<!-- capsule-v2 -->
# plugin-classpath-txt-mirror — what is the non-text `.txt` at plugins/ root and when do you read it instead of the .dat?

**Source:** JetBrains installed distributions (proprietary), RustRover decisive instance. **Question:** How do you enumerate every bundled plugin's effective descriptor (including inline module payloads) without opening each jar?

## rustrover/plugins/plugin-classpath.txt: binary-prefixed concatenated descriptor dump
**Path/Symbol:** `rustrover/plugins/plugin-classpath.txt` — `file(1)` says `data`; 4,685,707 bytes; first `<idea-plugin` at byte offset 6 after a 6-byte binary header (`02 01 00 19 5b 05`); contains 175 lines matching `<idea-plugin` and 1,068 ESCAPED payloads `&lt;idea-plugin …&gt;`.
**Signature:** concatenation of (a) the platform aggregate descriptor `<id>com.intellij</id>` whose children are capability tokens `<module value="com.intellij.modules.rust-capable|rustrover|python-in-mini-ide-capable|nativeDebug-plugin-capable|database-capable|…"/>`, then (b) every bundled plugin's META-INF/plugin.xml in turn (ids observed: AngularJS, com.intellij.cidr.parallelStacks, org.jetbrains.plugins.docker.gateway, Docker, per-color-scheme ids, …).
**Data Shape:** inside plugin descriptors, content modules appear as `<module name="intellij.profiler.common">&lt;idea-plugin visibility="public" package="com.intellij.profiler"&gt;…&lt;/idea-plugin&gt;</module>` — i.e., each module's own mini-descriptor is INLINED as escaped XML, carrying `visibility=` AND `package=` (exported package roots) attributes you will not see in the plain jar descriptor's module tag.

### Decisive source
```text
$ xxd -l 24 plugins/plugin-classpath.txt   # 6-byte header, then XML
00000000: 0201 0019 5b05 3c69 6465 612d 706c75...  <idea-plugin xmlns:xi=...
$ grep -n 'idea-plugin' plugins/plugin-classpath.txt | head -3
6:<idea-plugin xmlns:xi="http://www.w3.org/2001/XInclude">
7179:    <module name="intellij.libraries.jgoodies.binding" loading="embedded">&lt;idea-plugin /&gt;</module>
7181:    <module name="intellij.profiler.common">&lt;idea-plugin visibility="public" package="com.intellij.profiler"&gt;
```

**Flow:** build assembles install → serializes classpath+descriptor snapshot into this artifact next to a small binary header → tools/boot can bulk-read the whole plugin surface from ONE file; a miner greps it to census capability tokens, module visibilities, and exported packages across all bundled plugins without unzipping jars.
**Invariant:** it is a MIRROR, not a config: the runtime truth remains modules/module-descriptors.dat (+ per-jar META-INF/plugin.xml); never edit. Root-tag discipline still applies (platform aggregate vs per-plugin descriptors vs escaped module payloads) before any attribute census; escaped payloads must be unescaped (&lt; &gt; &quot;) before XML parsing.
**Probe:** `python3 - <<'EOF'
data=open('rustrover/plugins/plugin-classpath.txt','rb').read()
print(data[:6].hex(), data.count(b'<idea-plugin'), data.count(b'&lt;idea-plugin'), len(data))
EOF` → `020100195b05 175 1068 4685707` — the two counts are disjoint byte sequences: 175 raw `<idea-plugin` elements (top-level + nested real XML), 1,068 escaped `&lt;idea-plugin` payloads.
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-rustrover", paths: ["plugins/plugin-classpath.txt"] });
```
(no_recorded_issue / freshness not_tracked — binary-prefixed file is outside graph parsing; direct read is the evidence path.)

## Verdict
Adopt: treat a product-side concatenated descriptor mirror as the fast census surface for capabilities + module payload attributes (visibility/package exports); keep .dat/jars authoritative. Adapt: header handling (strip N bytes) and escape decoding for your grammar. Omit: JetBrains' exact serialization header semantics. Caveat: structure characterized by byte/grep probes of one install; the 6-byte header meaning is unverified.
