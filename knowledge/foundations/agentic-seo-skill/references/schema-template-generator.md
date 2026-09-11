<!-- capsule-v2 -->
# schema-template generator — how do you emit safe JSON-LD templates and auto-detect the right type?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** Why must templates be deep-copied before emission, and what is the detection fallback order?

## Bundled template catalog + detector
**Path/Symbol:** `scripts/schema_template_generator.py:load_templates` (:60-66), `detect_template_type` (:68-92), `get_template` (:94-103), `FALLBACK_TEMPLATES` (:18-57).
**Signature:** `get_template(schema_type: str, compact: bool = False) -> dict` (raises `SystemExit` on unknown type listing available types).
**Data Shape:** templates.json entries `{type, description, template:<JSON-LD dict>}`; emitted wrapper `{type, description, json_ld}` or bare object with `--compact`.

### Decisive source
```python
templates.update({key: value for key, value in FALLBACK_TEMPLATES.items() if key not in templates})
...
template = deepcopy(templates[schema_type]["template"])
```

**Flow:** load bundled `resources/schema/templates.json` → overlay Product/Review fallback dicts ONLY for missing keys → detection: existing page JSON-LD types checked against catalog FIRST, else keyword ladder video→VideoObject, product/price/buy/cart→ProductGroup, near-me/hours/location→LocalBusiness, blog/guide/article→BlogPosting, default WebSite → emission always `deepcopy`s so `[Placeholder]` mutation can never poison the in-memory catalog.
**Invariant:** The deepcopy is the placeholder-safety contract — templates are mutable dicts full of `[Product Name]` markers; returning the catalog entry directly would let one caller's fill-in corrupt every later caller. Fallbacks are subordinate to shipped config by design.
**Probe:** module-import check `len(stg.FALLBACK_TEMPLATES)` (= 2); `grep -cF 'if key not in templates' scripts/schema_template_generator.py` (= 1); `grep -c 'deepcopy' scripts/schema_template_generator.py` (= 2 import+use).
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"schema template generator detect","limit":5}'`.

## Verdict
Adopt catalog+fallback merge and copy-on-issue semantics for any template emitter; adapt the keyword ladder to your domain's type set; omit CLI output shaping. Probes executed green @69199160.
