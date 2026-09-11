<!-- capsule-v2 -->
# dual-parser HTML normalization kernel — what canonical page shape do all 88 evidence collectors agree on?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** What does `parse_html` guarantee (and deliberately not guarantee) so downstream scorers can trust its dict?

## Canonical page-dict builder
**Path/Symbol:** `scripts/seo_common.py:parse_html` (:168-256), with `normalize_url` (:49-61), `is_responsive_fill_image` (:64-68), `fetch_url` (:90-138), `load_html` (:159-165).
**Signature:** `parse_html(html: str, base_url: str = "") -> dict`.
**Data Shape:** Returns `{title, meta_description, meta_robots, viewport, canonical, lang, headings: {h1..h6: [str]}, links: [{href,text(≤160),rel}], images: [{src,alt,width,height,is_responsive_fill,loading,srcset,sizes,fetchpriority,decoding}], schema: [parsed JSON-LD | {"error":"invalid_json","snippet":first160}], word_count, body_text, forms, landmarks{main,nav,header,footer}, labels, inputs, buttons, soup}`.

### Decisive source
```python
except json.JSONDecodeError:
    schema.append({"error": "invalid_json", "snippet": raw[:160]})
for element in soup(["script", "style", "noscript", "template"]):
    element.decompose()
body_text = soup.get_text(" ", strip=True)
```

**Flow:** parser choice is environment-adaptive (`lxml` if already imported else stdlib `html.parser` — results can differ subtly across hosts) → meta keys fold name/property/http-equiv into one lowercased map (later tags overwrite) → canonical + hrefs resolve against `base_url`, fragments stripped → non-content anchors (`#`,`javascript:`,`mailto:`,`tel:`,`data:`) dropped → Next.js fill images (`data-nimg="fill"` or absolute-inset style) flagged `is_responsive_fill` so missing width/height is NOT a finding → JSON-LD blocks parse to dicts with invalid-JSON sentinel objects preserving a snippet → script/style/noscript/template decomposed BEFORE text extraction → words tokenized `\b[\w'-]+\b`.
**Invariant:** The invalid-JSON sentinel keeps malformed schema VISIBLE as data instead of raising — consumers must branch on `"error" in block`. And `soup` is returned live: any consumer mutating it affects every later reader.
**Probe:** `grep -c 'ld+json' scripts/seo_common.py` (= 1); `grep -cF '"error": "invalid_json"' scripts/seo_common.py` (= 1); `grep -c 'element.decompose()' scripts/seo_common.py` (= 1); direct test `tests/test_core_seo_scripts.py::test_parse_html_marks_next_image_fill_as_responsive_fill`.
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"parse_html images schema word_count","limit":5}'`.

## Verdict
Adopt this dict as the inter-script contract for any multi-check audit tool; adapt the responsive-fill heuristic to your framework set; omit the lxml-conditional parser selection only if you pin one parser per host. Probes executed green @69199160.
