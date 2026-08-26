<!-- capsule-v2 -->
# Update-deps skill contract — which repo-owned rules keep an agent-driven dependency sweep from breaking releases?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** When a coding AGENT (not a human) bumps dependencies, which hard rules and release-owned lines must the workflow fence off so automation cannot corrupt versioning or golden data?

## Key facts
**Path/Symbol:** `.agents/skills/update-deps/SKILL.md` — Hard rules (:16-27); Do-NOT-edit release-owned trio (:48-58); Process baseline-first ladder (:60-99); known-flake note (:110-112); completion checklist (:125-137).
**Signature:** agent-facing SKILL.md with frontmatter `user-invocable: true`; invoked by name from the Copilot-agent issue (`agent-assigned-sweep-issue` capsule) or by a human asking for "dependency sweep".
**Data Shape:** two non-negotiable environment contracts: (1) ALL resolves/syncs go through the Microsoft feed proxy `https://packagefeedproxy.microsoft.io/pypi/simple` configured as root `[[tool.uv.index]]` — never public PyPI, no `--index`/`UV_INDEX_URL`/`PIP_INDEX_URL` overrides; (2) target versions must be ≥7 days old because the proxy does not serve younger releases.

### Decisive source
```markdown
# .agents/skills/update-deps/SKILL.md :50-58 — the three release-owned lines:
1. Cross-package pins `graphrag-cache==...`, ... rewritten automatically by
   scripts/update_workspace_dependency_versions.py from the semversioner
   version. Hand-editing them causes drift.
2. [project] version fields — managed by semversioner.
3. graspologic-native>=1.2,<1.3 — held below 1.3 on purpose; 1.3.x changes
   Leiden clustering output and breaks golden regression data.
```
```toml
# packages/graphrag/pyproject.toml :46-49 — the pin AND its in-source rationale:
# Hold on the 1.2.x line: graspologic-native 1.3.x changes Leiden clustering
"graspologic-native>=1.2,<1.3",
```

**Flow:** baseline green first (`uv run poe check` + `poe test_unit`) so failures are attributable → edit specifiers only in member `[project] dependencies` / root dev group → `uv lock [--upgrade]` + `uv sync --all-packages` → repair breakage via `references/migration-gotchas.md` patterns → record via `uv run semversioner add-change` → checklist re-verifies every rule including "no `graphrag-*==` pin edited while editing nearby specifiers".
**Invariant:** the skill fences THREE classes of lines: cross-package pins (script-owned), `version` fields (semversioner-owned), and behavior-bearing held pins (`graspologic-native<1.3` protects the golden-file regression suite — bumping it silently invalidates `test_values_match_golden_file`). A porter who treats all pyproject lines as fair game breaks both the release tooling and determinism tests that other capsules pin.
**Probe:** `grep -cF 'packagefeedproxy.microsoft.io' .agents/skills/update-deps/SKILL.md` = 2 (:18,:46); `grep -nF 'graspologic-native' .agents/skills/update-deps/SKILL.md` hits :56,:136; same needle in `packages/graphrag/pyproject.toml` hits :49 (pin) with the rationale comment at :46.

## Get live surrounding code
**Retrieve:** doc-shaped node — search_code resolves the Module node line-exact:
```
codebase-memory-mcp cli search_code '{"project":"graphrag","pattern":"graspologic-native","file-pattern":"*.md"}'
```
rank#1 = `.agents/skills/update-deps/SKILL.md` :1-137.

## Verdict
Adopt the release-owned-line fencing pattern (script-generated pins, semversioner version fields, behavior-bearing held pins with in-source rationale) for any agent-driven dependency automation; adapt proxy URL, package names, and poe task names to host; omit Microsoft-internal feed specifics when porting outside MS infra. Coverage: `no_recorded_issue`; direct-test surface is indirect — the golden regression suite this pin protects is pinned by the cluster-graph-determinism capsule.
