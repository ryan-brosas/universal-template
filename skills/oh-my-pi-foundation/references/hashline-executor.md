<!-- capsule-v2 -->
# Hashline executor — how does a token stream become ordered, lenient edits without trusting the model?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you turn a token stream of model-authored patch lines into a flat, ordered edit list while repairing reflexive mistakes instead of failing?

## Token-driven state machine with deferred flush
**Path/Symbol:** `packages/hashline/src/parser.ts:Executor` (207–788), `#flushPending` (705–786), `parsePatch` (795–800), `parsePatchStreaming` (802–808), `InvalidAbsoluteRangeError` (38+).
**Signature:** `feed(token: Token): void`; `end(): { edits, fileOp?, warnings }`; `endStreaming()` — same shape but leaves trailing pending hunks unflushed.
**Data Shape:** `Pending { target: BlockTarget, lineNum, payloads: PayloadRow[], hadColon, deferredBlanks }` → flat `Edit[]` each carrying monotonic `index` + source `lineNum`.

### Decisive source
```ts
case "raw":
  if (this.#pending === undefined && isSkippableCommentLine(token.text)) {
    this.#skippableComments.push({ text: token.text, lineNum }); return; // buffer, don't commit
  }
  this.#consumePendingSkippableComments(); ...
// #flushPending — one ladder decides every op's meaning:
if (target.kind === "replace") {
  if (target.register !== undefined) return void this.#pushPaste({kind:"span", ...}, target.register, lineNum);
  if (payloads.length === 0) {
    if (!hadColon) throw new Error(`line ${lineNum}: ${COLONLESS_SPAN_PUT}`);
    this.#pushDeleteRange(target.range, lineNum);            // empty body ⇒ auto-CUT
    if (!this.#warnings.includes(EMPTY_PUT_AUTO_CUT_WARNING)) this.#warnings.push(EMPTY_PUT_AUTO_CUT_WARNING);
    return;
  }
  const cursor = { kind: "before_anchor", anchor: { ...target.range.start } };
  this.#emitPayloadRows(cursor, payloads, lineNum, "replacement");  // insert BEFORE delete ⇒ stable anchors
  this.#pushDeleteRange(target.range, lineNum);
}
```

**Flow:** tokens (`header|blank|payload-literal|raw|op-block|envelope-*|abort`) drive a single pending-hunk buffer → header/op flushes the previous hunk → flush resolves `-` bullet rows, strips uniform bare prefixes, then dispatches by target kind (`cut`, `cut_block`, `replace`, `block`, `insert_after_block`, gap cursors bof/eof/before/after) → skippable comment lines are buffered and only committed when real content follows (discarded at envelope end).
**Invariant:** edits are emitted in author order with strictly increasing `index` (the applier relies on it for deterministic replay); interior blank rows are payload, trailing blanks are layout and dropped; `:` exclusively promises body rows so ops that take no body reject or warn on it; range expansion is capped (`MAX_EXPANDED_RANGE_LINES = 100_000`) before file size is known.
**Probe:** direct `packages/hashline/test/format-v2.test.ts:54` empty-PUT-becomes-deletion warning; `:71/:78` auto-piped bare rows (incl. echoed read-prefix stripping); `:140/:145` streaming semantics — trailing pending empty replace is NOT flushed, a CUT IS flushed when the next hunk starts.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(Executor|parsePatchStreaming)$", limit: 5, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.hashline.src.parser.Executor" });
```

## Verdict
Adopt single-pending-buffer parsing with insert-before-delete replacement ordering, monotonic edit indices, and warning-grade repair of model reflexes (auto-pipe, auto-cut, colon stripping); adapt token kinds and message strings to your patch grammar; omit streaming mode unless your host consumes partial patches. Coverage caveat: tests excluded from graph index by design; probes are source-grounded from on-disk test files.
