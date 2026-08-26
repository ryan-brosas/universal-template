<!-- capsule-v2 -->
# Skill progressive disclosure — how are skills indexed into the prompt without loading bodies?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** How does the system prompt stay small while still making N playbooks reachable, and how is frontmatter parsed without a YAML dependency?

## AgentInstructions.skillsSection + SkillFrontmatter.parse
**Path/Symbol:** `Sources/PalmierPro/Agent/Tools/AgentInstructions.swift:skillsSection` (224–233); `Sources/PalmierPro/Agent/Skills/Skill.swift:SkillFrontmatter.parse` (30–53), `requiredFields` (55–61); `SkillStore.performSkillSync` (`Sources/PalmierPro/Agent/Skills/SkillStore.swift:195–206`).
**Signature:** `static func skillsSection(_ index: String) -> String`; `static func parse(_ text: String) -> (fields: [String: String], body: String)`.
**Data Shape:** skill file = `---` frontmatter (name, description required; source optional) + markdown body; prompt carries only a generated index string; bodies load via the `read_skill(id)` tool.

### Decisive source
```swift
static func skillsSection(_ index: String) -> String {
    guard !index.isEmpty else { return "" }
    return """
        # Skills
        Playbooks for specific tasks. Before a task that matches one, call read_skill(id) \
        to load its full procedure, then follow it.
        \(index)
        """
}
```
Dependency-free frontmatter scan (first line must be `---`, stops at closing `---`, strips paired double quotes, ignores keyless lines):
```swift
guard lines.first?.trimmingCharacters(in: .whitespaces) == "---" else { return (fields, text) }
while i < lines.count, lines[i].trimmingCharacters(in: .whitespaces) != "---" {
    if let colon = line.firstIndex(of: ":") { ... fields[key] = value }
    i += 1
}
```

**Flow:** run-loop entry awaits `SkillStore.shared.waitForSkillSync()` → `reloadSkills()` → sync ladder: reload local → refresh remote catalog → auto-install eligible entries (each step checks `Task.isCancelled`) → `AgentInstructions.skillsSection(SkillStore.shared.skillIndex)` concatenated after server instructions each turn → model calls `read_skill` to pull a body on demand.
**Invariant:** empty index ⇒ no Skills section at all (no dangling heading); a body-less or missing-name/description skill never enters the catalog; cancellation can abort the sync between any install.
**Probe:** `Tests/PalmierProTests/Agent/SkillFrontmatterTests.swift:7-15` (`requiresNonemptyNameAndDescription`: empty description rejected), `:17-38` (`replacingOnlyNameKeepsTheDraftInstructions`, `replacingFieldsPreservesUnchangedFrontmatter`: field replacement preserves untouched frontmatter and body), `:40-43` (`suggestedSkillIDIsStableAndFilesystemSafe`: `"  Interview Cleanup & Pacing  "` → `interview-cleanup-pacing`, all-punctuation → `new-skill`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "skillsSection SkillFrontmatter performSkillSync", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt index-only injection with a `read_skill`-style loader tool and the strict "empty index ⇒ omit section" rule; adopt the quote-stripping line scanner when you cannot afford a YAML parser and your frontmatter stays flat key: value. Adapt the sync/auto-install policy (PalmierPro's ledger + community-catalog gating is its own seam — next-pass target). Omit PalmierPro's specific skill directory layout. Coverage: AgentInstructions.swift, Skill.swift, SkillStore.swift all `no_recorded_issue` @ gen 2026-08-25T19:59:55Z; SkillFrontmatterTests read directly.
