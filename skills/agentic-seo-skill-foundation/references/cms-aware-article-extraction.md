<!-- capsule-v2 -->
# cms-aware article extraction — how do you pull the article body across Blogger/WordPress/Ghost/generic?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** What detection signals select the CMS, and what is each platform's body-container fallback ladder?

## Detection + scoped extraction
**Path/Symbol:** `scripts/article_seo.py:detect_cms` (:84-109), `extract_content` (:116-247).
**Signature:** `detect_cms(soup: BeautifulSoup, url: str) -> str` ∈ {blogger, wordpress, ghost, generic}.
**Data Shape:** extract_content returns `{title, meta_description, og_description, h1[], h2s[], h3s[], paragraphs[>8-word only], images[], labels[], publish_date, author}`.

### Decisive source
```python
if cms == "blogger":
    body_container = soup.find(attrs={"itemprop": "articleBody"})
    if not body_container:
        body_container = soup.find(attrs={"class": re.compile(r"post-body|entry-content", re.I)})
elif cms == "wordpress":
    body_container = (soup.find(attrs={"class": re.compile(r"entry-content|post-content|article-content", re.I)})
                      or soup.find("article"))
...
for p in para_scope.find_all("p"):
    text = p.get_text(" ", strip=True)
    if len(text.split()) > 8:  # skip tiny fragments
```

**Flow:** detection ladder: `<meta name=generator>` content (blogger/wordpress/ghost) → blogspot.com URL or `[data-blog-id]` → `wp-` body class → `gh-content|ghost-` class → `rel="https://api.w.org/"` link → generic. Extraction then scopes headings/paragraphs/images to the found container (falling back to whole soup) with per-CMS label/category harvesting (Blogger label-link classes, WP cat-links/tags-links) and a 3-selector publish-date ladder (`itemprop=datePublished` → published/post-date/entry-date classes → `article:published_time`).
**Invariant:** The >8-word paragraph filter silently drops captions/buttons from the corpus — word_count and keyword extraction both inherit this filter, so scores are computed on substantive paragraphs only. Author ladder = author/byline class → `span[itemprop=author]` → `a[rel=author]`, capped 100 chars.
**Probe:** `grep -cF 'if len(text.split()) > 8:' scripts/article_seo.py` (= 1); `grep -c 'blogspot.com' scripts/article_seo.py` (= 1); `grep -cF 'https://api.w.org/' scripts/article_seo.py` (= 1); DEPRECATED_SCHEMA = 8 members {HowTo, SpecialAnnouncement, CourseInfo, EstimatedSalary, LearningVideo, ClaimReview, VehicleListing, PracticeProblems}; RESTRICTED_SCHEMA = {"FAQPage"}.
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"detect_cms article body wordpress","limit":5}'`.

## Verdict
Adopt the generator-meta-first detection order and per-CMS container ladders; adapt class regexes as themes evolve; omit Blogger labels unless porting that platform. Probes executed green @69199160.
