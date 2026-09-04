<!-- capsule-v2 -->
# Formula-reply code-block surgery — how does a chat answer become a suggested ModifyColumn action?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How is the model's Python block extracted/tweaked into an applicable formula while keeping the chat reply consistent?

## completionToResponse builds ModifyColumn from assistanceFormulaTweak; replaceMarkdownCode rewrites the FIRST fenced block in the displayed reply
**Path/Symbol:** `app/server/lib/OpenAIAssistantV1.ts`: `completionToResponse` (:426–447), `replaceMarkdownCode` (:406–411), reply substitution at getAssistance (:152–161).
**Signature:** `replaceMarkdownCode(markdown: string, replaceValue: string): string`.
**Data Shape:** Response: `{suggestedActions: DocAction[], suggestedFormula?, reply?, state}`.

### Decisive source
```ts
function replaceMarkdownCode(markdown: string, replaceValue: string) {
  return markdown.replace(
    /```\w*\n(.*)```/s,                    // FIRST fenced block, DOTALL across lines
    "```python\n" + replaceValue + "\n```",
  );
}
...
const response = await completionToResponse(doc, request, completion);
if (response.suggestedFormula) {
  // Show the tweaked version of the suggested formula ... copied when Apply is clicked.
  response.reply = replaceMarkdownCode(completion, response.suggestedFormula);
} else {
  response.reply = completion;
}
// inside completionToResponse:
const suggestedFormula = await doc.assistanceFormulaTweak(completion) || undefined;
const suggestedActions = suggestedFormula ? [[
  "ModifyColumn", request.context.tableId, request.context.colId, { formula: suggestedFormula },
]] : [];
```

**Flow:** model text → doc-side `assistanceFormulaTweak` normalizes (`rec.A` → `$A`, strips `return`) or rejects invalid formulas (then NO action is offered but the raw reply still shows) → suggested action is a plain ModifyColumn user action the CLIENT applies (server never mutates unbidden) → displayed reply has its code block REPLACED by the tweaked version so copy/paste and Apply agree.
**Invariant:** Reply and suggestion must show the SAME formula or users paste one thing and apply another. The regex `/s` flag spans multi-line bodies; `\w*` tolerates ```python or bare fences; only the FIRST block is swapped because that's where the contract forces the function body. Invalid-formula completions degrade to prose-only replies (no action) rather than erroring.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && sed -n "406,412p" app/server/lib/OpenAIAssistantV1.ts | grep -n "w\|python" | head -3 && sed -n "174,190p" test/server/lib/OpenAIAssistantV1.ts | grep -c "does not suggest"'` → fence-regex lines; test title present (invalid-formula case).
Direct tests: `test/server/lib/OpenAIAssistantV1.ts` :96 "can suggest a formula" (asserts full deepEqual incl. tweaked reply), :174 "does not suggest anything if formula is invalid".

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"completionToResponse assistanceFormulaTweak replaceMarkdownCode ModifyColumn","limit":5,"detail":"ids"}'
```

## Verdict
Adopt apply-vs-display consistency + client-applied action shape; adapt tweak rules to your formula dialect; omit reply rewriting only if you display the raw completion instead (and accept divergence).
