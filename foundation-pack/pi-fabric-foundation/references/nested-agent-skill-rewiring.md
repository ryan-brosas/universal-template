<!-- capsule-v2 -->
# Nested skill rewiring — how does a fabric_exec sub-agent keep Pi's skill catalog, `<skill-dir>` expansion, and cross-skill references working inside a rewritten system prompt?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the contract for making Pi-native skills loadable when the nested agent has no direct `read` tool (only `pi.read` via fabric_exec)?

## Connected graph-selected seam
**Path/Symbol:** `src/core/skill-prompt.ts:restoreSkillsForFullCodePrompt` (:14-34); `src/core/skill-dir.ts:expandSkillDirMarkersInSkillBlock` (:12-27), `expandSkillDirMarkersForRead` (:41-52), `resolveReadPath` (:29-39); `src/core/skill-references.ts:buildSkillReferenceGuidance` (:20-55).
**Signature:** `restoreSkillsForFullCodePrompt(systemPrompt, skills)`; `expandSkillDirMarkers(content, skillDir)` replaces every literal `<skill-dir>`; `buildSkillReferenceGuidance(prompt, skills)` → guidance string | undefined.
**Data Shape:** marker token `<skill-dir>`; active-skill wrapper `<skill name="…" location="…">…</skill>` as the FIRST thing in the prompt; invocation verbs regex `/^\s*(?:[-*]\s*)?(?:(?:then|next|first|always|must|you must)\s+)?(?:run|invoke|load|start|follow|use)\b/i`; negations `/^\s*(?:[-*]\s*)?(?:do not|don't|never)\s+(?:run|invoke|load|start|follow|use)\b/i`.

### Decisive source
```ts
  if (systemPrompt.includes(SKILL_SECTION_HEADING)) {
    return systemPrompt.replace(          // ADAPT Pi's existing section…
      PI_SKILL_LOAD_INSTRUCTION,
      FABRIC_SKILL_LOAD_INSTRUCTION,      // …read tool → pi.read in fabric_exec
    );
  }

  const cwdIndex = systemPrompt.lastIndexOf(CWD_MARKER);
  if (cwdIndex < 0) return `${systemPrompt}${section}`;
  return `${systemPrompt.slice(0, cwdIndex)}${section}${systemPrompt.slice(cwdIndex)}`;
```

**Flow:** three cooperating rewrites. (1) PROMPT: if Pi's own skill section exists, only its load instruction is swapped (`Use the read tool…` → `` Use `pi.read` inside `fabric_exec`…``); otherwise the freshly formatted section is INSERTED before the trailing "Current working directory:" block (or appended). (2) MARKERS: `<skill-dir>` expands ONLY within the first `</skill>`-terminated block (parsed via `parseSkillBlock`, expanded to that block's `location` dirname) so user arguments after the block are preserved verbatim; for plain file reads it fires only when the resolved path's basename is exactly `SKILL.md` (after `@`-prefix strip + `~` expansion). (3) REFERENCES: when an expanded skill wrapper is present, lines inside the block matching an invocation verb AND naming another invocable skill (`/skill:` optional, word-boundary via lookahead) generate a mapping list `- /name -> "path"` with the instruction to resolve dependencies BEFORE task exploration and to continue the workflow afterward.
**Invariant:** never duplicate a skill section Pi already rendered — adapt it; user content outside the skill block is NEVER scanned or mutated; negated instructions ("do not run X") must not create references; `disableModelInvocation` skills are excluded from mappings; malformed wrappers (no closing tag / no body separator) yield NO guidance rather than a guess.
**Probe:** `tests/skill-prompt.test.ts:32` ("restores Pi's skill catalog before the working directory"), `:62` ("adapts an existing Pi skill section instead of duplicating it"); `tests/skill-dir.test.ts:24` ("expands only the Pi skill block and preserves user arguments"); `tests/skill-references.test.ts:78` ("ignores negated and non-invocation references").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "restoreSkillsForFullCodePrompt expandSkillDirMarkers buildSkillReferenceGuidance", limit: 5, fields: ["signature", "name", "file"] });
```
