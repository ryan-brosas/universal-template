<!-- capsule-v2 -->
# Verifier Config Helpers & Error Taxonomy — SDK-side config objects vs server-side execution

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** What do provider helpers like claude_verifier actually DO (and not do), and how are AwaitVerify errors shaped?

## Thin config factories; errors follow what→why→fix→docs with subclassable base
**Path/Symbol:** `packages/python/awaithumans/verifiers/{claude,openai,gemini,azure_openai}.py` — e.g. `claude_verifier` (:24-48); `awaithumans/errors.py` base `AwaitHumansError` (ServiceError class-attribute taxonomy: code/message/hint/docs_url — see bootstrap-token-error-taxonomy capsule for the handler envelope); `awaitverify/errors.py` — `VerifyError(AwaitHumansError)` (:18) + four concrete subclasses (:22-98).
**Signature:** `claude_verifier(instructions: str, *, model="claude-sonnet-4-20250514", max_attempts=3, api_key_env="ANTHROPIC_API_KEY") -> VerifierConfig`.
**Data Shape:** every helper returns a plain VerifierConfig — NO client, NO network. Execution happens SERVER-side ("This helper just creates the config that tells the server what to do").

### Decisive source
```python
class VerifyDocumentTooLargeError(VerifyError):
    def __init__(self, page_count: int):
        super().__init__(
            code="VERIFY_DOCUMENT_TOO_LARGE",
            message=f"This document has {page_count} pages. AwaitVerify supports up to {AWAITVERIFY_MAX_PAGES}...",
            hint=("Split the document into smaller chunks client-side ... contact us about a Scale tier"),
            docs_url=f"{_VERIFY_DOCS_URL}/limits",
        )
```
`VerifyDepsMissingError(missing)` fires from LAZY vendor imports (flow-b-extraction-dispatch covers the import ladder) so the core SDK stays httpx+pydantic only.

**Flow:** caller writes `verifier=claude_verifier("Check consistency", max_attempts=3)` → config rides to server → verifier-loop capsule owns execution/attempts → failures inside verify_document surface as VerifyError subclasses catchable with one `except VerifyError` while carrying actionable hint + docs link.
**Invariant:** config-vs-execution split is the trust contract (API keys read SERVER-side via api_key_env name — see secret-lookup-funnel); error subclasses add NO fields beyond the base taxonomy.
**Probe:** graph/Class pins + `packages/python/tests/test_sdk_typed_errors.py` (typed-error parity across the family) + construction tests in `tests/awaitverify/test_client.py::TestAwaitHumansClient`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "claude_verifier VerifierConfig VerifyError docs_url hint", limit: 5 });
```

## Verdict
Adopt the thin-config-factory pattern and the what→why→fix→docs error shape; adapt provider/model defaults to your stack; omit extra provider twins freely — they're 48-line clones differing only in defaults.
