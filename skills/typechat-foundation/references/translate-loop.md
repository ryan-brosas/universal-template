<!-- capsule-v2 -->
# Translate loop — where do JSON extraction, repair, and failure boundaries live?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How does the translator turn a raw LLM string into a validated object, and what exactly happens on each failure class?

## TS createJsonTranslator.translate
**Path/Symbol:** `typescript/src/typechat.ts:124-163` (`translate`, inner to `createJsonTranslator` :97-163).
**Signature:** `async translate(request: string, promptPreamble?: string | PromptSection[]): Promise<Result<T>>`.
**Data Shape:** preamble normalized: bare string → single `{role:"user"}` section; loop state = growing `PromptSection[]` + one-shot `attemptRepair` latch copied from the public property at entry (so mutating the property mid-flight cannot loop forever).

### Decisive source
```ts
const startIndex = responseText.indexOf("{");
const endIndex = responseText.lastIndexOf("}");
if (!(startIndex >= 0 && endIndex > startIndex)) {
    return error(`Response is not JSON:\n${responseText}`);
}
const jsonText = responseText.slice(startIndex, endIndex + 1);
```
**Flow:** complete → slice first-`{`..last-`}` → JSON.parse (SyntaxError message becomes the Failure) → optional `stripNulls` → `validator.validate` → on success chain through `validateInstance` hook → on failure append assistant+repair-prompt turns and retry EXACTLY once (`attemptRepair = false` after first push, :160).
**Invariant:** repair is one-shot and unconditional-by-default — there is no per-error retry policy; the repair context is the FULL original response text (not the sliced JSON) pushed as assistant content. Validation success returns the validator's output instance (post-stripNulls), not the raw parse.

## Python translate
**Path/Symbol:** `python/src/typechat/_internal/translator.py:52-101` (`TypeChatJsonTranslator.translate`) with prompts `_create_request_prompt`/:103-115, `_create_repair_prompt`/:117-125.
**Signature:** `async def translate(self, input: str, *, prompt_preamble: str | list[PromptSection] | None = None) -> Result[T]`.
**Data Shape:** `_max_repair_attempts = 1` class attr (:23); guard is `if num_repairs_attempted >= self._max_repair_attempts` BEFORE increment (:97).

### Decisive source
```py
first_curly = text_response.find("{")
last_curly = text_response.rfind("}") + 1
if 0 <= first_curly < last_curly:
    trimmed_response = text_response[first_curly:last_curly]
    parsed_response = pydantic_core.from_json(trimmed_response, allow_inf_nan=False, cache_strings=False)
```
**Flow:** identical ladder but THREE distinct failure messages: no-curly → "Response did not contain any text resembling JSON."; parse ValueError → "Error: {e}\n\nAttempted to parse:..."; validation → validator's rendered message. Python parses with `allow_inf_nan=False` so `NaN`/`Infinity` literals are rejected as invalid JSON (TS `JSON.parse` also rejects them — port both ways or accept divergent behavior).
**Invariant:** empty-object edge differs by construction: `indexOf("{")===lastIndexOf("}")` makes TS reject `"{}"` while Python's rfind+1 accepts it — this asymmetry is real in shipped code; do not "fix" it silently when porting either side.
**Probe:** `grep -c 'attemptRepair = false' typescript/src/typechat.ts` (=1); `grep -c "'''" python/src/typechat/_internal/translator.py` (=4 triple-quote delimiters across the two prompt templates). EXECUTED live this pass: repo-owned `pytest -vv` from `python/` at pin 83caa124 under Python 3.14.7 → all five `test_translator.py` conversation snapshots pass (`__snapshots__/test_translator.ambr`, read directly), including the parse-error variant ("Error: expected `,` or `}` at line 1 column 16" + "Attempted to parse:") and the validation variant ("Validation path `c` failed ... Field required") — the repair turn re-sends FULL original request + assistant response + revision instruction, byte-for-byte. See py-offline-model-fakes for the fake-model mechanics.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"createJsonTranslator translate attemptRepair","limit":5}'
// rank1 typescript/src/typechat.ts 97-163; py twin Method python/.../translator.py 52-101
```

## Verdict
Adopt the extract-slice-parse-validate-repair-once loop verbatim; adapt the failure-message wording to host conventions but keep three distinct classes; omit TS `stripNulls` if schemas tolerate nulls. Direct tests cover the conversation shape (test_translator.py ×5 snapshots); no coverage caveat.
