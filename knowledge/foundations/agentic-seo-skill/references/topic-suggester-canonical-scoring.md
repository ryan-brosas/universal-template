<!-- capsule-v2 -->
# topic suggestion scoring — how do you rank candidate topics from mixed evidence that can partially fail?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** What score formula combines a canonical phrase table, raw word frequency, and competitor topics — and how does the result stay useful when the GitHub API call fails?

## Canonical-phrase scoring with graceful-degradation limitations
**Path/Symbol:** `scripts/repo_topic_suggester.py:suggest_topics` (:48-121), `CANONICAL_TOPICS` (:21-32), `_local_text` (:35-41), `_topicify` (:44-45). Consumes the pass-2 shared client (`auth_context`, `resolve_repo`, `fetch_json`) and the pass-3 CLI contract (`print_json_or_text`).
**Signature:** `suggest_topics(repo=None, path=".", token="", provider="auto", competitors=None, intent_terms=None, limit=20) -> dict`.
**Data Shape:** Output keys: `repo`, `auth_context` (mode trichotomy from `gh-auth-exit-zero-trap` capsule), `summary{current_topic_count, suggestions, competitors_used}`, `current_topics[]`, `suggested_topics[{topic, score, evidence[]}][]`, `competitor_topics{}`, `issues[]`, `limitations[]`. Every failed evidence source appends a human-readable string to `limitations` instead of raising.

### Decisive source
```python
try:
    resolved_repo = resolve_repo(repo, cwd=path)
    payload = fetch_json(f"/repos/{resolved_repo}", token=token, provider=provider)
    metadata = payload.get("data") or {}
except Exception as exc:
    limitations.append(f"GitHub metadata unavailable: {exc}")        # :60
...
score += phrase_hits * (20 + max(0, phrase_words - 1) * 12)          # :75
...
candidates[topic] += count * 5                                       # :95  competitor weight
...
if topic in current_topics or topic in STOP_WORDS or len(topic) < 3: # :100
    continue
```

**Flow:** auth context first (so the report always says which mode ran) → repo metadata fetch wrapped in catch-all: failure becomes a `limitations` entry and `metadata` stays `{}` → evidence text = name + description + local files (README.md, pyproject.toml, package.json concatenated) + intent terms, lowercased → canonical pass: for each of the 10 `CANONICAL_TOPICS` entries, every phrase found in the text scores `occurrences × (20 + max(0, words−1) × 12)` — a single-word phrase hits at 20/hit, two-word at 32/hit, three-word at 44/hit (longer phrases are rarer, so they are worth more per hit) → raw-word floor: every non-stopword token ≥3 chars (regex `[a-z][a-z0-9-]{2,}`) and ≤35 chars adds +1 to its `_topicify`d form (lowercase, non-alnum→hyphen, strip hyphens, cap 50) → competitor pass: each competitor's live topics add `count × 5` with evidence tag "competitor topic", per-competitor failures also go to `limitations` → ranking: `Counter.most_common()`, skip topics already present on the repo, stopword topics, and topics shorter than 3 chars; rows carry sorted-deduped `evidence`; cut at `limit` → issues: <3 current topics ⇒ warning `few_current_topics`; zero suggestions ⇒ info `no_suggestions`.
**Invariant:** No evidence source may raise out of `suggest_topics` — the function's total-function contract is what lets the direct test run it with `repo="invalid"` and still assert on local-only output. Canonical phrases must be matched as substrings of the LOWERCASED text (multi-word phrases like "technical seo" only match across word boundaries because the text is one blob); the per-hit × word-length bonus is the anti-spam rule — a README mentioning "seo" 20 times must not outrank one saying "technical seo" twice. Current topics are excluded from suggestions (you never re-suggest what the repo already has) but DO still contribute to the text blob for other topics' phrase matching.
**Probe:** direct upstream test executed green at pin: `tests/test_link_and_github_depth_scripts.py::test_topic_suggester_uses_local_intent_without_github` (:57-75) writes a tmp README ("Technical SEO CLI … Schema JSON-LD audit automation for AI search."), calls `suggest_topics(repo="invalid", path=tmp, token="", provider="api", intent_terms=["github seo"], limit=5)`, and asserts `"technical-seo"` lands in suggested topics AND `result["limitations"]` is non-empty — pinning both the local-evidence path and the degradation contract. Family subset 4 passed; full suite 34 passed (`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider`). Content pins: score formula :75 ×1, `count * 5` :95 ×1, filter :100 ×1, `GitHub metadata unavailable` :60 ×1.
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"suggest_topics canonical topics score limitations","limit":5}}
```
Not executed this pass — Codebase Memory MCP surface absent in the pass-3 session; seam selected and confirmed by direct full-file read (147L) plus direct test read at pin (recorded in verification.md). Execute on revalidation.

## Verdict
Adopt the three-evidence-source blend (curated phrase table with per-hit length bonus, raw-word frequency floor, external-signal multiplier) and the limitations-list degradation contract verbatim for any "suggest tags/labels/categories" problem. Adapt the canonical table to your domain vocabulary, the ×5 competitor weight and 20/12 base/bonus constants to your corpus, and the local-file list (README/pyproject/package.json) to your artifact set; omit nothing structural. Coverage caveat: the competitor-fetch loop and issue emission are content-pinned; only the local-evidence + degradation path has a direct test.
