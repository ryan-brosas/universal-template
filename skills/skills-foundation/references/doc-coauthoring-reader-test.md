<!-- capsule-v2 -->
# Doc co-authoring reader test — how do you verify a document works for readers without context bleed?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What is the three-stage co-authoring workflow's exit conditions, and how does Stage 3 use a fresh context-free agent as a reader proxy?

## Three-stage guided workflow (`skills/doc-coauthoring/SKILL.md`, whole file)
**Path/Symbol:** `skills/doc-coauthoring/SKILL.md` — Stage 1 Context Gathering (:28–102), Stage 2 Refinement & Structure (:104–240), Stage 3 Reader Testing (:242–331).
**Signature:** behavioral contract (no code): offer → accept/decline gate → per-section loop {clarify → brainstorm 5–20 options → curate keep/remove/combine → gap check → draft via str_replace → iterate} → reader test.
**Data Shape:** section scaffold created FIRST with placeholder text ("[To be written]"); artifact if available, else a working-directory markdown file; edits are always surgical replacements, never full reprints.

### Decisive source
```markdown
# :261-275 — Stage 2 sub-agent variant: zero context bleed
For each question, invoke a sub-agent with just the document content
and the question.
Summarize what Reader Claude got right/wrong for each question.
...
Invoke sub-agent to check for ambiguity, false assumptions, contradictions.
# :96-97 — Stage 1 exit condition
Sufficient context has been gathered when questions show understanding -
when edge cases and trade-offs can be asked about without needing basics explained.
```

**Flow:** offer the workflow, work freeform on decline → **Stage 1**: meta-questions (type/audience/impact/template/constraints), then invite an unstructured info dump, then 5–10 numbered clarifying questions answerable in shorthand; exit when edge-case questions no longer need basics explained → **Stage 2**: agree sections (start with the most unknowns; summaries LAST), scaffold all placeholders, then per section run the six-step loop; freeform feedback like "looks good" is parsed into keep/remove/combine decisions; after 3 no-change iterations ask what can be cut; at ~80% done re-read the whole doc for flow/redundancy/slop → **Stage 3**: predict 5–10 realistic reader questions, then EITHER spawn fresh sub-agents given ONLY doc+question (agent environments) OR hand the user a manual protocol for a clean conversation (web environments); also probe ambiguity / assumed knowledge / internal contradictions; failures loop back into refinement of the offending sections. Exit: Reader Claude answers consistently correctly with no new gaps. Final review returns ownership: the USER does the last read-through and fact-check.
**Invariant:** The reader agent must have NO conversation context — the entire value is measuring what the DOCUMENT alone conveys; user feedback during Stage 2 is treated as preference training data for later sections (justifications like "Remove 3 (duplicates 1)" teach priorities); the guide never reprints the whole document — every edit is a targeted replacement.
**Probe:** Content-only skill, no upstream tests. Deterministic anchors (executed this pass):
`grep -c 'invoke a sub-agent with just the document content' skills/doc-coauthoring/SKILL.md` = 1;
`grep -c 'without needing basics explained' skills/doc-coauthoring/SKILL.md` = 1;
`grep -c 'Use .str_replace. to make edits (never reprint the whole doc)' skills/doc-coauthoring/SKILL.md` = 1.

## Get live surrounding code
**Retrieve:** (BM25 graph search misses markdown-only skills here — content search resolves it)
```ts
await mcp.codebase_memory.search_code({ project: "skills", pattern: "invoke a sub-agent with just the document content", file_pattern: "*.md", limit: 5 });
```
→ hits `skills.skills.doc-coauthoring.SKILL` :265 (observed live this pass; a `search_graph` query "doc co-authoring reader testing stage" returns only webapp-testing noise — recorded as the adversarial-miss example).

## Verdict
Adopt: fresh-context reader proxy as a universal acceptance test for authored artifacts; staged gates with explicit exit conditions; numbered-option curation as the feedback grammar; scaffold-first + surgical-edits discipline. Adapt: "sub-agent"/"artifact" to your host's equivalents (any isolated-context worker and any shared file surface); shorthand-answer conventions to your users. Omit: Claude.ai connector/settings mentions and claude.ai manual-test URLs. This is a behavior contract like discernment-nudge-contract, not code tooling.
