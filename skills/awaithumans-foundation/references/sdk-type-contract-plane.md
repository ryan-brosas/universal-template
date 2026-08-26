<!-- capsule-v2 -->
# SDK Type Contract Plane — TaskStatus ladder, AssignTo union, VerifierConfig envelope

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** Which cross-runtime type contracts must stay byte-stable between Python SDK, TS adapters, server, and human-facing UIs?

## types/{task,routing,verification}.py — the vocabulary every plane shares
**Path/Symbol:** `packages/python/awaithumans/types/task.py` — `TaskStatus` 11-member str-Enum (:15-26), `AwaitHumanOptions` (:29-58), `TaskRecord` (:61-79); `types/routing.py` — `AssignTo` union + `HumanIdentity` (:10-42); `types/verification.py` — `VerifierConfig/VerifierResult/VerificationContext` (:10-48).
**Signature:** `AwaitHumanOptions.timeout_seconds: int = Field(ge=60, le=2_592_000)` (1 min..30 days); `VerifierConfig.max_attempts: int = Field(default=3, ge=1, le=10)`.
**Data Shape:** AssignTo = `str(email) | list[str](first-to-claim) | PoolAssignment | RoleAssignment(access_level?) | UserAssignment | MarketplaceAssignment(Literal[True], Phase-3 reserved)`.

### Decisive source
```python
class TaskStatus(str, enum.Enum):
    CREATED = "created"; NOTIFIED = "notified"; ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"; SUBMITTED = "submitted"; VERIFIED = "verified"
    COMPLETED = "completed"; REJECTED = "rejected"; TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"; VERIFICATION_EXHAUSTED = "verification_exhausted"
```
idempotency_key docstring pins the retry contract: same key returns the STORED response or terminal-status error even after restart — fresh task requires a DISTINCT key ('":retry-1"').

**Flow:** SDK caller constructs AwaitHumanOptions → wire → server persists status ladder CREATED→NOTIFIED→ASSIGNED→IN_PROGRESS→SUBMITTED→(VERIFIED|REJECTED*)→COMPLETED / TIMED_OUT / CANCELLED / VERIFICATION_EXHAUSTED → TaskRecord returns response + verifier_result. Routing union resolves server-side (routing-and-assignment capsule); VerifierConfig rides to the SERVER where execution happens ("passed to the server, executed server-side").
**Invariant:** these are the shared nouns across every capsule boundary — statuses are compared BY VALUE string across TS/Python; terminal set lives in utils/constants.TERMINAL_STATUSES_SET consumed by stats and guards.
**Probe:** graph Class nodes pin all three modules line-exact; behavioral: stats completion_rate sums TERMINAL_STATUSES_SET values against TaskStatus.COMPLETED (see stats capsule); TS mirror tests exist under packages/typescript-sdk/tests/.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "TaskStatus AwaitHumanOptions AssignTo VerifierConfig", limit: 6 });
```

## Verdict
Adopt the status vocabulary, timeout bounds, and AssignTo union wholesale if porting the task model; adapt member sets carefully — every consumer (guards, stats, TS adapters, UI) switches on these exact strings.
