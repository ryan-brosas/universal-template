<!-- capsule-v2 -->
# JS auto-repair before execution — how do you fix LLM-mangled JavaScript instead of failing the action?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** which escaping artifacts does browser-use repair in agent-written JS, and what must it never touch?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `Tools._validate_and_fix_javascript` (:1943-2020); consumer `evaluate` action (:1806, executes validated code with awaitPromise=True; wasThrown backup check :1862).
**Signature:** `def _validate_and_fix_javascript(self, code: str) -> str`.

### Decisive source
```python
# Pattern 1: double-escaped quotes          \\\" -> \"
fixed_code = re.sub(r'\\"', '"', code)
# Pattern 2: over-escaped regex classes     \\\\d -> \\d (and char-class members)
fixed_code = re.sub(r'\\\\([dDsSwWbBnrtfv])', r'\\\1', fixed_code)
fixed_code = re.sub(r'\\\\([.*+?^${}()|[\]])', r'\\\1', fixed_code)
# Patterns 3-6: mixed-quote selectors converted to template literals so inner
# quotes survive — document.evaluate(...), querySelector(All), .closest, .matches:
xpath_pattern = r'document\.evaluate\s*\(\s*"([^"]*)"\s*,'
def fix_xpath_quotes(m): return f'document.evaluate(`{m.group(1)}`,'
# Note: getAttribute deliberately NOT fixed - attribute names rarely have mixed quotes

changes_made = []
if r'\"' in code and r'\"' not in fixed_code: changes_made.append('fixed escaped quotes')
if '`' in fixed_code and '`' not in code: changes_made.append('converted mixed quotes to template literals')
```

**Flow:** agent JS → six regex repairs applied unconditionally (idempotent: repaired output no longer matches) → Runtime.evaluate with returnByValue + awaitPromise always on (ignored for non-promises) → exceptionDetails OR legacy `wasThrown` flag both become structured error ActionResults including a 500-char preview of the VALIDATED code.
**Invariant:** repairs are narrow and idempotent — broad quote rewriting would corrupt legitimate backtick strings; result text >20k chars truncated AFTER extracting data-URI images into metadata (`[Image]` placeholders keep them deliverable as ContentPartImageParam); memory keeps full result only under 10k chars else points at length only.
**Probe:** deterministic source probe (coverage caveat: no dedicated unit file; behavior pinned by citation :1943-:2020 and evaluate-path error shapes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "_validate_and_fix_javascript evaluate exceptionDetails wasThrown data:image", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the six-repair ladder + dual error detection (exceptionDetails/wasThrown) + image-extraction-before-truncation ordering; adapt limits; omit the debug log cosmetics.
