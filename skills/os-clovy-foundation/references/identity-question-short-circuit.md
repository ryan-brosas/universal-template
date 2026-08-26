<!-- capsule-v2 -->
# Identity question short-circuit — which inputs must answer without any model call?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter branding an assistant on top of third-party models needs a deterministic gate that answers "who are you?" locally, cheaply, and without leaking the upstream vendor.

## clovyIdentityResult gate
**Path/Symbol:** `agent-runtime/src/identity.ts:clovyIdentityResult` (:44-68), `isGeneralIdentityQuestion` (:70-82). Call sites: `service.ts:startAcceptedRun` :109-119 (before compaction!) and `sdk-engine.ts:start` :135-140.
**Signature:** `clovyIdentityResult(params: RunStartParams): EngineResult | undefined`.
**Data Shape:** Returns a full `EngineResult`: fixed reply text, history = prior history + appended user+assistant pair, `usage:{}`, `interruptions:[]`.

### Decisive source
```ts
if ((params.attachments?.length ?? 0) > 0 || !isGeneralIdentityQuestion(params.input))
  return undefined;
// normalization: NFKC → lowercase → strip ' and ’ → tokenize [a-z0-9]+
// trim LEADING fillers (hi/hello/hey/um/ok/so/well/yo/clovy/june/please/there)
// trim TRAILING fillers (clovy/june/please)
// exact match against 17 phrasings: "who are you", "what r u",
//   "are you chatgpt", "what should i call you", "who am i talking to", ...
```

**Flow:** Checked TWICE by design — in the service before compaction (so a 7k-token history around "who r u?" never triggers summarization; service.test asserts `engine.summaryInputs.length === 0`) and again at engine entry. On hit: emit `run.started` → `message.delta` with the fixed reply → settle completes normally; no model request, no tool invoke (`sdk-tool-loop.test` asserts `hostCalls === 0`).
**Invariant:** The gate is EXACT-MATCH after normalization, not substring/regex — "What model are you using?" deliberately stays on the model route (test: "keeps explicit model questions on the model route"); attachments always opt out; the reply never names the upstream model (identity instructions separately tell the model to call provider choice an implementation detail).
**Probe:** `agent-runtime/test/sdk-tool-loop.test.ts` "answers general identity questions as Clovy without calling a model" (:16-57) and `agent-runtime/test/service.test.ts` "answers identity before history compaction or model inference" (:45-77). sdk-tool-loop suite runner-blocked at pin; service-side assertions mirrored in the blocked suite too — both read directly.

## Get live surrounding code
**Retrieve:** executed at pin (top hits = target):
```
search_graph({ project:"os-clovy", query:"identity question reply without model call", file_pattern:"agent-runtime/*" })
→ src.identity.isGeneralIdentityQuestion Function identity.ts 70-82  (rank 1)
   src.identity.clovyIdentityResult Function identity.ts 44-68
```

## Verdict
Adopt exact-match-after-normalization with filler trimming, the attachments opt-out, and the double placement (service pre-compaction AND engine entry). Adapt the phrase list and reply string to your brand; add localized phrasings as additional set members rather than loosening to substrings. Omit nothing structural — loosening the match is the classic wrong port (it hijacks real prompts).
