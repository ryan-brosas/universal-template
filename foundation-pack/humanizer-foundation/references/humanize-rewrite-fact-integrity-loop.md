<!-- capsule-v2 -->
# humanize-rewrite-fact-integrity-loop — how does the rewrite change prose without drifting a single fact?

**Source:** Humanizer MIT-declared `main@e2e92e7b4b8229253ed5c8e81dc65463fdeddda5`; Codebase Memory `humanizer`. **Question:** When porting an LLM text-rewrite procedure, how does it guarantee every output claim is traceable to the input while still restructuring freely?

## Rewrite process + return-mode contract
**Path/Symbol:** `SKILL.md` — `## What to do` (:19–28), `## Match the writer's voice` (:30–38), `## How to return the result` (:432–438), `## Rewrite process` (:440–450). Procedure, not a callable: the "signature" is *text-in → mode-keyed output*.
**Data Shape:** Input is one of three kinds — pasted text (default), a named file path, or an embedded call from another task. Output shape follows the input kind; the same rewrite process runs in every mode.

### Decisive source
```markdown
3. Ask two questions:
   - **"What still sounds AI-generated?"**
   - **"Did the rewrite add or remove any fact, name, number, date, quote,
     citation, ranking, or other claim?"**
   Treat any unsupported addition or lost claim as an error.
```
(SKILL.md :444–447 — the audit gate is quoted verbatim in the prompt so the executor asks itself both questions every run.)

**Flow:** (1) read source and mark each AI pattern against the 35-pattern list → (2) write a draft and read it aloud for rhythm, simple verbs (*is*, *has*), formality → (3) run the two-question audit; any unsupported addition or lost claim = error, not a style note → (4) write the final version at paragraph granularity ("state each point naturally instead of patching one flagged phrase at a time"), then sweep dashes per §14 → return per mode: pasted ⇒ draft + remaining-pattern list + final; file ⇒ ONLY final text into the file with code blocks, YAML metadata, data, and link targets untouched, plus a short summary to the user; embedded ⇒ final text only.

**Invariant:** Every factual claim in the output must come from the source or the user. Inventing a fact, name, number, date, quote, or citation is forbidden even when it would smooth the prose; if a sentence needs a missing detail, ask or use a simpler sentence. Fiction is explicitly exempt (invented details are the task there). A user-provided writing sample takes priority over all style rules, including keeping em dashes at the sample's rate ("Do not apply §14 as a ban").

**Probe:** No executable test exists for prompt behavior — recorded caveat, not worked around. Deterministic probes executed this pass: direct read of SKILL.md :444–447 pins the two questions byte-for-byte; repo-owned command `python3 scripts/validate-package.py` exited 0 printing `Humanizer package v2.11.2 is valid`, which pins that the corpus carrying this loop is intact (frontmatter present, ≤500 lines, §1–35 ordered).

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "humanizer", qn_pattern: "Rewrite-process|What-to-do|How-to-return-the-result" })
```

## Verdict
Adopt the two-question audit as a mandatory post-draft gate and the mode-keyed output contract (file mode writes final text only and never touches code/frontmatter/data/link targets) verbatim. Adapt step wording, category names, and the dash-sweep rule to your own corpus; keep the "paragraph-level rewrite beats phrase patching" instruction — it is what prevents whack-a-mole style edits. Omit the specific 35-pattern references if your detector uses different tells; the audit-gate structure is the portable part.
