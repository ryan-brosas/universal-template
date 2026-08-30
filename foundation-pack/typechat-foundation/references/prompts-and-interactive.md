<!-- capsule-v2 -->
# Prompt templates + interactive loop — what exact text drives the model, and how are sessions driven?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** What is the byte-exact request/repair prompt wording (both languages), and what are the file-mode vs REPL semantics of the request loop?

## Request prompt
**Path/Symbol:** TS `typescript/src/typechat.ts:110-116` (+ program variant `typescript/src/ts/program.ts:223-231`); PY `python/src/typechat/_internal/translator.py:103-115`.
**Signature:** `(request: string) => PromptContent | str` — overridable instance property (TS) / private method (Py).
**Data Shape:** schema fenced with triple BACKTICKS in both; user request fenced with triple DOUBLE-QUOTES (`"""`) in TS but triple SINGLE-quotes (`'''`) in Python.

### Decisive source
```ts
return `You are a service that translates user requests into JSON objects of type "${validator.getTypeName()}" according to the following TypeScript definitions:\n` +
    `\`\`\`\n${validator.getSchemaText()}\`\`\`\n` +
    `The following is a user request:\n` +
    `"""\n${request}\n"""\n` +
    `The following is the user request translated into a JSON object with 2 spaces of indentation and no properties with the value undefined:\n`;
```
```py
The following is a user request:
'''
{intent}
'''
```
**Flow:** preamble sections first, then the generated request section; repair appends assistant(original full response)+user(repair prompt).
**Invariant:** the closing instruction demands "2 spaces of indentation and no properties with the value undefined" — that phrase is why stripNulls exists downstream. The repair prompt differs subtly per language: TS "The JSON object is invalid for the following reason:" (:118-122) vs Py "The ABOVE JSON object is invalid..." (:117-125) — because Python's template renders as one block where the invalid JSON sits above. Program translators override BOTH prompts ("programs represented as JSON", "JSON program object") while reusing the identical translate loop.
**Probe:** `grep -c "'''" python/src/typechat/_internal/translator.py` (=4 = 2 fences × open/close); `grep -c 'no properties with the value undefined' typescript/src/typechat.ts typescript/src/ts/program.ts python/src/typechat/_internal/translator.py` (=1+1+1). Live conversation pins: `python/tests/test_translator.py` snapshots capture full FixedModel conversations incl preamble variants.

## processRequests / process_requests
**Path/Symbol:** TS `typescript/src/interactive/interactive.ts:12-35`; PY `python/src/typechat/_internal/interactive.py:3-37`.
**Signature:** TS `processRequests(interactivePrompt: string, inputFileName: string|undefined, processRequest: (request)=>Promise<void>)`; py async mirror.
**Flow:** FILE mode replays each non-empty line through the callback (TS logs prompt+line first); py SKIPS lines starting `"# "` and uses `filter(str.rstrip, file)`. REPL mode loops until quit/exit (case-insensitive; py strips before comparing), py adds optional readline import + EOFError→newline+break, TS closes the readline interface after break.
**Invariant:** file-mode lines are processed SEQUENTIALLY awaited — examples drive whole test scripts through this path. Quit words never reach the callback.
**Probe:** `grep -c 'startswith("# ")' python/src/typechat/_internal/interactive.py` (=1); `grep -c '"quit"' typescript/src/interactive/interactive.py 2>/dev/null || grep -c "'quit'" python/src/typechat/_internal/interactive.py` (=1 py site). No dedicated unit tests for either loop — coverage caveat: exercised only via examples.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"processRequests interactive input","limit":3}'
```

## Verdict
Adopt the fence asymmetry awareness when diffing prompts across ports (a porter copying TS quotes into Python templates changes model behavior subtly); adapt quit-words/prompt strings to host UX; omit file mode if your host has its own batch driver. Caveat recorded: interactive loops lack direct unit tests at this pin.
