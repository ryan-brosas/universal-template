<!-- capsule-v2 -->
# Bundled light-profile XML — the product-tier inspection default, precisely

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** What EXACTLY does the one bundled XML inspection profile shipped cluster-wide contain, entry by entry?

## Connected graph-selected seam
**Path/Symbol:** `phpstorm-light/lib/intellij.php.resources.jar:inspectionProfiles/PhpStormLight.xml` (52 lines; 45 `inspection_tool` entries).
**Signature:** n/a (data plane; extends bundled-inspection-profile [DONE:221] with full-content verification at pass-12 pins).
**Data Shape:** root `<component name="InspectionProjectProfileManager"><profile version="1.0">`; identity via `<option name="myName" value="PhpStorm Light"/>`; every entry is a DISABLED delta row: `class="<InspectionSimpleName>" enabled="false" level="..." enabled_by_default="false"`.

### Decisive source
```
$ unzip -p lib/intellij.php.resources.jar inspectionProfiles/PhpStormLight.xml \
    | grep -oE 'level="[^"]+"' | sort | uniq -c
      1 level="GRAMMAR_ERROR"
     43 level="INFORMATION"
      1 level="WEAK WARNING"
```
Tail rows (verbatim semantics): 43 PHP INFO-class inspections silenced + `PhpUnused` (WEAK WARNING) + `GrazieInspection` (GRAMMAR_ERROR). Comment markers wrap the block: `<!-- Disabled PHP INFO inspections -->` … `<!-- End of disabled PHP INFO inspections -->`.

**Flow:** product tier ships this single profile → on first project open the "light" tier resolves to Project Default MINUS these rows → the ONLY product differentiation JetBrains ships as profile data is NOISE SUPPRESSION (info-level style nags + grammar checker), not extra checking.
**Invariant:** a bundled profile is a DENIAL LIST over defaults — entries are almost all `enabled="false"`; porting it as an enable-list inverts its meaning.
**Probe:** from phpstorm-light install root:
`unzip -p lib/intellij.php.resources.jar inspectionProfiles/PhpStormLight.xml | grep -cF 'enabled="false"'` prints `45`;
`unzip -l lib/intellij.php.resources.jar | grep -c inspectionProfiles` prints `1`. Cluster: still the ONLY lib-rooted bundled XML profile (qodana YAML catalogs are the CI-side counterpart — see qodana-yaml-inspection-catalog).
**Coverage caveat:** jar resource plane unindexed; unzip probes are the primitive.

## Get live surrounding code
**Retrieve:** no BM25 target for jar resources (adjudicated wrong-plane); deterministic probes above ARE the retrieval path. For the runtime side:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "inspection profile manager default profile", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: noise-suppression-only bundled profiles as the product-tier pattern. Adapt: severity vocabulary to your host ladder. Omit: IntelliJ profile resolution order. Erratum vs [DONE:221] wording: "product tiers differentiate via profile data" now verified EXACTLY — 45 disabled rows, three severity classes, zero enabled additions.
