<!-- capsule-v2 -->
# three-way-version-parity-set — how do three files agree on one version with a missing-key trap?

**Source:** Humanizer MIT-declared `main@e2e92e7b4b8229253ed5c8e81dc65463fdeddda5`; Codebase Memory `humanizer`. **Question:** What is the smallest correct check that SKILL.md, README.md, and a plugin manifest all declare the same release version?

## Set-of-three version agreement
**Path/Symbol:** `scripts/validate-package.py` :34–47 (`skill_version`, `readme_version`, `package_versions`).
**Signature:** no function — three module-level extractions folded into `set` comparison.
**Data Shape:** skill_version: first indented `version: "x.y.z"` (quoted or bare) inside the extracted frontmatter block. readme_version: FIRST line matching `- **X.Y.Z**` in README (the newest entry of a newest-first history list). plugin version: `PLUGIN.get("version", "")`. Comparison: `len({skill_version, readme_version, str(PLUGIN["version"-default])}) != 1` → SystemExit.

### Decisive source
```python
package_versions = {skill_version, readme_version, str(PLUGIN.get("version", ""))}
if len(package_versions) != 1:
    raise SystemExit(
        f"Use one package version in all files: {sorted(package_versions)}"
    )
```
(:43–47. The set-length form needs no pairwise diffs, and the failure message prints the sorted offending values so the fix is obvious.)

**Flow:** extract skill version from metadata block only (`(?m)^\s+version:\s*["\']([^"\']+)["\']\s*$` — the required indentation matches `metadata:` nesting and would REJECT a top-level `version:` field, which AGENTS.md :24 also forbids by name) → extract README's first bold semver entry (:39 regex takes line 1 of the history; newest-first ordering makes "first" mean "current") → fold with plugin.json's version into a set → demand exactly one element.

**Invariant:** All three declarations must be byte-equal at publish time. The `str(...)` coercion is load-bearing: if plugin.json lacks `version`, its contribution is `""`, the set has ≥2 elements, and the check fails loudly ("missing key passes silently" is impossible). The error message sorts the set for deterministic output.

**Probe:** Deterministic probes executed: direct reads pin SKILL.md :10 `version: "2.11.2"`, README :157 first history entry `- **2.11.2** - Removed the plugin symlink…`, plugin.json :5 `"version": "2.11.2"` — three-way equality at the pin; validator GREEN run exercised this exact gate live (exit 0). Mutation RED blocked by read-only checkout — recorded caveat.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "humanizer", qn_pattern: "skill_version|readme_version|package_versions" })
```

## Verdict
Adopt the set-size-one formulation plus get-with-""-coercion for any N-file version agreement — it is shorter and louder than pairwise comparison. Adopt "first entry of a newest-first changelog = current version" only together with a validator that enforces it. Adapt the extraction regexes to your changelog/frontmatter dialect; keep the sorted-values failure message.
