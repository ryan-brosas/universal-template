<!-- capsule-v2 -->
# frontmatter-portability-gate — which YAML frontmatter shape stays portable across agent hosts?

**Source:** Humanizer MIT-declared `main@e2e92e7b4b8229253ed5c8e81dc65463fdeddda5`; Codebase Memory `humanizer`. **Question:** When one prompt corpus must load on Claude Code, skills.sh agents, and OpenAI-style agent hosts, which metadata fields may exist and how is the allowed set enforced?

## Anchored frontmatter extraction + banned-field scan
**Path/Symbol:** `scripts/validate-package.py` :25–32 (extraction via `yaml_metadata`, ban loop over `unsupported_field`); protected object: `SKILL.md:1–11` frontmatter (`name`, `description` with trigger prose, `license`, `metadata.version`).
**Signature:** extraction = `re.match(r"\A---\n(.*?)\n---\n", SKILL, re.DOTALL).group(1)` wrapped in require_match; ban = `re.search(rf"(?m)^{re.escape(field)}", yaml_metadata)` per field.
**Data Shape:** Input: whole SKILL.md text. Output: the inner frontmatter block as a string for later regex gates. Failure shapes: "SKILL.md must begin with YAML metadata" (no frontmatter) or "Remove unsupported YAML field: compatibility" / ": allowed-tools".

### Decisive source
```python
for unsupported_field in ("compatibility:", "allowed-tools:"):
    if re.search(rf"(?m)^{re.escape(unsupported_field)}", yaml_metadata):
        raise SystemExit(f"Remove unsupported YAML field: {unsupported_field[:-1]}")
```
(:30–32. The scan runs over ONLY the extracted block, line-anchored, so the words cannot trip the gate when they appear in body prose.)

**Flow:** anchor-at-start match (`\A`) with non-greedy DOTALL group captures exactly the first `---…---` block → ban scan rejects host-specific fields line-by-line inside that block → surviving metadata feeds the version gate (see three-way-version-parity-set).

**Invariant:** The frontmatter must be the very first bytes of the file; only host-neutral fields survive. `compatibility:` and `allowed-tools:` are Claude-specific skill fields — banning them keeps the same file loadable by any agent that reads plain Markdown skills. AGENTS.md states the design rule directly ("Keep the skill portable. Do not write instructions that limit it to one or two agent tools.") and the projection files prove the payoff: `agents/openai.yaml` carries only an interface card (display_name / short_description / default_prompt referencing `$humanizer`), and plugin.json points its loader at the root rather than copying the prompt.

**Probe:** Deterministic probes executed: direct read of :25–32 pins both regexes; direct read of SKILL.md :1–11 confirms the shipped frontmatter contains no banned fields and nests version under `metadata:`; validator GREEN run (exit 0) exercises this gate live on every run since it precedes all other gates. No mutation-based RED possible in a read-only checkout — recorded caveat.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "humanizer", name_pattern: "yaml_metadata", fields: ["lines"] })
```

## Verdict
Adopt: first-block anchored extraction, a literal allow-list posture enforced by banning known host-specific fields, and scanning only the extracted block so body text can't false-trip. Adapt the banned list to whichever hosts you target (e.g., ban `allowed-tools:` only if your other hosts lack the concept). Omit per-host frontmatter variants — the whole point here is ONE file, zero forks.
