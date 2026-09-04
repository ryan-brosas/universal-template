<!-- capsule-v2 -->
# Griffe docstring extraction — turning a function's docstring into a main description plus per-parameter descriptions

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How are tool docstrings parsed into description/schema metadata across Google/NumPy/Sphinx styles, and when does the description become XML?

## `doc_descriptions` + `_infer_docstring_style`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_griffe.py:doc_descriptions` (:18–80), `_infer_docstring_style` (:83–92), `_docstring_style_patterns` (:96–169), `_disable_griffe_logging` (:172–178).
**Signature:** `doc_descriptions(func, sig: Signature, *, docstring_format: DocstringFormat) -> tuple[str | None, dict[str, str]]`.
**Data Shape:** Returns `(main_desc, params)` — `main_desc` is plain text normally but becomes `<summary>…</summary>\n<returns>\n[<type>…</type>\n]<description>…</description>\n</returns>` XML when the docstring has a returns section; `params` maps parameter names to descriptions. No docstring → `(None, {})`.

### Decisive source
```python
# _griffe.py:64-78 — the returns-section XML fork
main_desc = ''
if main := next((p for p in sections if p.kind == DocstringSectionKind.text), None):
    main_desc = main.value
if return_ := next((p for p in sections if p.kind == DocstringSectionKind.returns), None):
    return_statement = return_.value[0]
    return_desc, return_type = return_statement.description, return_statement.annotation
    type_tag = f'<type>{return_type}</type>\n' if return_type else ''
    return_xml = f'<returns>\n{type_tag}<description>{return_desc}</description>\n</returns>'
    main_desc = f'<summary>{main_desc}</summary>\n{return_xml}' if main_desc else return_xml
return main_desc or None if False else main_desc, params   # plain text passes through unchanged
```

**Flow:** `docstring_format='auto'` infers style by regex-probing section markers in priority order Sphinx → Google → NumPy (each pattern tried against every alias word of that style's markers) → default 'google' on no match → parse via griffe with Google-specific parser options only when Google (`returns_named_value=False, returns_multiple_items=False`) → take first parameters/text/returns sections.

**Invariant:** The Signature instance doubles as griffe's parent object (`cast(GriffeObject, sig)` — griffe issue #293 workaround); root logging is suppressed during parse because griffe logs warnings through the root logger (issue #293#issuecomment workaround). Style inference is deliberately simplistic and ordered — a docstring containing ANY Sphinx-style marker line wins Sphinx even if Google markers also appear.

**Probe:** Direct-test coverage caveat: no dedicated unit test file pins this module's branches at the pinned commit (extraction exercised indirectly through tool-schema tests, e.g. `tests/test_tools.py` docstring-description assertions); treat exact XML shape as source-pinned, not test-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "doc_descriptions docstring_format griffe DocstringSectionKind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-style inference order and the returns-section→XML transform (it keeps return descriptions visible to models whose schema rendering drops them). Adapt the XML vocabulary to your schema format. Omit griffe version quirks beyond the two cited workarounds.
