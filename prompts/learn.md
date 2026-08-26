---
description: Extract new knowledge and lessons into a permanent skill or capability
argument-hint: "<what was learned or what needs capturing>"
---

# Learn: $ARGUMENTS

Extract the lessons, edge cases, and platform quirks discovered during this session (or from the user's arguments) into a new or updated permanent skill in `~/.agents/skills/`.

## Load Skills

Load `~/.agents/skills/writing-skills/SKILL.md` (the uniform SKILL.md grammar)
and `~/.agents/templates/skill.md` (the mandated skeleton) to craft
high-quality skills.

## Process

### Phase 1: Context Gathering
- Identify the core problem that was solved, the edge case encountered, or the platform quirk discovered.
- Identify what caused the original failure or friction.
- Identify the exact code pattern, command, or technique that successfully solved it.

### Phase 2: Distillation (The Arbitrage)
- Strip away project-specific details. Generalize the solution into a repeatable pattern.
- Identify the exact symptoms or triggers that should cause an agent to use this skill in the future.
- If this is a mechanical rule (e.g. "never use X, always use Y"), consider if it can be implemented as a programmatic linter or CI check instead of a prompted skill (Steer Outcomes, Not Behavior). If it can, write a Python verification script instead.

### Phase 3: Skill Drafting
- Determine if this knowledge belongs in an existing skill (e.g. `pack-quality`, `pack-foundations`) or requires a new dedicated skill.
- If creating a new skill, create a directory `~/.agents/skills/<kebab-case-name>/` and author a `SKILL.md` from `~/.agents/templates/skill.md` using the standard YAML frontmatter (`name`, `description`). New leaf skills get `disable-model-invocation: true`; only pack routers and workflow skills stay model-visible.
- Document the problem, the context, the generalized solution, and provide clear code examples of the "Wrong Way" vs the "Right Way".
- Add the new skill by validating its frontmatter/`name`/`description` against the writing-skills grammar; discovery is automatic from `~/.agents/skills` (no `manifest.json` / `packs.json` to edit in the global tree).

### Phase 4: Tripled-Layer OpenViking Sync
- If the OpenViking MCP server or CLI is available, execute `ov reindex viking://resources/pi-skills` to ensure the new skill is immediately embedded and searchable in the 1024/2048-dimensional semantic space.

## Schema boundary

Before creating or editing any skill file, run the Schema loop inside one `fabric_exec`: `schema.hypothesize` → `schema.verify` → `schema.commit` with declared operations. Only `committed` authorizes the edit.

## Output

Report:
1. The extracted lesson or pattern.
2. The path to the new or updated `SKILL.md` file.
3. Confirmation that the skill validates (frontmatter `name` + `description` ≤ 1024, grammar via writing-skills) and is discoverable from `~/.agents/skills/`.
4. Confirmation of OpenViking reindexing, if applicable.
