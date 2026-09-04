<!-- capsule-v2 -->
# Typed Error Taxonomy & Cross-Language Parity — how do two SDKs raise identical failures from one wire contract?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What must an error class carry so users write transport-specific recovery without string matching — and how is parity kept when one language adds an error?

## what→why→fix→docs errors keyed by stable codes
**Path/Symbol:** `packages/python/awaithumans/errors.py` whole (:9–177); TS twin `packages/typescript-sdk/src/errors.ts`; constants shared via each SDK's constants module.
**Signature:** `AwaitHumansError(code, message, hint, docs_url)` — full_message = `message\n\nhint\n\nDocs: {url}`; TS mirrors field-for-field (`readonly code/hint/docsUrl`, same joined message).
**Data Shape:** 11 concrete classes: TimeoutRangeError, TaskTimeoutError, SchemaValidationError(field), TaskCreateError(status, body[:500]), PollError, ServerUnreachableError(url, cause), TaskNotFoundError, TaskCancelledError, TaskAlreadyTerminalError(task_id, status), VerificationExhaustedError(task, attempts), MarketplaceNotAvailableError.

### Decisive source
```python
# These mirror the TypeScript SDK's error classes one-for-one ...
# Cross-language parity is a CLAUDE.md §7 hard rule — Python users
# `except TaskNotFoundError`, TypeScript users `catch (e instanceof
# TaskNotFoundError)`, both see the same wire `code` field, both can
# write transport-specific recovery without conditionals on string codes.

class TaskTimeoutError(AwaitHumansError):
    def __init__(self, task: str, timeout_seconds: int) -> None:
        super().__init__(
            code="TIMEOUT_EXCEEDED",
            message=f'Task "{task}" timed out after {timeout_seconds} seconds.',
            hint=("No human completed the task. Check:\n"
                  "  1. Is your notification channel configured? ...\n"
                  "  3. Consider increasing timeout_seconds if humans need more time."),
            docs_url=f"{DOCS_TROUBLESHOOTING_URL}#timeout")
```

**Flow:** validation errors raise BEFORE any network call (range gate 60s…30d with the "for sub-minute timeouts use a coroutine, not HITL" hint); connection-level failures convert httpx ConnectError/ConnectTimeout into typed ServerUnreachableError; every poll/create status path maps to its class; server bodies are truncated to 500 chars inside hints (never echo unbounded responses).
**Invariant:** the `code` string is the cross-language join key — never rename without bumping both SDKs; hints are actionable checklists, not stack traces; docs_url anchors into troubleshooting sections. Marketplace stub exists in BOTH languages purely to claim the name and teach the roadmap alternative.
**Probe:** `tests/test_sdk_typed_errors.py`; TS behavior pins `tests/await-human.test.ts` (:91–121 rejects, :415–445 terminal throws).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "AwaitHumansError typed error code hint", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-field error shape, stable-code parity discipline, pre-network validation gates, and body truncation in hints. Adapt class names/codes to your product. Omit the reserved Phase-4 stubs unless you also need name-claiming.
