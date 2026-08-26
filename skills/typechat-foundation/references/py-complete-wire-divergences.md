<!-- capsule-v2 -->
# Python complete() wire divergences — where does the httpx port break parity with the TS failure contract?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** If I port the TS "malformed-200 is an immediate Failure" contract onto the Python client, what silently changes — and vice versa?

## Shape errors are RETRIED in Python, terminal in TS
**Path/Symbol:** `python/src/typechat/_internal/model.py:97-109` vs `typescript/src/model.ts` OK-path (see model-fetch-loop capsule).
**Signature:** same `complete()` envelope; divergence is in exception topology, not code shape.

### Decisive source
```py
json_result = cast(
    dict[Literal["choices"], list[dict[Literal["message"], PromptSection]]],
    json.loads(raw)
)
return Success(json_result["choices"][0]["message"]["content"] or "")
...
except _ResponseTooLargeError as e:
    return Failure(str(e))
except Exception as e:
    if retry_count >= self.max_retry_attempts:
        return Failure(str(e) or f"{repr(e)} raised from within internal TypeChat language model.")
```
**Flow:** `json.loads` + `["choices"][0]["message"]["content"]` all sit INSIDE the try whose generic handler retries. A 200 with a JSON body missing `choices`, or with `choices: []`, raises KeyError/IndexError → sleeps → resends up to `max_retry_attempts`. TS instead type-checks `typeof content === "string"` OUTSIDE any retry and returns "REST API unexpected response format" immediately.
**Invariant:** three compounding divergences a cross-port host must reconcile: (1) malformed-200 costs Python `max_retry_attempts+1` network calls and only then fails, with the raw KeyError text as the Failure message; (2) `"content"] or ""` coerces `null`/`""` content to `Success("")` while TS rejects null content outright; (3) the bare `cast(...)` asserts a shape nothing enforces — the type lie is what routes shape bugs into the retry path. The ONLY non-retryable Python exceptions are `_ResponseTooLargeError` (:105) and non-transient statuses.
**Probe:** no upstream test pins these. EXECUTED live this pass: full fleet enumeration via repo-owned `pytest -vv` from `python/` at pin 83caa124 (Python 3.14.7) → **22 passed, 17 snapshots**, and the collected item list confirms the Python side has ZERO malformed-body/header/status tests (test_model.py contributes only its 4 size-limit cases; unlike TS model.test.mjs :161-199). Static pins executed: `grep '\["content"\] or ""' model.py`=1 @101; `grep 'except Exception' model.py`=2 @107,152.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"HttpxLanguageModel complete transient retry","limit":5}'
// rank1 complete :70-112 — read the try/except nesting directly; the graph shows ranges, not the topology trap.
```

## Header composition + provider factories
**Path/Symbol:** `model.py:71-74` (spread order), `:193-210` (`create_openai_language_model`), `:212-226` (`create_azure_openai_language_model`).
**Signature:** `headers = {"Content-Type": "application/json", **self.headers}`.
### Decisive source
```py
headers = {
    # Needed when using managed identity
    "Authorization": f"Bearer {api_key}",
    # Needed when using regular API key
    "api-key": api_key,
}
```
**Flow:** user headers spread AFTER Content-Type so a custom Content-Type wins; Azure sends BOTH bearer and api-key forms on every request (managed identity vs regular key); OpenAI always sends `OpenAI-Organization` even when org defaults to `""` (:205).
**Invariant:** empty-org header is observable wire behavior some gateways log or reject; dual Azure auth headers are intentional redundancy, not a bug. TS composes equivalent headers in `createLanguageModel` env routing but org var name differs (`OPENAI_ORG` py vs `OPENAI_ORGANIZATION` ts).
**Probe:** executed pins: `OpenAI-Organization`@205, `"api-key"`@224 (1 site each). No upstream header assertions exist.
**Verdict placement:** see Verdict below.

## Verdict
Adopt the TS contract (shape error ⇒ immediate typed Failure, string-typed content) when porting fresh hosts; adopt Python's exact topology ONLY when reproducing its behavior matters (retry-count-sensitive cost models, message text). Adapt header maps per provider but keep user-header-overrides-default ordering; omit the empty-org header unless matching upstream byte-for-byte. Coverage caveat: every claim here is source-pinned with zero upstream test cover on the Python side.
