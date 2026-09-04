<!-- capsule-v2 -->
# bleach sanitizer + link rel policy — how does rendered HTML stay safe and unexploitable?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What is allowed through the sanitizer, how are links hardened, and why are "new" links suppressed?

## Sanitizer
**Path/Symbol:** `isso/html/__init__.py:Sanitizer` (9–83).
**Signature:** `sanitize(text) -> linker.linkify(bleach.clean(text, tags=..., attributes=..., strip=True))`.
**Data Shape:** element allowlist = Sundown's serializer set (+sub/sup) plus config extras; attribute map = `{table:[align], a:[href], code: <language-* class callback>, *: <config attrs>}`.

### Decisive source
```python
code_language_pattern = re.compile(r"^language-[a-zA-Z0-9]{1,20}$")

@staticmethod
def allow_attribute_class(tag, name, value):
    return name == "class" and bool(Sanitizer.code_language_pattern.match(value))

def set_links(attrs, new=False):
    # Linker can misinterpret text as a domain name and create new invalid links.
    if new:
        return None          # drop linker-INVENTED links entirely
    ...
    rel_values = [val for val in attrs.get(rel_key, "").split(" ") if val]
    for value in ["nofollow", "noopener"]:
        if value not in [rel_val.lower() for val_lower in rel_values]:
            rel_values.append(value)
    attrs[rel_key] = " ".join(rel_values)
```

**Flow:** markdown output → bleach.clean strips disallowed tags/attrs (strip=True removes tag but keeps text) → Linker adds rel="nofollow noopener" to EXISTING anchors only; mailto: links untouched; linker-fabricated links (bare domain-looking text) are discarded by returning None. `class` survives ONLY on `<code>` matching `language-…` (highlight hints).
**Invariant:** No user-controlled attribute passes except href on a, align on table, language-class on code, plus explicitly configured globals. The no-new-links rule prevents text like "example.com" from silently becoming an anchor with different semantics than the author saw in preview.
**Probe:** `grep -c 'if new:' isso/html/__init__.py` (`1`); `grep -c code_language_pattern isso/html/__init__.py` (`2`).
**Test:** `isso/tests/test_html.py:test_sanitizer`, `test_sanitizer_extensions`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "Sanitizer bleach clean linkify rel nofollow", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt allowlist-clean then link-harden pipeline. Adapt allowlists per product. Keep both quirks: mailto passthrough and invented-link suppression — they encode UX-correct security.
