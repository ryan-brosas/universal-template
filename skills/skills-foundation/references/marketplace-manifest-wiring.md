<!-- capsule-v2 -->
# Marketplace Manifest — plugin wiring + skill-name reserved-word and description-length constraints

**Source:** anthropics/skills (Apache-2.0 example) `main@3b3fad9`; Codebase Memory `skills`. **Question:** How is a set of skills wired into a distributable plugin marketplace, and which name/description constraints gate upload as a custom skill?

## Plugin-grouping manifest with a reserved-word name ban and a 1024-char description cap
**Path/Symbol:** `.claude-plugin/marketplace.json` (read whole) + `skills/academy-guide/SKILL.md` frontmatter (the rename commit `0a64e39`).
**Signature:** JSON manifest: top-level `{name, owner:{name,email}, metadata:{description,version}, plugins:[{name, description, source, strict, skills:["./skills/<x>", ...]}]}`.
**Data Shape:** each `plugins[]` entry groups one or more skills under a plugin name; `skills[]` paths are relative (`./skills/xlsx`, `./skills/claude-api`, …). `strict: false` on all entries. Skill names in the manifest AND the SKILL.md frontmatter `name:` must NOT contain the reserved words `claude` or `anthropic` (agent-skills best-practices) — so `claude-academy-guide` was renamed to `academy-guide`; the frontmatter description must be ≤1024 characters (skill-upload validation limit).

### Decisive source
```json
{
  "name": "academy-guide",
  "description": "Recommends relevant Claude Academy courses, tutorials, and use cases when users ask how to use Claude",
  "source": "./",
  "strict": false,
  "skills": ["./skills/academy-guide"]
}
```
```text
# commit 0a64e39 (rename)
- Rename: the skill folder, the SKILL.md frontmatter name, and the
  marketplace.json entry name and path. Skill names cannot contain the
  reserved words "claude" or "anthropic" (per the agent skills
  best-practices documentation).
- Description: shortened from 1,176 to 992 characters to fit the
  1,024-character limit that skill upload validation applies to the
  SKILL.md frontmatter description.
```

**Flow:** a skill folder + SKILL.md + LICENSE.txt becomes distributable → wire it into the marketplace by adding a `plugins[]` entry (or extending an existing one) with `name`, `description`, `source: "./"`, `skills: ["./skills/<name>"]` → ensure the SKILL.md `name:` matches the folder and the manifest path, contains no reserved word, and the description fits the 1024-char cap.
**Invariant:** name/path consistency across three places (folder, SKILL.md frontmatter `name:`, marketplace.json `skills[]` path) is load-bearing — a mismatch breaks the plugin's skill resolution. The reserved-word ban (`claude`/`anthropic`) is a hard upload constraint, not a style preference. The description cap is enforced by upload validation, so a description that reads well but exceeds 1024 chars silently fails packaging.
**Probe:** No upstream test runner. Deterministic (re-derived & executed 2026-08-24): `grep -c '"name": "academy-guide"' .claude-plugin/marketplace.json` = 1; `grep -c '"name": "discernment-nudge"' .claude-plugin/marketplace.json` = 1; the plugin's skills array is MULTI-LINE (`"skills": [` newline `"./skills/academy-guide"`), so single-line grep for the collapsed form returns 0 — use `grep -c '"\./skills/academy-guide"' .claude-plugin/marketplace.json` = 1; `git show 0a64e39 --stat` lists the rename.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "marketplace.json plugins skills academy-guide reserved word", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the plugin-grouping manifest shape + name/path consistency + reserved-word ban + description-length-cap contract for any skill-packaging marketplace. Adapt the plugin grouping and source paths to your layout. Omit the Anthropic-specific owner/metadata. Coverage caveat: no executable test — contract pinned by source grep + commit evidence + graph metadata_match only.
