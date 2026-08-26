<!-- capsule-v2 -->
# Markdown renderer selection + p-wrapper — how is user text rendered and normalized?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How does Markup pick mistune vs deprecated misaka, and what post-processing guarantees an HTML block?

## Markup factory + render wrapper
**Path/Symbol:** `isso/html/__init__.py:Markup` (86–121); `isso/html/markdown.py:Markdown.render` (13–20); `isso/html/mistune.py:MistuneMarkdown` (10–37).
**Signature:** `Markup.render(text) = sanitizer.sanitize(parser.render(text))`; `Markdown.render` rstrips newlines then wraps in `<p>` unless output starts `<p>` or ends `</p>`.
**Data Shape:** mistune built via `create_markdown(escape=True, hard_wrap=hard_wrap, plugins=[...])` — escape is FORCED on (config cannot disable it).

### Decisive source
```python
# markdown.py
def render(self, text: str) -> str:
    rv = self._render(text).rstrip("\n")
    if rv.startswith("<p>") or rv.endswith("</p>"):
        return rv
    return "<p>" + rv + "</p>"

# __init__.py
if conf_markup.has_option("renderer") and conf_markup.get("renderer") == "mistune":
    self.parser = MistuneMarkdown(conf.section("markup.mistune"))
elif not conf_markup.has_option("renderer") or conf_markup.get("renderer") == "misaka":
    self.parser = MisakaMarkdown(conf)
    logging.warning("Misaka has been deprecated. ...")
else:
    logging.fatal("The `renderer` configuration option is set to an unknown value: %s ...")
    raise ValueError(...)
```

**Flow:** unknown renderer values are FATAL (fail-closed, not fallback); misaka still works but deprecation-warns. Mistune's empty-plugin config quirk (`getlist` yields `['']`) must coerce to None or create_markdown breaks. The p-wrapper normalizes single-line renders (e.g. plain URLs) into block-level HTML so the client CSS always receives a block.
**Invariant:** Raw HTML in comments is ALWAYS escaped (mistune escape=True hard-coded); rendering happens at READ time (`isso.render` calls in views), never stored — so renderer migrations instantly restyle old content.
**Probe:** `grep -cF 'startswith("<p>")' isso/html/markdown.py` (`1`); anchor for forced-escape rationale: `grep -c 'escape=True' isso/html/mistune.py` (`1`).
**Test:** `isso/tests/test_html_mistune.py:test_markdown` (`<em>Hi</em>` input → `&lt;em&gt;Hi&lt;/em&gt;` escaped), `test_markdown_plugins`, `test_github_flavoured_markdown`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "Markup renderer mistune misaka render paragraph", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt read-time rendering + fail-closed renderer selection + escape-forced parser. Adapt the wrapper rule to your block model. Omit the misaka branch (deprecated upstream).
