<!-- capsule-v2 -->
# Declared-skill quiet skip — which skill-file problems surface as diagnostics and which are silently ignored?

**Source:** pi-upstream MIT `main@a470b121bf683b4c2b9fc0b3a7c807de7e0cfe9c` (drift-window change to harness/skills.ts). Codebase Memory `pi-upstream`. **Question:** A porter loads a directory tree of markdown skills and warns on every parse failure — why does that flood logs on non-skill root files, and what is the declared-vs-incumbent distinction?

## loadSkillFromFile: only SKILL.md files are "declared"; loose .md needs frontmatter AND description
**Path/Symbol:** `packages/agent/src/harness/skills.ts:250-255` (`isDeclaredSkill` derivation), `:263-271` (conditional parse diagnostic + description requirement).
**Signature:** `isDeclaredSkill = filePath.replace(/[\\/]+$/, "").split(/[\\/]/).pop() === "SKILL.md"`; `loadSkills(env, ...)` traverses recursively, treating direct root `.md` files as candidate skills.
**Data Shape:** `SkillDiagnostic {type:"warning", code:"read_failed"|"parse_failed"|"invalid_metadata", message, path}`; `SkillFrontmatter` requires string `description` for load.

### Decisive source
```ts
const parsed = parseFrontmatter<SkillFrontmatter>(rawContent.value);
if (!parsed.ok) {
    if (isDeclaredSkill) {
        diagnostics.push({ type: "warning", code: "parse_failed", message: parsed.error.message, path: filePath });
    }
    return { skill: null, diagnostics };
}

const { frontmatter, body } = parsed.value;
const description = typeof frontmatter.description === "string" ? frontmatter.description : undefined;
if (!isDeclaredSkill && (!description || description.trim() === "")) {
    return { skill: null, diagnostics };
}
```

**Flow:** read file (read failures ALWAYS warn — even undeclared files) → parse frontmatter: failure warns ONLY when the file is named `SKILL.md` (an explicit declaration of intent); loose `.md` files failing parse are skipped silently → valid frontmatter but empty/missing description: `SKILL.md` still loads with undefined description (host decides), loose `.md` is quietly rejected → remaining metadata validation warns regardless of declared status.
**Invariant:** Diagnostic noise scales with declaration, not presence: a README.md with broken frontmatter in the skills root must not produce warnings, but a file explicitly named SKILL.md that fails to parse always does — because the filename itself is the declaration of intent. Loose files additionally need a non-empty description to be usable at all.
**Probe:** Deterministic source probes from repo root at this pin: `grep -n "isDeclaredSkill" packages/agent/src/harness/skills.ts` (≥3 hits) and `grep -n "if (isDeclaredSkill)" packages/agent/src/harness/skills.ts` (1 hit at :265). Coverage caveat: no dedicated upstream unit test located for the quiet-skip branch at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "loadSkills SKILL.md frontmatter diagnostics", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt declaration-driven diagnostics: warn unconditionally on read failures and on declared (`SKILL.md`) parse failures, stay silent for undeclared loose-markdown parse failures, and require descriptions only from undeclared files. Adapt the declaring-filename convention to your host's loader. Omit if your skill directory contains only curated SKILL.md files. Coverage caveat: pinned by source citation + live greps.
