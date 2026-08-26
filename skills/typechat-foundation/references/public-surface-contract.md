<!-- capsule-v2 -->
# Public surface contract — what does each port actually export, and where must porters reach into privates?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** Which symbols are public API in each language port, and which load-bearing pieces are deliberately private?

## Python allow-list vs TS wildcard barrels
**Path/Symbol:** `python/src/typechat/__init__.py:5-25` (13-name `__all__`); `typescript/src/index.ts:1-3` (three `export *`); subpath entries `typescript/src/ts/index.ts`, `typescript/src/zod/index.ts`.
**Signature:** py re-exports `TypeChatLanguageModel, TypeChatJsonTranslator, TypeChatValidator, Success, Failure, Result, python_type_to_typescript_schema, PromptSection, create_language_model, create_openai_language_model, create_azure_openai_language_model, process_requests`.

### Decisive source
```ts
export * from './result';
export * from './model';
export * from './typechat';
```
**Flow:** TS root barrel exports result+model+typechat ONLY — the compiler-validator plane (`typechat/ts`) and zod plane (`typechat/zod`) live behind package subpaths that pull in heavy deps lazily per consumer. Python flattens everything into ONE namespace with an explicit allow-list.
**Invariant:** the asymmetry that bites: Python's allow-list OMITS the `HttpxLanguageModel` class itself — only factory functions and the Protocol are public. Upstream's own test suite reaches into the private module (`from typechat._internal.model import HttpxLanguageModel`, tests/test_model.py:12) to subclass it and swap `_async_client` for a MockTransport client. So in Python the model class + its client attribute are de-facto extension points that are NOT committed API; in TS every validator factory is importable but split across subpaths. A porter who "fixes" the private import breaks mockability; one who treats the py allow-list as exhaustive misses that `HttpxLanguageModel` even exists. Also note `_internal/interactive.py`'s `process_requests` IS public while its TS twin ships from `typechat/interactive` (not the root barrel).
**Probe:** executed pins: `grep 'HttpxLanguageModel' python/src/typechat/__init__.py`=0 (absence — the omission is real); `grep 'export \*' typescript/src/index.ts`=3 (:1-3). Live cross-check: tests/test_model.py imports via `typechat._internal.model`.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"typechat package exports init","limit":5}'
// BM25 returns only ts_conversion/__init__ symbols — the ROOT __init__.py carries no graph nodes; adjudicate from direct read (coverage no_recorded_issue).
```

## Verdict
Adopt each port's surface discipline as-is: explicit allow-list (py) vs dependency-lumping subpaths (ts) — they encode real dependency economics, not style; adapt by adding your own sanctioned extension seam if you need mockable transports; omit any promise that private-path imports stay stable across versions. Coverage caveat: root __init__ files are invisible to graph symbol search; this capsule rests on direct reads plus coverage checks (no_recorded_issue ×2).
