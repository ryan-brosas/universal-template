<!-- capsule-v2 -->
# Qodana YAML inspection profiles — how does JetBrains ship a static-analysis rule catalog as data?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** What grammar lets a CI linter catalog hundreds of inspections per language without shipping code — and how do tiers compose?

## Connected graph-selected seam
**Path/Symbol:** `<install>/plugins/qodana/lib/qodana.jar:qodana-profiles/.idea/inspectionProfiles/*.yaml` (13 files in webstorm/rider/goland/rustrover/phpstorm; md5 of qodana.recommended.yaml = `25cc97c6d967d1a7c19b7e4d9c41dc08` IDENTICAL across all five).
**Signature:** n/a (data plane).
**Data Shape:** keys `baseProfile` (parent name, e.g. "Project Default" or "empty"), `name`, `include:` (list of sibling YAML files), `groups:` (named groups whose members are inspection simple-names OR `"category:<path>"` selectors OR nested group ids), `inspections:` (list of `{inspection|group, enabled}`). Flavor files reuse names per family (`qodana-js.recommended.yaml` vs `qodana-dotnet.recommended.yaml` — same `name: "qodana.recommended"`, different content).

### Decisive source
```yaml
# qodana.starter.yaml (whole file):
baseProfile: "Project Default"
name: "qodana.starter"

include:
  - "qodana.recommended.yaml"
  - "qodana.starter.exclusions.yaml"
```
and from qodana.recommended.all.yaml:
```yaml
  - groupId: JSInspections
    groups:
      - "category:JavaScript and TypeScript"
      - "category:Angular"
      - "JSRelatedInspections"     # group-id references compose like category selectors
```

**Flow:** recommended.all.yaml (44 `category:` selectors) includes the language-family leaves → starter includes recommended PLUS an exclusions file whose terminal lines are `inspections: [{group: StarterExcluded, enabled: false}]` flipping ONE group that aggregates 28 category selectors + 54 named inspections, each with an inline rationale comment ("Style", "Spam", "Heavy") → sanity composes baseProfile:"empty" + dotnet.static + rust groups. Tiers are INCLUDE-COMPOSITION, not copies.
**Invariant:** exclusion-by-category is the tier's whole personality (starter strips style/naming/spam categories with inline rationale comments); a porter must keep include-order semantics — later flips override earlier enables by group reference.
**Probe:** from `<install>` root:
`unzip -p plugins/qodana/lib/qodana.jar qodana-profiles/.idea/inspectionProfiles/qodana.starter.yaml | tail -3` ends with the two-file include list; and
`for p in webstorm rider goland rustrover phpstorm; do unzip -p $p/plugins/qodana/lib/qodana.jar qodana-profiles/.idea/inspectionProfiles/qodana.recommended.yaml | md5sum; done` prints five identical hashes.
**Coverage caveat:** jar resource plane — not indexed; unzip probes are the retrieval primitive.

## Get live surrounding code
**Retrieve:** graph covers only the code plane; profile loading lives inside qodana.jar classes (`org/jetbrains/qodana/staticAnalysis/profile/providers/QodanaEmbeddedProfilesProvider.class` — name-level evidence via `unzip -l`). No BM25 target (adjudicated wrong-plane).

**Descriptor census (qodana.jar META-INF/plugin.xml, unzip -p + grep -o):** 26 distinct `intellij.qodana.*` content modules (coverage ×6 per-language variants, inspectionKts family ×5 incl. .mcp/.kotlin/.js/.java), 53 `<extensionPoint>` declarations, 52 `<extensions>` blocks across 10 namespaces (`com.intellij`×23, `org.intellij.qodana`×15, `org.jetbrains.qodana.inspectionKts`×4, …), 6 `<globalInspection hasStaticDescription="true">` coverage checks (Go/Js/Php/…), `commandLineInspectionProjectConfigurator` (PHP) — the plugin that makes the headless persona work is itself a normal v2 modular plugin consuming the SAME EP grammar as everything else in this pack.

## Verdict
Adopt: include-composed YAML catalogs with named groups + `category:` selectors as THE portable static-analysis-catalog pattern. Adapt: your host's inspection ids/categories. Omit: Qodana's cloud/SARIF plumbing. Erratum scope: extends bundled-inspection-profile ([DONE:221]) from XML delta-profiles to the YAML composition layer JetBrains ships for CI linting.
