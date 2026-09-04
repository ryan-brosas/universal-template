<!-- capsule-v2 -->
# Link headers — how does `Response.links` turn an RFC-style `Link:` header into a rel-keyed map?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `requests`. **Question:** What is the exact tokenization contract for `<url>; rel=x, <url2>; rel=y` link headers, including its tolerated sloppiness?

## utils.parse_header_links + Response.links
**Path/Symbol:** `src/requests/utils.py:parse_header_links` (:965-999); `src/requests/models.py:Response.links` (:1127-1142).
**Signature:** `parse_header_links(value: str) -> list[dict[str, str]]`; `Response.links -> dict[str, dict[str, str]]` property.
**Data Shape:** input is the raw `link` header value; output is a list of dicts always containing `"url"`, plus one key per parsed param; `links` collapses that list into a dict keyed by `rel` (falling back to `url`).

### Decisive source
```python
replace_chars = " '\""
value = value.strip(replace_chars)
if not value:
    return links

for val in re.split(", *<", value):          # comma + OPTIONAL space before '<'
    try:
        url, params = val.split(";", 1)
    except ValueError:
        url, params = val, ""                # URL with no params
    link = {"url": url.strip("<> '\"")}
    for param in params.split(";"):
        try:
            key, value = param.split("=")     # exactly ONE '=' — no maxsplit
        except ValueError:
            break                             # bare token aborts remaining params
        link[key.strip(replace_chars)] = value.strip(replace_chars)

# Response.links:
key = link.get("rel") or link.get("url")
resolved_links[key] = link
```

**Flow:** strip quote/space padding from both ends → split entries on `, *<` → per entry split URL from params at the FIRST `;` → split each param on `=` and strip `<> '" ` from keys and values → a param without `=` silently ends that entry's param loop (earlier params kept) → `Response.links` indexes by `rel`, else by `url`.
**Invariant:** The split regex is `, *<` — a comma NOT followed by optional-space-then-`<` stays inside a param value; and because `split("=")` has no maxsplit, a param like `title=a=b` raises ValueError and truncates all REMAINING params of that entry. Keys fall back to url only when `rel` is absent or empty-string-falsy.
**Probe:** Direct tests: `tests/test_utils.py::test_parse_header_links` (:677-697, parametrized incl. two-entry split, trailing-`;`, and empty-value→`[]` arms); `tests/test_requests.py::test_links` (:1272-1296) pins `r.links["next"]["rel"] == "next"` against a realistic GitHub header.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "requests", query: "parse_header_links rel url", limit: 10 });
```

## Verdict
Adopt the tokenizer byte-for-byte if you must parse GitHub-style pagination identically. Adapt to a real RFC 5988 parser when inputs are untrusted (this one mis-splits quoted commas). Omit nothing if compat with existing callers matters.
