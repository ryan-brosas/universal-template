<!-- capsule-v2 -->
# Progress notifications — what does the `progressToken` opt-in contract require of senders, and which monotonic/rate limits keep streams sane?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6`; Codebase Memory `modelcontextprotocol`. **Question:** When may a server emit `notifications/progress`, what shape and ordering must the values obey, and when must they stop?

## Client opts in via request `_meta.progressToken`; server MAY notify at will
**Path/Symbol:** `docs/specification/2026-07-28/basic/patterns/progress.mdx` (whole page, 90L: token placement :13–31; notification fields :33–56; behavior requirements :58–67; sequence diagram :69–84; implementation notes :86–90).

**Signature:** request carries `"params": { "_meta": { "progressToken": "abc123" } }` → notifications `{ method: "notifications/progress", params: { progressToken, progress, total?, message? } }`.

**Data Shape:** `progressToken` string or integer, client-chosen, MUST be unique across all ACTIVE requests; `progress` and `total` MAY be floating point; `message` optional human-readable.

### Decisive source
```md
# progress.mdx:53-56 + 60-67 (the monotonic + discretionary rules)
- The `progress` value **MUST** increase with each notification, even if the total is
  unknown.
- The `progress` and the `total` values **MAY** be floating point.
- The `message` field **SHOULD** provide relevant human readable progress information.
...
1. Progress notifications **MUST** only reference tokens that:
   - Were provided in an active request
   - Are associated with an in-progress operation
2. Servers receiving a request with a progress token **MAY**:
   - Choose not to send any progress notifications
   - Send notifications at whatever frequency they deem appropriate
   - Omit the total value if unknown
```

**Flow:** client embeds a unique token in the request `_meta` → server MAY emit zero or many notifications referencing that exact token while work is in flight (`0.2/1.0 → 0.6/1.0 → 1.0/1.0`) → final method response arrives AFTER the last progress notification; notifications MUST STOP once the operation completes.

**Invariants:**
1. **Opt-in is absolute**: no token in the request ⇒ no progress notifications, ever; tokens from other/finished requests MUST NOT be referenced.
2. **Monotonicity without a total**: each notification's `progress` exceeds the previous even when `total` is omitted — a porter who resets progress on phase changes violates the wire contract.
3. **Rate limiting is a SHOULD on both parties** (flood prevention), and completion silences the stream permanently for that token.
4. Tokens ride the SAME per-request `_meta` grammar as all modern-era metadata (`meta-key-grammar.md`); they are not a separate channel.

**Probe:** reference-server behavioral pin: `src/everything/__tests__/tools.test.ts:328–366` (`trigger-long-running-operation` — "should send progress notifications when progressToken provided") demonstrates the token-gated emission end-to-end over the SDK; spec page itself has no runtime tests (docs-only caveat recorded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "ProgressNotification|notifications/progress", limit: 10 });
```

## Verdict
Adopt token-gated emission, strictly increasing progress values, optional totals with human messages, and stop-on-completion; adapt cadence and float scaling to your operation; pair with `cancellation-pattern.md` (progress MAY reset timeout clocks there) and `progress-notifications.md` (the reference-server emission mechanics).
