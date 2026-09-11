<!-- capsule-v2 -->
# Shared-plugin descriptor-train families — how do you detect that one plugin build serves several IDEs?

**Source:** JetBrains IDE distributions (proprietary distribution), pins as in leaf Provenance pass 10; Codebase Memory `jetbrains-*` (resource plane, direct extraction). **Question:** Given the same plugin directory in many IDE installs, how do you tell whether they are byte-twins, same-payload re-stamps, or genuinely divergent builds?

## Connected graph-selected seam
**Path/Symbol:** `<product>/plugins/{terminal,DatabaseTools,grid-core-plugin,uml}/lib/*.jar` → `META-INF/plugin.xml`; method = md5 over descriptor with `<version>` and `since-build/until-build` NORMALIZED to empty.
**Signature:** raw digest differs per install; normalized digest groups into families.
**Data Shape:** normalized families at these pins — terminal.jar: {cl,go,ps,py,rr,rm,ws,dg}×8 identical payload · {psl,rider}×2 · dataspell alone · mps alone. DatabaseTools: SAME 8-product majority · {psl,rider} · dataspell alone. grid-core-plugin: 1 digest over ALL 10 installs (fully uniform). uml: 9-install family + dataspell outlier (261-train). Raw digests are ALL distinct because every descriptor self-stamps `<version>` = since = until = the HOST product's exact build number.
**Pattern rule:** majority-family + per-train outliers is the signature of ONE plugin codebase released per platform train: 262.9437.* mainstream vs rider's 262.8665.* line vs DataSpell/MPS 261.* line.

### Decisive source
```text
terminal.jar META-INF/plugin.xml diff between any two 262.9437 installs:
-  <version>262.9437.136</version>
-  <idea-version since-build="262.9437.136" until-build="262.9437.136" />
+  <version>262.9437.163</version>
+  <idea-version since-build="262.9437.163" until-build="262.9437.163" />
(1 hunk total; jar entry counts equal: 1453 == 1453)

normalized-digest families:
  terminal   3256b74858 ×8 {cl,go,ps,py,rr,rm,ws,dg} | 2139da812a ×2 {psl,rider} | ds | mps
  dbtools    5ae34a5f86 ×8 same-majority           | e045ef2172 ×2 {psl,rider} | ds
  grid-core  87fea12b2f ×10 all
  uml        b587752f91 ×9                          | e01b992cb8 {ds}
```

**Flow:** plugin team builds once per train → each product's installer embeds the jar with its OWN build number stamped into the descriptor → naive byte-compare reports N different plugins → normalization isolates the stamp and reveals the true release family → outliers align exactly with the known train boundaries (rider micro-line, 261 DataSpell/MPS).
**Invariant:** descriptor version stamps track the HOST build, never the plugin's own upstream version; equality of payload can only be decided after stamp normalization. This generalizes the pass-3 release-train finding from lib jars to plugin granularity.
**Probe:** `python3 - <<'EOF'\nimport zipfile, hashlib, re\nJB='$REFERENCE_ROOT/reference/jetbrains'\nfor j in sorted(__import__('glob').glob(f'{JB}/*/plugins/terminal/lib/terminal.jar')):\n    t=zipfile.ZipFile(j).read('META-INF/plugin.xml').decode()\n    t=re.sub(r'<version>[^<]*</version>','<version/>',t)\n    t=re.sub(r'since-build="[^"]*" until-build="[^"]*"','since-build="" until-build=""',t)\n    print(j.split('/')[-5], hashlib.md5(t.encode()).hexdigest()[:10])\nEOF` → 8 installs share 3256b74858; psl+rider share 2139da812a; ds/mps unique.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-datagrip", query: "terminal plugin actions", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: stamp-normalized digest comparison as THE twin-detection primitive for installed-build studies; treat descriptor versions as host-stamps. Adapt thresholds for your fleet. Omit vendor-specific train calendars.
