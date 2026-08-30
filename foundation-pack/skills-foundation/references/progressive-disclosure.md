<!-- capsule-v2 -->
# Progressive Disclosure — what goes at each of a skill's three loading levels?

**Source:** anthropics/skills Apache-2.0 `main@3b3fad96`; Codebase Memory `skills`. **Question:** When authoring a skill, which content belongs in frontmatter, in the SKILL.md body, and in bundled resources — and what are the size budgets?

## Three-level loading system
**Path/Symbol:** `skills/skill-creator/SKILL.md` (Progressive Disclosure section; graph Section `skills.skills.skill-creator.SKILL.Progressive-Disclosure`, lines 86-87).
**Signature:** N/A (markdown contract).
**Data Shape:** Level 1 = metadata (name + description), ~100 words, always in context. Level 2 = SKILL.md body, loaded whenever the skill triggers, <500 lines ideal. Level 3 = bundled resources (`scripts/`, `references/`, `assets/`), loaded/executed as needed without limit.

### Decisive source
```markdown
#### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)

**Key patterns:**
- Keep SKILL.md under 500 lines; if you're approaching this limit, add an
  additional layer of hierarchy along with clear pointers about where the
  model using the skill should go next to follow up.
- Reference files clearly from SKILL.md with guidance on when to read them
- For large reference files (>300 lines), include a table of contents
```

**Flow:** Model always carries every skill's metadata → on trigger it loads that one body → while executing it reads only the referenced files needed for the current step → scripts run without ever entering context.
**Invariant:** All "when to use" information lives in the description (level 1), never in the body — a body-only trigger condition can never cause triggering because the body is not yet loaded.
**Probe:** `skills/skill-creator/SKILL.md` lines 86-96 pin the budgets; cross-check any real skill: `wc -l skills/*/SKILL.md` shows bodies from 32L (internal-comms) to 556L (claude-api; +3 lines from sdk-upgrade guide, drift re-verified 2026-08-24), all under/near 500 with heavy content pushed into references/.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "skills", "pattern": "Progressive", "limit": 10}'
# resolves `skills/skill-creator/SKILL.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the three-level budget and the "all trigger info in the description" rule verbatim — they are host-independent skill-format contracts. Adapt the exact numbers (~100 words / 500 lines / 300-line TOC threshold) to your loader's real token costs. Omit Anthropic-specific resource conventions you don't share. Caveat: prose source, no executable test exists for this contract.
