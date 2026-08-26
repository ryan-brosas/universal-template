<!-- capsule-v2 -->
# UI tool-invocation state union — how does one discriminated union make illegal tool-call states unrepresentable while still surviving hostile JSON from the wire?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** Which fields exist in which tool-invocation state, and what must a porter replicate so replayed history cannot smuggle outputs into streaming calls?

## UIMessage part taxonomy & UIToolInvocation
**Path/Symbol:** `packages/ai/src/ui/ui-messages.ts` whole file (640L): `UIMessage` (:44-75), `UIMessagePart` union (:77-91), `TextUIPart.state 'streaming'|'done'` (:107), `CustomContentUIPart.kind` template-literal `` `${string}.${string}` `` (:118-130), `FileUIPart.mediaType` wildcard-normalization doc (:189-200), `providerReference` precedence doc (:213-218), `ReasoningFileUIPart` (:229-249), `UIToolInvocation` 7-state union (:284-387), `ToolUIPart` = ValueOf over tool names prefixed `tool-${NAME}` (:389-393), `DynamicToolUIPart` mirror with `toolName` field (:395-504).
**Signature:** type-level only; runtime surface is the guard family: `isDataUIPart` (:273-277, `.startsWith('data-')`), `isStaticToolUIPart` (:556-560, `.startsWith('tool-')`), `isDynamicToolUIPart` (:567-571), `isToolUIPart = static || dynamic` (:580-584), `getStaticToolName` (`part.type.split('-').slice(1).join('-')`, :591-595), `getToolName` (:603-607), deprecated alias `getToolOrDynamicToolName = getToolName` (:612).

### Decisive source
```ts
// ui-messages.ts:296-311 — every variant re-lists ALL cross-state keys as
// `never` so assignment/excess checks kill wrong-state fields:
| {
    state: 'input-streaming';
    input?: DeepPartial<asUITool<TOOL>['input']> | undefined;
    output?: never; errorText?: never; approval?: never;   // <-- never-gated
    callProviderMetadata?: ProviderMetadata;
  }
// :341-356 output-available is the ONLY variant with a real `output`
// and an optional approval whose approved is narrowed to literal true:
| { state: 'output-available';
    input: ...; output: ...;
    preliminary?: boolean;
    approval?: { id: string; approved: true; reason?; isAutomatic?; signature? }; }
// :373-386 output-denied carries approved:false — the denial lives in
// approval.approved, not in errorText:
| { state: 'output-denied'; input: ...; approval: { id: string; approved: false; ... } }
```

**Flow:** static tools are typed through mapped-key parts (`type: 'tool-${NAME}'`); dynamic tools (runtime-discovered) carry the name in a `toolName` field under the literal `'dynamic-tool'` type — both share the identical 7-state machine: `input-streaming → input-available → (approval-requested ⇄ approval-responded)? → output-available | output-error | output-denied`. The three terminal states embed which approval decision produced them: `output-available`/`output-error` may carry `approval {approved: true}` (auto or manual approve), `output-denied` always carries `{approved: false}`.
**Invariant:** state is the ONLY discriminator that decides which fields are meaningful — a porter who models output as optional on one flat interface lets `input-streaming` parts carry outputs after replay, which then double-render in UI and duplicate results on model conversion. `getStaticToolName` must split-then-JOIN because tool names themselves contain dashes (`'tool-get-location'` ⇒ `'get-location'`; naive `[1]` indexing truncates). The `mediaType` field accepts top-level IANA segments (`image`) with `image/*` normalized equivalent — providers resolve via provider-utils helpers. FileUIPart `providerReference`, when present, takes precedence over `url` in model messages (upload-flow contract). Direct test suite is tiny by design (`ui-messages.test.ts`:84L — getStaticToolName dash case :21-31, custom/data guards); the union's behavior is pinned downstream by validate-ui-messages + reducer suites.

**Probe:** `bash -c "grep -c \"it('\" /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui/ui-messages.test.ts"` → 7 tests across three describes (getStaticToolName ×2 incl. dash case, isCustomContentUIPart ×3, isDataUIPart ×2); `bash -c "sed -n '21,31p' /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui/ui-messages.test.ts | grep -c 'get-location'"` → 2 (test title + expectation).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "UIToolInvocation ToolUIPart getStaticToolName isToolUIPart DynamicToolUIPart", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the 7-state discriminated union with never-gated cross-state fields, the static-prefix vs dynamic-field duality, and split-join name extraction verbatim. Adapt part names/media-type resolution to your schema. Omit the deprecated alias only if you control all call sites.
