<!-- capsule-v2 -->
# repo-file-inventory scoring — how do you score presence-of-files without punishing errors twice?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** What is the sectioned check taxonomy, and why does the score subtract only warnings?

## Five-section inventory + warning-only penalty
**Path/Symbol:** `scripts/repo_file_inventory.py:inventory_repository` (:25-69), `CHECKS` taxonomy (:12-18).
**Signature:** `inventory_repository(path=".") -> dict`.
**Data Shape:** Result keys: `path, summary{present,missing,score}, sections{core,docs,governance,github,package→[{path,present,type}]}, readme{present,bytes,headings,install_mentions,demo_mentions}, issues[]`. Issue severities: `error` / `warning`; types: `missing_required_file`, `missing_trust_file`, `readme_install_cta`.

### Decisive source
```python
score = max(0,
    round(100 * len(present) / max(1, len(present) + len(missing)))
    - len([i for i in issues if i["severity"] == "warning"]) * 2)      # :62
if readme_stats["present"] and readme_stats["install_mentions"] == 0:
    issues.append({"severity": "warning", "type": "readme_install_cta",
                   "path": "README.md",
                   "message": "README has no obvious install call-to-action"})  # :59-61
```

**Flow:** iterate five fixed sections (`core`: README/LICENSE/CHANGELOG; `docs`: docs/examples/demo/site dirs; `governance`: CONTRIBUTING/CODE_OF_CONDUCT/SECURITY/SUPPORT/CITATION.cff; `github`: workflows/issue-templates/PR-template(s)/CODEOWNERS/dependabot; `package`: pyproject/package.json/requirements.txt/setup.py), each row typed `file` vs `directory` by `is_dir` → README stats: byte length of UTF-8 text, heading count = lines starting `#`, `install`/`demo` substring counts on lowercased text → issues: missing README/LICENSE ⇒ error `missing_required_file`; missing CONTRIBUTING/SECURITY/CHANGELOG ⇒ warning `missing_trust_file`; present-but-install-less README ⇒ warning CTA → score: presence ratio ×100 minus 2 per warning, floored at 0.
**Invariant:** Errors already drag the ratio down because the required files count as missing — penalizing them again in the subtraction would double-count; only warnings are additive deductions. The denominator guard `max(1, …)` keeps an empty tree at score 0 instead of ZeroDivisionError. Substring `count("install")` is deliberately crude (matches "installation") — a heuristic CTA detector, not a parser.
**Probe:** direct upstream test executed green at pin: `tests/test_link_and_github_depth_scripts.py::test_repo_file_inventory_scores_present_files` (:44-54) builds tmp README+LICENSE+SECURITY and asserts `summary.present >= 3`, `readme.install_mentions == 1`, and NO `readme_install_cta` issue; full suite 34 passed (`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider`). Content pins: `readme_install_cta` = 1 (:60), `== "warning"]) \* 2` = 1 (:62).
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"inventory repository checks readme install mentions score","limit":5}}
```
Executed live: resolves `inventory_repository` (:25-69) rank-1; also surfaces consumer `github_weekly_scorecard._score_from_inventory` (deferred seam).

## Verdict
Adopt the sectioned taxonomy shape and the warning-only subtraction verbatim for any checklist scorer; adapt the file lists to your ecosystem (e.g. add `.gitlab` section) and replace substring CTA detection if you have real parsing; omit nothing structural — this is the leaf's smallest complete scorer. Coverage caveat: the module has exactly one direct upstream test (the local-scoring path); the `github`-section rows and directory typing are content-pinned only (:16,:34).
