<!-- capsule-v2 -->
# repo-audit finding contract — how does an audit report stay honest when half its data sources are missing?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** How do you encode per-finding evidence confidence and gate local checks so a report never presents inferred claims as confirmed?

## Envelope + confidence downgrade + severity-weighted score
**Path/Symbol:** `scripts/github_repo_audit.py:build_audit` (:195-495), `add_finding` (:77-95), `score_findings` (:98-113), `local_file_signals` (:59-74).
**Signature:** `build_audit(repo, token, cwd, provider) -> dict`; `score_findings(findings) -> {"score","rating","critical","warning"}`.
**Data Shape:** Report envelope keys: `timestamp_utc, repo, auth_context, local_repo_context, api_access, limitations[], metadata, title_analysis, community_profile, local_signals, findings[], summary`. Finding shape (from `add_finding`): `{area, severity, confidence, finding, evidence, fix}`.

### Decisive source
```python
confidence = "Confirmed"
try:
    repo_resp = fetch_json(f"/repos/{repo}", token=token, provider=provider)
    ...
except GitHubAPIError as exc:
    confidence = "Likely"                                   # EVERY later finding inherits :241
    report["limitations"].append(f"Repository API unavailable: {exc} ...")
...
local_checks_enabled = bool(local_repo) and (local_repo.lower() == repo.lower())  # :198
```
```python
score = max(0, 100 - (critical * 20) - (warning * 8))       # Pass/Info severities free :102
if not findings:
    add_finding(findings, "Overall", "Pass", "Confirmed",
                "No major GitHub SEO issues detected in current scope.", ...)  # sentinel :483-492
```

**Flow:** stamp envelope with auth context → infer origin; enable local file checks ONLY when the detected origin matches the target slug case-insensitively, else append a limitation → fetch `/repos/{repo}` and `/repos/{repo}/community/profile`; EITHER failure downgrades module-level `confidence` to `"Likely"` and records the limitation while continuing → metadata checks emit findings through severity ladders (description missing=Warning/<60 chars=Info; topics 0=Warning/>20=Critical/<5=Info; archived=Critical; push>180d=Warning; underscore slug=Warning) → community health <85% and six named profile files each warn → local checks (when enabled) mark README/LICENSE missing as **Critical "Confirmed"** and six trust artifacts as Warning — direct filesystem evidence keeps full confidence even when APIs failed → empty findings ⇒ one `Pass` sentinel → summary scored.
**Invariant:** Confidence travels with evidence provenance: API-derived findings can be at most "Likely" once an endpoint failed, but locally verified facts stay "Confirmed". The scoring function counts only Critical/Warning — `Pass`, `Info` findings are deliberately score-free. Local checks must NEVER run against an unrelated checkout (origin-gating prevents auditing the wrong tree).
**Probe:** executed grep pins on `scripts/github_repo_audit.py`: `\(critical \* 20\) - \(warning \* 8\)` = 1 (:102), `local_checks_enabled` = 5 (:198,:203,:209,:230,:457), `confidence = "Likely"` = 2 (:241,:251), `pushed_days > 180` = 1 (:368), `"Overall",` sentinel = 1 (:486); repo-owned suite 34 passed @pin.
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"build_audit findings confidence limitations community profile audit","limit":5}}
```
Executed live: resolves `build_audit` (:195-495) rank-1 and `score_findings` rank-2 (also surfaces sibling consumers `github_seo_report.collect_findings`, `generate_report.collect_report_findings` — deferred seams).

## Verdict
Adopt the finding schema (area/severity/confidence/finding/evidence/fix), the Confirmed→Likely downgrade-on-source-failure rule, origin-gated local verification, and the `100 − 20·Critical − 8·Warning` weights verbatim; adapt thresholds (180-day staleness, 85% health, 60-char description) to your domain's reality; omit the GitHub-specific metadata checks themselves — they are instances of the ladders, not the contract. Coverage caveat: no upstream unit test drives `build_audit` end-to-end (network-bound); behavior pinned by executed content probes and byte-identical snippet/direct reads at pin.
