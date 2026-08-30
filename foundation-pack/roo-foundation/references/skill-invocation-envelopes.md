<!-- capsule-v2 -->
# skillInvocation envelopes — how does a skill invocation get approved and what exactly enters the conversation?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What is the wire shape of a skill approval prompt and its tool-result payload?

## Three pure helpers: lookup, approval JSON, result text
**Path/Symbol:** `src/services/skills/skillInvocation.ts` (whole file, lines 1–54): `resolveSkillContentForMode` :7, `buildSkillApprovalMessage` :21, `buildSkillResult` :35.
**Signature:** `resolveSkillContentForMode(skillsManager: SkillLookup | undefined, skillName: string, currentMode: string): Promise<SkillContent | null>`; `buildSkillApprovalMessage(skillName, args, skillContent): string`; `buildSkillResult(skillName, args, skillContent): string`.
**Data Shape:** `SkillLookup` is a one-method interface (`getSkillContent(name, currentMode?)`) so callers depend on the capability, not the manager class; approval payload = JSON `{tool:"skill", skill, args, source, description}`; result is plain text with fixed section headers.

### Decisive source
```ts
result += `\nSource: ${skillContent.source}`
result += `\n\n--- Skill Instructions ---\n\n${skillContent.instructions}`
```

**Flow:** undefined manager or unknown name → null (caller renders its own error); found → read SKILL.md body (frontmatter stripped at load) → approval message carries name/args/source/description for the ask dialog → after approval the RESULT text embeds full instructions under the literal `--- Skill Instructions ---` banner with Source line BEFORE it.
**Invariant:** instructions are injected as TOOL-RESULT TEXT, not a system prompt — the model reads them once per invocation; ordering of Description / Provided arguments / Source / Instructions sections is fixed and consumers parse nothing (display-only), but the banner string itself appears in transcripts. Mode filtering happens INSIDE getSkillContent via getSkillsForMode, so a mode-restricted skill resolves to null in other modes rather than falling back to the generic twin.
**Probe:** `grep -c 'getSkillContent' src/services/skills/skillInvocation.ts` → 2; `grep -cF -- '--- Skill Instructions ---' src/services/skills/skillInvocation.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "buildSkillResult resolveSkillContentForMode SkillLookup", limit: 10 });
```

## Verdict
Adopt the three-helper decomposition and the null-not-throw lookup contract; keep instructions-as-tool-result (not system injection) unless your host has a native skills channel. Adapt banner wording. Direct test: `src/services/skills/__tests__/skillInvocation.spec.ts`.
