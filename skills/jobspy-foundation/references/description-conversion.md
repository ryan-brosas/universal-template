<!-- capsule-v2 -->
# Description conversion — markdown/plain/HTML converters and the remove-attributes prettify pattern

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does JobSpy convert scraped HTML descriptions into markdown/plain text, and what is the `remove_attributes` prettify pattern used before conversion?

## Description converters
**Path/Symbol:** `jobspy/util.py` — `markdown_converter` (154–158), `plain_converter` (160–167), `remove_attributes` (205–208); used across `jobspy/linkedin/__init__.py` (273–276), `jobspy/indeed/__init__.py` (206–207), `jobspy/glassdoor/__init__.py` (254–256), `jobspy/ziprecruiter/__init__.py` (209–211), `jobspy/naukri/__init__.py` (173–174), `jobspy/bdjobs/__init__.py` (310–316).
**Signature:** `markdown_converter(description_html: str) -> str | None`; `plain_converter(description_html: str) -> str | None`; `remove_attributes(tag) -> tag`.
**Data Shape:** `DescriptionFormat` enum is `MARKDOWN | HTML | PLAIN`; the default in `ScraperInput` is `MARKDOWN`. `markdown_converter` returns `None` for `None` input; `plain_converter` collapses whitespace.

### Decisive source
```python
def markdown_converter(description_html):
    if description_html is None: return None
    markdown = md(description_html)          # markdownify
    return markdown.strip()

def plain_converter(decription_html):
    from bs4 import BeautifulSoup
    if decription_html is None: return None
    soup = BeautifulSoup(decription_html, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def remove_attributes(tag):
    for attr in list(tag.attrs): del tag[attr]
    return tag
```

**Flow:** when a site has HTML description and the format is `MARKDOWN`, call `markdown_converter` (markdownify + strip); when `PLAIN`, call `plain_converter` (BeautifulSoup `get_text(separator=" ")` + whitespace collapse + strip). `remove_attributes` strips ALL attributes from a tag before `prettify(formatter="html")` so the serialized HTML is clean (used by LinkedIn `_get_job_details`, ZipRecruiter `_get_descr`, BDJobs `_get_job_details`).
**Invariant:** `None` input → `None` output (never crashes); markdown strips surrounding whitespace; plain collapses runs of whitespace to single spaces; `remove_attributes` mutates the tag in place and is applied BEFORE `prettify` so no `class`/`id`/`style` leaks into the stored description. The `HTML` format is the raw prettified fragment (no conversion).
**Probe:** no in-repo test suite; verified against source + per-site call sites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "markdown_converter plain_converter remove_attributes DescriptionFormat", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the markdown/plain conversion pair and the remove-attributes-before-prettify pattern. Adapt the markdownify/BeautifulSoup calls to your HTML source. Omit the `HTML` passthrough if you always convert. Coverage caveat: no in-repo tests; verified against source.
