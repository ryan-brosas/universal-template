<!-- capsule-v2 -->
# llm-first orchestration contract — how does a 88-script evidence layer stay subordinate to LLM reasoning?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** What is the mandated pipeline order and failure doctrine that keeps scripts as evidence, not verdicts?

## SKILL.md routing + bounded-retry doctrine
**Path/Symbol:** `SKILL.md` (369L: Deterministic Trigger Mapping :16-25, Orchestration Steps 1-8 :50-256, Critical Rules :336-351); enforcement via `scripts/validate_skill_inventory.py`.
**Signature:** n/a — prose contract enforced by CI validators.
**Data Shape:** mandatory deliverables `FULL-AUDIT-REPORT.md` + `ACTION-PLAN.md` created at audit START; severity vocabulary {🔴 Critical, ⚠️ Warning, ✅ Pass, ℹ️ Info}; confidence labels {confirmed, likely (Hypothesis)}.

### Decisive source
```text
9. **LLM-first, resilient pipeline** — Start by reading the page with `read_url_content`,
   then always run relevant scripts for structured evidence. Scripts are the **preferred**
   evidence source — use them actively. However, if any script fails ..., the LLM MUST
   still produce a complete analysis using its own reasoning (confidence: `Likely`).
   Never block a report on a single script failure.
```

**Flow:** deterministic trigger mapping (generic "perform seo analysis on <url>" ⇒ single-page full audit with the two file artifacts) → Step 2 evidence: built-in read tool FIRST, scripts for structured verification → Steps 4/6.5: run baseline scripts then `finding_verifier.py --findings-json` BEFORE final tables → Step 7 scoring: narrative weights (Technical 25 / Content 20 / On-Page 15 / Schema 15 / CWV 10 / Images 10 / GEO 5) live in EXACTLY two sanctioned locations (SKILL.md + seo-audit.md) while generate_report uses its own 14-cat script weights — dual-rubric by design → environment failures become "Environment Limitations" sections with confidence downgraded, retry each source AT MOST ONCE, no web-search pivot loops.
**Invariant:** The dated-fact rules are hard gates: INP not FID (FID removed 2024-09-09), FAQPage restricted to gov/health (2023-08), HowTo deprecated never recommend, JSON-LD only (no Microdata/RDFa), E-E-A-T all queries post-Dec-2025. `validate_skill_inventory.py` fails CI when README/SKILL counts drift from disk (16 sub-skills, 10 agents, 89 scripts) — porters adding scripts must update the counters or CI breaks.
**Probe:** `grep -cF 'Never block a report on a single script failure' SKILL.md` (= 1); `grep -c 'INP not FID' SKILL.md` (= 1); `python3 scripts/validate_skill_inventory.py` exits 0 at pin; `grep -cF 'FULL-AUDIT-REPORT.md' SKILL.md` (≥ 3).
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"orchestration trigger audit report","limit":5}'` resolves SKILL.md sections.

## Verdict
Adopt evidence-subordinate-to-reasoning pipeline order, bounded retries, artifact-first deliverables, and CI-enforced inventory counts for ANY agent skill pack; adapt the SEO-specific fact gates to your domain's dated truths; omit IDE-format installer matrix if single-host. Probes executed green @69199160 (inventory validator run exit 0).
