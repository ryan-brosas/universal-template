<!-- capsule-v2 -->
# Requirement model and version-spec grammar — how does the shipped API represent PEP 508 requirements and match them against installed packages?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm` (`lib/src/pycharm-openapi-src`). **Question:** What is the `PyRequirement`/`PyRequirementRelation`/`PyRequirementVersionSpec` data model, and what does the editable-install detection rule look like?

## Connected graph-selected seam
**Path/Symbol:** `lib/src/pycharm-openapi-src/com/jetbrains/python/packaging/PyRequirement.java` — interface citing PEP-508/PEP-440/pip docs in its javadoc; accessors `getName/getPackageName/getVersionSpecs/getExtras`; `getInstallOptions()` with doc note that >1 element implies `--src/-e/--editable/--global-option/--install-option`; matching `PyPackage match(Collection<PyPackage>)` (FIRST satisfying package or null) + `boolean match(PyPackage)`; **editable rule** default method :50-55: `isEditable() = !installOptions.isEmpty() && ("-e".equals(first) || "--editable".equals(first))`. Relation enum `packaging/requirement/PyRequirementRelation.java`: EXACTLY 8 constants `LT("<") LTE("<=") GT(">") GTE(">=") EQ("==") NE("!=") COMPATIBLE("~=") STR_EQ("===")`; spec interface `PyRequirementVersionSpec`: `getRelation()/getVersion()/matches(String)` + presentable = relation+version.
**Signature:** `requirement.match(List.of(this)) != null` is how a single package checks membership.
**Data Shape:** requirement = name + extras + ordered specs + install-option list; display text = name+extras+comma-joined specs.

### Decisive source
```java
// PyRequirement.java:48-55
default boolean isEditable() {
  if (getInstallOptions().isEmpty()) return false;
  String firstOption = getInstallOptions().get(0);
  return "-e".equals(firstOption) || "--editable".equals(firstOption);
}
// PyRequirement.java:38-44 — the >1-options ⇒ legacy-setup-options implication, stated verbatim
```

**Flow:** parse requirements.txt/setup metadata → requirement objects → `match()` folds specs against installed `PyPackage`s → first hit wins.
**Invariant:** editability is encoded in INSTALL OPTIONS positionally (first option only), not as a flag — a porter who scans all options for "-e" changes behavior on option order; STR_EQ (`===`) exists separately from EQ because PEP 440 arbitrary equality is string comparison.
**Probe:** from `pycharm/lib/src/pycharm-openapi-src` root:
`grep -cE '^\s+(LT|LTE|GT|GTE|EQ|NE|COMPATIBLE|STR_EQ)\(' com/jetbrains/python/packaging/requirement/PyRequirementRelation.java` → `8`;
`grep -n '"-e".equals' com/jetbrains/python/packaging/PyRequirement.java` → 1 hit;
`grep -n 'pep-0508\|pep-0440' com/jetbrains/python/packaging/PyRequirement.java` → 2 hits (:17/:18 javadoc hrefs; display form `PEP-508`/`PEP-440` occurs only INSIDE those link texts).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "PyRequirement isEditable getVersionSpecs PyRequirementRelation", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: spec/relation model + positional editable rule. Adapt: parser to your manifest formats. Omit: pip invocation details.
