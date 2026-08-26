<!-- capsule-v2 -->
# LLM response salvage — how do you parse extraction JSON when the model wraps, thinks, or shapes facts oddly?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** what is the ladder that turns raw LLM output into structured memories without failing the add?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/utils.py`: `remove_code_blocks` (:115-129), `extract_json` (:133-150), `normalize_facts` (:90-112), `ensure_json_instruction` (:36-58), `parse_messages` (:61-76); consumed in `_add_to_vector_store` Phase 2 (:971-984).
**Signature:** `remove_code_blocks(content) -> str` (strips one enclosing ``` fence AND `<think>` spans); `extract_json(text) -> str` (fenced block → first-{-to-last-} → raw).
**Data Shape:** target: `json.loads(...).get("memory", [])`; tolerated fact shapes: str | `{"fact": ...}` | `{"text": ...}` | other→str().

### Decisive source
```python
# remove_code_blocks: strip fence, then <think> reasoning traces
return re.sub(r"<think>.*?</think>", "", match_res, flags=re.DOTALL).strip()
...
# utils.py ensure_json_instruction:
# OpenAI's API requires the word 'json' to appear in the messages when
# response_format is set to {"type": "json_object"}. When users provide a
# custom_instructions that doesn't include 'json', this causes a 400 error.
```

**Flow:** generation with `response_format={"type":"json_object"}` → transport failure RAISES (LLMError) → strip code fences + `<think>` blocks → try strict-ish `json.loads(strict=False)` → on JSONDecodeError fall back to `extract_json` brace-slicing → `.get("memory", [])` tolerates missing key; per-fact normalization accepts dict-shaped facts from small models. Empty/whitespace response ⇒ empty list, messages still saved.
**Invariant:** parsing failure degrades to "no memories extracted", never raises — only TRANSPORT failure is fatal; `ensure_json_instruction` patches the OpenAI json-mode contract violation caused by user custom instructions lacking the literal word "json"; tool-call messages without content are skipped in both parsers (`parse_messages`, `parse_vision_messages`).
**Probe:** `tests/test_chatty_llm_parsing.py` (fence/think salvage); `tests/memory/test_memory_utils.py` (fact-shape normalization, extract_json).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "remove_code_blocks extract_json normalize_facts ensure_json_instruction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier salvage order and the raise-on-transport/degrade-on-parse split; adapt fact schemas; keep the json-word patch if you support OpenAI-style json mode.
