<!-- capsule-v2 -->
# Formula-body compilation ladder — how does an arbitrary user formula string become a safely callable Python method body without ever crashing compilation?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What is the exact transform ladder from raw formula text to method body, and what happens at each malformed-input rung (bad indent, bad syntax, missing return, `$` inside strings)?

## Dollar-placeholder parse + AST patch ladder (codebuilder.py)
**Path/Symbol:** `sandbox/grist/codebuilder.py:make_formula_body` (:46–82), `_do_make_formula_body` (:98–204), `_multiline_string_nodes` (:85–95), `GristSyntaxError` (:28–31), `LAZY_ARG_FUNCTIONS` (:19–25), `_get_formula_type` (:357–363).
**Signature:** `make_formula_body(formula, default_value, assoc_value=None, indent='') -> textbuilder.Builder`.
**Data Shape:** input is raw user text (str or bytes decoded utf8); output is a Builder whose `.get_text()` is the final body AND which carries position-preserving patches (`assoc_value` rides `textbuilder.Text` so later renames map back to user-typed offsets); the failure mode is NEVER an exception out of compile — errors become body text that raises at evaluation time.

### Decisive source
```python
# Turn '$foo' into 'DOLLARfoo' FIRST so the translated entity is ONE token (precise error positions).
tmp_patches = textbuilder.make_regexp_patches(formula, DOLLAR_REGEX, 'DOLLAR')
tmp_formula = textbuilder.Replacer(textbuilder.Text(formula, None), tmp_patches)
atok = asttokens.ASTText(tmp_formula.get_text(), filename=code_filename)
try:
  tree = atok.tree                      # constructing ASTText does not parse; .tree does
except SyntaxError as e:
  return textbuilder.Text(_create_syntax_error_code(tmp_formula, formula, e))

for node in ast.walk(tree):
  if isinstance(node, ast.Name) and node.id.startswith('DOLLAR'):
    startpos = atok.get_text_range(node)[0]
    input_pos = tmp_formula.map_back_offset(startpos)   # back onto ORIGINAL text offsets
    m = DOLLAR_REGEX.match(formula, input_pos)
    if m:   # no match => pre-existing 'DOLLARblah' identifier; leave it alone
      patches.append(textbuilder.make_patch(formula, m.start(0), m.end(0), 'rec.'))

last_statement = tree.body[-1] if tree.body else None
if isinstance(last_statement, ast.Expr):            # auto-insert return for trailing expression
  patches.append(textbuilder.make_patch(formula, input_pos, input_pos, "return "))
elif last_statement is None:
  patches.append(textbuilder.make_patch(formula, len(formula), len(formula), '\npass'))
elif not any(type(node) == ast.Return for node in itertools.chain([last_statement], ast.walk(tree))):
    # message += equality hint when last_statement is an Assign: use == instead of =
    error = GristSyntaxError(message, ('<string>', 1, 1, ''))
    return textbuilder.Text(_create_syntax_error_code(tmp_formula, formula, error))

# Second parse with inference: catches rec assignments / kwarg cases where DOLLARfoo parsed fine.
with use_inferences(InferRecAssignment, InferRecAttrAssignment):
  try: astroid.parse(final_formula.get_text())
  except (astroid.AstroidSyntaxError, SyntaxError) as e:
    return textbuilder.Text(_create_syntax_error_code(final_formula, formula, getattr(e, "error", e)))
```

**Flow:** decode bytes -> empty/whitespace formula yields return-with-repr(default_value) -> dedent common leading whitespace -> dollar-columns become DOLLARfoo tokens -> parse (SyntaxError means emit raise-on-call error code) -> AST walk emits patches against ORIGINAL text: real DOLLAR Names become rec-prefixed, lazy args of IF/ISERR/ISERROR/IFERROR/PEEK get wrapped lambda calls (Excel short-circuit semantics, slices in LAZY_ARG_FUNCTIONS) -> trailing Expr gains a return keyword, comment-only body gains pass, no-return body raises the ==hint GristSyntaxError -> apply patches to original builder -> astroid re-parse under rec-assignment inference -> attach have_multiline_strings hint -> outer make_formula_body indents every non-empty line, then AST-reverts indentation ONLY inside multi-line string/f-string literals when the hint fires.
**Invariant:** every transform must keep a mapping back to user-typed positions (renames and error messages depend on it); malformed formulas COMPILE into code that raises structured errors as cell values — compilation itself cannot crash the engine — and `$` inside string literals/comments plus genuine DOLLAR-star identifiers are never rewritten.
**Probe:** `sandbox/grist/test_codebuilder.py::test_make_formula_body` (:13–38: empty gives default repr, $foo->rec.foo, string/comment/DOLLAR immunities :29–37), `test_make_formula_body_unicode_token_bug` (:208–223), `test_wrap_error` (:255).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "make_formula_body formula syntax error", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the placeholder-token-before-parse trick with offset remapping, patch-based position preservation, auto-return for trailing expressions, and the errors-as-runtime-code compilation posture. Adapt the lazy-function table and inference pass to your host function library; omit Grist column-type inference (`_get_formula_type`) and the asttokens/astroid stack only with an equally precise parser wrapper. Live-test caveat: python-plane runner blocked this lane (dependency-less ambient venv); probes pinned to exact test lines instead.
