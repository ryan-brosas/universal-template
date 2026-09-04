<!-- capsule-v2 -->
# llms.txt quality scoring — how do you grade a site's LLM-facing manifest?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** What is the llmstxt.org grammar the parser accepts, and what is the exact point ladder with its bonus tiers?

## Manifest parser + additive grader
**Path/Symbol:** `scripts/llms_txt_checker.py:check_llms_txt` (:30-100), `_parse_llms_txt` (:103-152), `_score_quality` (:155-202).
**Signature:** `check_llms_txt(url: str, timeout: int = 15) -> dict`.
**Data Shape:** `{url, full_url, exists, full_exists, status, full_status, content, parsed{title,description,sections[{name,links[]}],links[]}, quality{score,issues[],suggestions[]}, error}`.

### Decisive source
```python
if parsed["title"]:
    score += 20
...
if len(parsed["description"]) < 20:
    quality["issues"].append("⚠️ Description too short")
elif len(parsed["description"]) > 50:
    score += 5  # Bonus for good description
```

**Flow:** probe `/llms.txt` then optional `/llms-full.txt` (existence recorded, never parsed) → first `# `-line becomes title else issue → `> `-prefixed lines join into description (first wins, later appended) → `## ` opens a section → `- [Title](URL): Desc` links attach BOTH to the global list and the current section → grading: title 20 + description 20 (bonus +5 if >50 chars; <20 flagged) + sections 15 (+5 at ≥3) + links 20 (+5 at ≥5, +5 more at ≥10) + content >200 chars 5 → capped `min(score, 100)` = 105 raw max.
**Invariant:** Missing file scores 0 with an explicit 🔴 issue — absence and low quality are distinct states in `exists` vs `quality.score`. The link regex requires the `- [` prefix; bare markdown links parse to nothing.
**Probe:** `grep -cF 'score += 20' scripts/llms_txt_checker.py` (= 3: title/description/links); `grep -cE '>= (5|10):' scripts/llms_txt_checker.py` (= 2); `grep -cF 'min(score, 100)' scripts/llms_txt_checker.py` (= 1); `grep -cF 'llms-full.txt' scripts/llms_txt_checker.py` (= 1).
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"llms txt quality score sections","limit":5}'`.

## Verdict
Adopt the section/link grammar and tiered-bonus ladder for any llms.txt validator; adapt point weights to your rubric; omit `llms-full.txt` probing only if your consumers never read it. Probes executed green @69199160.
