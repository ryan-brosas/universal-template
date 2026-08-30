<!-- capsule-v2 -->
# Skill metadata quality gate — which structural checks catch bad skill metadata without drowning maintainers in false alarms?

**Source:** pi-template MIT `foundations-sync@37e9bc1736b7`; Codebase Memory `pi-template`. **Question:** How do you split catalog-quality violations into hard errors versus warnings, and detect near-duplicate descriptions cheaply?

## Errors vs warnings over the whole SKILL.md tree
**Path/Symbol:** `scripts/quality-gate.py` (module-level gate; description collection lines ~33–45; orphan warning line 57; prefix-similarity lines 66–78; essentials block lines 81+).
**Signature:** module scan of every dir under `.pi/skills` containing `SKILL.md`; regex frontmatter extraction `^name:` / `^description:` (MULTILINE), falling back to dir basename.
**Data Shape:** builds `skills[name] = {path, desc, dir}`; appends to `errors[]` (exit 1) or `warnings[]` (printed, exit stays 0).

### Decisive source
```python
# 4. Near-duplicate descriptions (prefix overlap > 60%)
descs = [(n, i["desc"].lower()) for n, i in skills.items() if i["desc"]]
for i in range(len(descs)):
    for j in range(i+1, len(descs)):
        n1, d1 = descs[i]; n2, d2 = descs[j]
        if not d1 or not d2: continue
        shorter = min(len(d1), len(d2))
        if shorter < 20: continue
        common = 0
        for k in range(min(shorter, 60)):
            if d1[k] == d2[k]: common += 1
            else: break
        if common > 0.6 * shorter:
            warnings.append(f"near-duplicate descriptions: {n1} ~ {n2} (prefix {common} chars)")
```

**Flow:** JSON validity → collect all skills, error on duplicate name OR duplicate description string → for each leaf with a `references/` dir, warn when a `.md` file is never mentioned by its own leaf text (orphaned reference) → pairwise lowercase-description prefix overlap >60% of the shorter (min length 20, compare window 60) warns near-duplicates → essentials docs must exist AND each be indexed inside `essentials/README.md` (error otherwise) → exit 1 only on errors; warnings print as `(warn)`.
**Invariant:** the error/warning split IS the design: identity collisions (duplicate names/descriptions) and broken index structure fail the gate; stylistic drift (orphans, near-dupes) surfaces without blocking — because pre-existing leaves may link references by other means.

**Probe:** `python3 scripts/quality-gate.py` executed live at the pin → exit 0 with real warnings observed: `QUALITY GATE OK: ... no failures` plus `(warn) orphaned reference: crewai-foundation/references/*.md not in leaf` (a sibling lane's work-in-progress leaf — warnings correctly did NOT fail the gate). CI wiring via `.github/workflows/check.yml`.

## Get live surrounding code
**Retrieve:** (executed at the pin)
```ts
await mcp.codebase_memory.search_graph({ project: "pi-template", query: "duplicate skill names near-duplicate descriptions quality gate", limit: 5 });
// -> BM25 surfaced tests/harness cassette helpers only: quality-gate.py checks are MODULE-LEVEL code with no Function graph nodes; discovery went file-query + direct read (honest retrieval caveat).
```

## Verdict
Adopt the errors-vs-warnings taxonomy keyed to "would this corrupt routing?" and the O(n²)-but-windowed prefix-overlap near-duplicate detector as the cheap semantic-ish screen. Adapt thresholds (0.6 / 20 chars / 60-char window) to your catalog's description style; use token-based similarity if prefixes diverge early. Omit the fixed essentials list — that is this repo's philosophy-doc inventory, not a mechanism.
