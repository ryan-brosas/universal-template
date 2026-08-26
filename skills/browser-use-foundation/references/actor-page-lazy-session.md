<!-- capsule-v2 -->
# Actor Page lazy session + JS-string repair + LLM element-by-prompt — the standalone CDP convenience surface

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** How does a thin page-handle lazily attach CDP sessions, tolerate LLM-authored JavaScript strings, and find elements by natural-language prompt?

## Page._ensure_session / _fix_javascript_string / get_element_by_prompt
**Path/Symbol:** `browser_use/actor/page.py:Page._ensure_session` (53-70), `evaluate` (103-159), `_fix_javascript_string` (161-190), `press` modifier-bitmask ladder (213-277), `get_element_by_prompt` (399-479), `_extract_clean_markdown` (557-565).
**Signature:** `async def _ensure_session(self) -> str`; `async def evaluate(self, page_function: str, *args) -> str`
**Data Shape:** session created once per Page (`Target.attachToTarget {flatten:true}`) then four domains enabled in ONE asyncio.gather; evaluate returns ALWAYS a string (json.dumps for dict/list, str() otherwise); extract wraps llm.ainvoke in 120s wait_for.

### Decisive source
```python
if not (page_function.startswith('(') and '=>' in page_function):
    raise ValueError(f'JavaScript code must start with (...args) => format. Got: ...')
if args:
    arg_strs = [json.dumps(arg) for arg in args]
    expression = f'({page_function})({", ".join(arg_strs)})'
...
# 1. Remove obvious Python string wrapper quotes if they exist
if (js_code.startswith('"') and js_code.endswith('"')) or (...):
    inner = js_code[1:-1]
    if inner.count('"') + inner.count("'") == 0 or '() =>' in inner:
        js_code = inner
# 2. Only fix clearly escaped quotes that shouldn't be
if '\\"' in js_code and js_code.count('\\"') > js_code.count('"'):
    js_code = js_code.replace('\\"', '"')
```

**Flow:** any operation → `_ensure_session` memoizes attach+Page/DOM/Runtime/Network enables → evaluate: strip Python string artifacts CONSERVATIVELY (only when unambiguous), enforce arrow-function format, JSON-encode args into the call expression, Runtime.evaluate{returnByValue,awaitPromise}, exceptionDetails ⇒ RuntimeError → prompt path: full DOM tree → serialize_accessible_elements → fixed browser_state system prompt → structured ElementResponse{element_highlight_index} → index must exist in selector_map else None → wrap in Element with the node's own CDP session via `cdp_client_for_node`.
**Invariant:** JS-string repair must stay conservative — over-eager quote stripping corrupts valid JS containing quotes; the count-comparison guards (`count escaped > count plain`) are the load-bearing trick. Key combos press modifiers down FIRST (bitmask Alt=1/Control=2/Meta=4/Shift=8), main key with modifiers, then release modifiers REVERSED. LLM-returned indexes outside selector_map return None (never raise) — the model cannot fabricate valid targets.
**Probe:** deterministic source pins: `grep -n "must start with" browser_use/actor/page.py` (:121) and `"modifier_map = {'Alt': 1, 'Control': 2, 'Meta': 4, 'Shift': 8}"` (:225). Coverage caveat: no upstream unit file for actor/page.py; prompts pinned verbatim.
**Retrieve note:** graph anchor `Page._ensure_session` resolves actor/page.py:53-70.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_ensure_session _fix_javascript_string get_element_by_prompt", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy-attach + gather-enable + conservative JS-string cleanup for any raw-CDP convenience layer; adapt the prompt text to your serialization format (it references [index]<type>text</type> exactly); omit get_element_by_prompt unless you already ship an LLM client.
