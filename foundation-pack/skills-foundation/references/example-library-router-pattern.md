<!-- capsule-v2 -->
# Example-library router skill — how do you serve many output formats from one tiny skill body without blowing the context budget?

**Source:** anthropics/skills Apache-2.0 `main@3b3fad96af16`; Codebase Memory `skills`. **Question:** What shape lets a single skill cover N document formats while loading only the one format in use?

## Routing-table body + per-format guideline files + Keywords line
**Path/Symbol:** `skills/internal-comms/SKILL.md` (:1–32; whole file is the seam).
**Signature:** n/a (skill-shape pattern).
**Data Shape:** frontmatter = name + pushy description enumerating every covered format (status reports, leadership updates, 3P updates, newsletters, FAQs, incident reports…); body = 3-step dispatch (identify type → load exactly one `examples/<format>.md` → follow it); four guideline files with `general-comms.md` as catch-all; trailing `Keywords:` section listing trigger vocabulary.

### Decisive source
```markdown
1. **Identify the communication type** from the request
2. **Load the appropriate guideline file** from the `examples/` directory:
    - `examples/3p-updates.md` - For Progress/Plans/Problems team updates
    - `examples/company-newsletter.md` - For company-wide newsletters
    - `examples/faq-answers.md` - For answering frequently asked questions
    - `examples/general-comms.md` - For anything else that doesn't explicitly match

## Keywords
3P updates, company newsletter, company comms, weekly update, faqs, common questions, updates, internal comms
```
Plus the unmatched-type rule: "If the communication type doesn't match any existing guideline, ask for clarification or more context about the desired format."

**Flow:** request arrives → description triggers the skill (its format list doubles as the trigger contract) → model matches type against the routing table → loads ONE guideline file into context → follows its formatting/tone/gathering instructions; no-match asks instead of guessing.
**Invariant:** The body stays a dispatch table (~32 lines here) — never inline the formats themselves; progressive disclosure does the scaling. The catch-all file absorbs near-misses so unmatched input degrades to a clarifying question, not a hallucinated format. Keywords live in the BODY (description is capped at 1024 chars and must stay readable).
**Probe:** repo-root deterministic probes: `grep -c '^    - \`examples/' skills/internal-comms/SKILL.md` = 4 (four routed files); `wc -l skills/internal-comms/SKILL.md` = 32 (body budget held).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", file_pattern: "*internal-comms*", limit: 10 });
```
Live result 2026-08-26: Folder + SKILL Module :1–405? — graph shows `internal-comms` Folder plus examples files (`3p-updates.md`, `company-newsletter.md`, `faq-answers.md`, `general-comms.md`) as File nodes; BM25 misses markdown-only skills (known caveat), so the direct read above is decisive.

## Verdict
Adopt for any multi-format authoring skill (comms, report templates, email families): routing-table body, one-file-per-format resources, catch-all fallback, body-level keyword block. Adapt the guideline-file contents to your house styles. Omit the specific comms content. Caveat: markdown-only skill — graph coverage is Section-level only (coverage checked: `no_recorded_issue`); claims rest on the full direct read at pin main@3b3fad96af16.
