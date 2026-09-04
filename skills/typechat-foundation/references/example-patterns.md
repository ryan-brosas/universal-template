<!-- capsule-v2 -->
# Example-plane patterns — how do real apps compose translators, history, and program dispatch?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** What reusable composition patterns do the examples establish that a porter should replicate before inventing their own?

## Chat-history translator wrapper (healthData)
**Path/Symbol:** `typescript/examples/healthData/src/translator.ts:36-43` (`translate`) + `python/examples/healthData/translator.py:30-34` (`TranslatorWithHistory.translate`) — graph entry_points for both.
**Signature:** wraps a base `TypeChatJsonTranslator` and re-issues `createRequestPrompt` with accumulated conversation turns prepended as preamble sections.
**Flow:** keep rolling message list → each request rebuilds the prompt with history sections before the schema section → model sees prior Q/A pairs.
**Invariant:** history is threaded through the PUBLIC `promptPreamble` hook — no core changes; this is the sanctioned extension surface (TS interface docs :28-33 say "An application can assign a new function to provide a different prompt").

## Program dispatch host (math / multiSchema)
**Path/Symbol:** `python/examples/math/program.py:112-116` (`TypeChatProgramValidator.validate_object` overriding the stock validator) + agent factory pair in `typescript/examples/multiSchema/src/agent.ts` (`createJsonMathAgent`/`createJsonPrintAgent`, graph entry points) with `_handleMessage`.
**Flow:** translate request → if result is a Program, `evaluateJsonProgram(program, onCall)` where onCall whitelists function names against the API and returns promises → feed results back into chat.
**Invariant:** the validator-subclass seam exists precisely so program hosts can validate `{"@steps":...}` JSON against the Program type while keeping the standard translator loop; multiSchema shows TWO named schemas sharing one validator object (the Zod map pattern).

## Coffee-shop schema idioms
**Path/Symbol:** `python/tests/test_coffeeshop.py` + `typescript/examples/coffeeShop/src/schema.ts` (graph: examples package, 369 nodes).
**Data Shape:** discriminated union via `type: Literal["UnknownText"|"Caffeine"|...]` tag fields; `NotRequired["OptionQuantity"]`; `Annotated[str, Doc("The text that wasn't understood")]` doc-comments surfacing in printed schema.
**Invariant:** UnknownText is the ESCAPE HATCH member — schemas give the model a legitimate way to say "didn't understand", which keeps validation success meaningful. The deprecated twin (`coffeeshop_deprecated.py`) proves List[X]/Union/X[Y] legacy generics convert identically.
**Probe:** live suite pins example parity: coffeeshop snapshot passes at 3.12 this run; `grep -c 'UnknownText' python/tests/test_coffeeshop.py` (=2 class+usage).
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"createHealthDataTranslator createJsonPrintAgent","limit":5}'
// entry_points list names both families directly
```

## Verdict
Adopt the preamble-as-history and validator-subclass seams instead of forking the core; adapt UnknownText-style escape members to your domain vocabulary; omit example app scaffolding (UI, file IO) entirely.
