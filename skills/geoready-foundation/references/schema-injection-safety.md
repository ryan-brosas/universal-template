<!-- capsule-v2 -->
# Schema injection safety — placeholder substitution, </script> escaping, and FAQ harvesting without tree mutation

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you generate and inject JSON-LD into HTML without JSON injection or XSS via premature script close?

## fill_template / schema_to_html_tag / inject_schema_into_html
**Path/Symbol:** `src/geo_optimizer/core/schema_injector.py:fill_template` (98–123), `schema_to_html_tag` (126–135), `inject_schema_into_html` (275–335), `extract_faq_from_html` (138–181).
**Signature:** `fill_template(template: dict, values: dict) -> dict`; `schema_to_html_tag(schema_dict) -> str`; `inject_schema_into_html(file_path, schema_dict, backup=True, validate=True) -> (bool, msg|None)`.
**Data Shape:** templates from config `SCHEMA_TEMPLATES` with `{{key}}` placeholders; file ops restricted to existing `.html/.htm` inside validated paths.

### Decisive source
```python
template_str = json.dumps(template)
for key, value in values.items():
    safe_value = str(value) if value else ""
    # json.dumps adds quotes; strip the OUTER pair but keep internal escapes (", \, newline)
    escaped = json.dumps(safe_value)[1:-1]
    template_str = template_str.replace(f"{{{{{key}}}}}", escaped)
residui = re.findall(r"\{\{\w+\}\}", template_str)     # #114: leftover placeholders = warning
...
json_str = json.dumps(schema_dict, indent=2, ensure_ascii=False)
json_str = json_str.replace("</", r"<\/")   # browser would close <script> at '</script>' inside JSON
```

**Flow:** template→JSON-string→escape-each-value-by-reserialization→substitute→warn on leftovers→parse back to dict. Injection path: validate path (`validate_safe_path`, extension+existence), optionally validate JSON-LD required-fields per type (`validate_jsonld(..., strict=False)`), `.bak` backup, parse soup, append escaped `<script type="application/ld+json">` before `</head>` — refusing when no head exists. FAQ harvest reads dt/dd, details/summary (answer = full text minus question WITHOUT `.extract()` so the caller's tree is never mutated), and faq/question class containers.
**Invariant:** The `</` → `<\/` replacement is mandatory on EVERY serialization into a script context (both raw tag and Astro template emit it identically); value escaping must go through json.dumps round-trip, not ad-hoc replace chains, or quotes/backslashes break the surrounding JSON. Deepcopy templates before mutation (#17).
**Probe:** `tests/test_core.py::test_basic_faq_schema` + `test_analyze_file_with_faqs` (+ security suites covering injection; `PYTHONPATH=src pytest tests/test_core.py tests/test_p0_security_fixes.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "fill_template schema inject", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt reserialization-escaping + script-close-guard + non-mutating extraction for any HTML/JSON-LD tooling; adapt template catalog; omit the Astro snippet emitter unless targeting Astro.
