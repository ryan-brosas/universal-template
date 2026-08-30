<!-- capsule-v2 -->
# Operation log with check-before-act dedup — how does a stateless agent avoid repeating irreversible actions across sessions?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the exact dedup key and exit-code contract that lets an LLM agent (via Bash) never like/follow/reply to the same URL twice?

## Append-only JSONL-style log; exit-code protocol for the agent loop
**Path/Symbol:** `scripts/log-operation.ts`:`add`/`check`/`recent`/`summary` commands (`:86-175`), `Operation` shape (`:40-48`).
**Signature:** CLI: `add --platform <p> --action <a> --url <u> --status <s> [--device <d>] [--note <n>]`; `check --platform <p> --action <a> --url <u>` (exit 0 = done, 1 = not done); `recent [--limit N]`; `summary [--days D]`.
**Data Shape:** `{ version, description, operations: Operation[] }`; `Operation { ts: ISO, platform, action, url, status: success|failed|skipped|restricted, device?, note? }`. Path override via `LOCO_OP_LOG_PATH` (tests/doctor isolation).

### Decisive source
```ts
// check — the dedup predicate
const found = log.operations.find(
  op => op.platform === platform && op.action === action && op.url === url && op.status === 'success'
)
if (found) { console.log(JSON.stringify({ done: true, operation: found })); process.exit(0) }
else       { console.log(JSON.stringify({ done: false }));                   process.exit(1) }
```
and the prompt-side contract (`src/constants/prompts.ts:306`):
```
Before each action, use: bun run scripts/log-operation.ts check --platform <p> --action <a> --url <url>.
After each successful action, log it with: ... add ... --status success [--note <context>]
```

**Flow:** agent runs `check` before every action → exit 0 ⇒ skip silently; exit 1 ⇒ proceed → after success run `add`, which mkdir-creates the gitignored parent dir on first write so a fresh clone doesn't ENOENT → `summary` filters to status==='success' within the window and emits per-platform "already-acted URLs" lists injected into the system prompt.
**Invariant:** The dedup key is exactly `(platform, action, url)` against SUCCESS entries only — failures don't block retries. `device` is provenance only and deliberately NOT part of the key ("a like is account-level": the same URL liked from desktop is still done). The whole protocol is exit-code-based so the agent needs no JSON parsing to comply.
**Probe:** `scripts/log-operation.test.ts` — `add --device records device; check dedups by url (device-agnostic)` (:9): asserts saved `.device === 'ios'` while `check` without `--device` still exits 0. Coverage caveat: this test spawns the script via Bun (`process.execPath`) and is blocked on hosts without Bun.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "log-operation check dedup operation", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the (platform, action, url)-against-success dedup key, the exit-code check/add protocol, first-write dir creation, and the summary-to-prompt injection. Adapt action vocabularies and storage (swap JSON file for SQLite at scale). Omit nothing in the key semantics — including `device` in the key is the classic wrong port.
