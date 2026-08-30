<!-- capsule-v2 -->
# finding-verifier dedupe gate — how do raw multi-source findings become a trustworthy report?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** What is the canonical pipeline order for findings (raw → verified), and what can silently drop or merge them?

## Severity-ranked dedupe + evidence suppression
**Path/Symbol:** `scripts/finding_verifier.py:verify_findings` (:77-123), `canonical_key` (:30-51), `should_suppress` (:54-74), `SEVERITY_RANK` (:17).
**Signature:** `verify_findings(findings: list, context: dict = None) -> {"findings","dropped","raw_count","verified_count"}`.
**Data Shape:** Finding = `{severity: Critical|Warning|Info|Pass, finding, evidence, fix, confidence, source}`; context carries counter-evidence like `{"readme_metrics": {"code_block_count": N, "h1_count": N, ...}}`.

### Decisive source
```python
SEVERITY_RANK = {"Critical": 0, "Warning": 1, "Info": 2, "Pass": 3}
...
if _sev_rank(item.get("severity")) < _sev_rank(existing.get("severity")):
    for field in ("severity", "finding", "evidence", "fix", "confidence"):
        existing[field] = item.get(field, existing.get(field))
```

**Flow:** suppression FIRST (counter-metric in context kills the finding with a recorded reason into `dropped`) → canonical key via 4 domain regexes (`missing-required:` / `missing-recommended:` / `community-profile-missing:` ×2 phrasings) else 160-char sanitized-text fallback → duplicates merge keeping the STRONGER severity and copying its five fields wholesale while accumulating distinct `sources` → final sort ascending by rank (Critical first).
**Invariant:** The whole-file regexes mean only GitHub-audit finding phrasings dedupe semantically — website-audit duplicates still collapse ONLY on near-identical text. Unknown severity ranks 9 (worst) so garbage sorts last. Suppression is context-gated, never unconditional.
**Probe:** `grep -c 'm = re.search' scripts/finding_verifier.py` (= 4); `grep -cF 'base[:160]' scripts/finding_verifier.py` (= 1); `grep -c 'return True, "Suppressed' scripts/finding_verifier.py` (= 4); direct tests `tests/test_content_ai_scripts.py`.
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"verify_findings canonical_key suppress severity","limit":5}'`.

## Verdict
Adopt verify-after-collect ordering plus stronger-severity merge as the universal report gate; extend the regex family set when porting to new audit domains; omit the GitHub-specific key patterns if your findings vocabulary differs (write YOUR domain's keys). Probes executed green @69199160.
