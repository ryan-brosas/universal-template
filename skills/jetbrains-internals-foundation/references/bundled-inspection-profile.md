<!-- capsule-v2 -->
# Bundled default inspection profile — how does a product ship its out-of-box rule activation state?

**Source:** JetBrains IDE distributions (proprietary distribution; study/reference use only); direct jar reads; Codebase Memory `jetbrains-phpstorm`. **Question:** Where does the DEFAULT severity/enabled state of inspections live if every user-visible profile edit persists `shortName`s — and how does a lighter product tier differ from the full one?

## Product-default profile as data
**Path/Symbol:** `lib/intellij.php.resources.jar!inspectionProfiles/PhpStormLight.xml` → `<component name="InspectionProjectProfileManager"><profile version="1.0">`.
**Signature:** `<inspection_tool class="SHORT_NAME" enabled="false" level="INFORMATION" enabled_by_default="false"/>` inside `<profile version="1.0">` with `<option name="myName" value="PhpStorm Light"/>`.
**Data Shape:** 6,339-byte XML listing ~100 `Php*Inspection` entries, ALL disabled INFORMATION-level (plus `PhpUnused` WEAK WARNING and `GrazieInspection` GRAMMAR_ERROR off). Cluster census: exactly 2 occurrences — phpstorm-light + phpstorm, same jar name `intellij.php.resources.jar`. No other IDE ships a bundled `inspectionProfiles/*.xml`.

### Decisive source
```xml
<component name="InspectionProjectProfileManager">
  <profile version="1.0">
    <option name="myName" value="PhpStorm Light"/>
    <!-- Disabled PHP INFO inspections -->
    <inspection_tool class="PhpAddOverrideAttributeInspection" enabled="false"
                     level="INFORMATION" enabled_by_default="false" />
    ...
    <inspection_tool class="PhpUnused" enabled="false" level="WEAK WARNING" enabled_by_default="false" />
    <inspection_tool class="GrazieInspection" enabled="false" level="GRAMMAR_ERROR" enabled_by_default="false" />
  </profile>
</component>
```

**Flow:** engine builds effective settings = built-in per-inspection defaults (from `localInspection` attrs) overlaid by the active profile's `class`-keyed overrides → bundled profile ships ONLY the deltas it wants flipped off (comment-delimited block) → user edits persist more `class` keys alongside.
**Invariant:** `class` here is the `localInspection` `shortName`, NOT the implementation FQN — renaming a shortName orphans this file's entries silently (same stability contract as the catalog capsule). A bundled profile must stay a DELTA: listing unchanged tools duplicates upstream defaults and rots.
**Probe:** `unzip -p phpstorm/lib/intellij.php.resources.jar inspectionProfiles/PhpStormLight.xml | grep -c enabled=\"false\"` → ≥100, all `level="INFORMATION"` except two; `for p in pycharm webstorm; do unzip -l $p/lib/*.jar | grep -c inspectionProfiles || true; done` → 0 (only the PhpStorm family ships one).
**Coverage caveat:** resource-plane capsule; cited via direct jar extraction (installed builds have no test runner).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm", query: "inspection profile manager default profile", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: default analysis state ships as a delta-over-defaults profile keyed by stable rule ids; product tiers differentiate via bundled profile data, not code forks. Adapt the file format to your host's settings serialization. Omit IntelliJ's profile UI internals. This is the third leg of the inspection triad: catalog-registration (declaration) → description-catalog (docs) → this capsule (default activation).
