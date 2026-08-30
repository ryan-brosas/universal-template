<!-- capsule-v2 -->
# Auto-close ladder — when does a poll close itself, reopen, and why must manual closes stick?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** What is the full open/closed lifecycle — cron auto-close, the "reopen on new future options" rule, and the closedReason values that decide which closes are reversible?

## autoClosePolls + optionEndsInFuture + modify's reopen gate
**Path/Symbol:** `apps/web/src/features/poll/mutations.ts:autoClosePolls` (lines 294–311); `apps/web/src/trpc/routers/polls.ts:optionEndsInFuture` (lines 41–46) and `modify` reopen block (lines 380–389, 439); trigger `apps/web/src/app/api/house-keeping/[...method]/route.ts:/auto-close-polls` (lines 61–75).
**Signature:** `autoClosePolls(): Promise<number>` (row count); `optionEndsInFuture(option: { startTime: Date; duration: number }): boolean`.
**Data Shape:** `closed_reason ∈ {"auto","manual"} | null`; status ∈ open|closed|scheduled|canceled.

### Decisive source
```sql
UPDATE polls p
SET status = 'closed', closed_reason = 'auto'
WHERE p.status = 'open'
  AND p.deleted = false
  AND EXISTS (SELECT 1 FROM options o WHERE o.poll_id = p.id)
  AND NOT EXISTS (
    SELECT 1 FROM options o
    WHERE o.poll_id = p.id
      AND o.start_time + (CASE WHEN o.duration_minutes = 0
            THEN interval '24 hours'
            ELSE make_interval(mins => o.duration_minutes) END) > (now() AT TIME ZONE 'UTC')
  )
```
```ts
// Mirrors the auto-close house-keeping task: an option ends at
// start + duration, with all-day options (duration 0) treated as 24h.
const optionEndsInFuture = (option) =>
  dayjs(option.startTime)
    .add(option.duration === 0 ? 24 * 60 : option.duration, "minute")
    .isAfter(dayjs());
// Reopen an auto-closed poll when new future dates are added. Manually
// closed polls stay closed — that was the organizer's decision.
if (newOptions.some(optionEndsInFuture)) {
  const poll = await tx.poll.findUnique({ where: { id: pollId }, select: { status: true, closedReason: true } });
  reopen = poll?.status === "closed" && poll.closedReason === "auto";
}
```

**Flow:** cron GET `/api/house-keeping/auto-close-polls` (bearer CRON_SECRET) → SQL flips every open poll with no still-future option to closed+auto → organizer later edits options; if any NEW option ends in the future AND closedReason was 'auto', the same transaction reopens (`status:"open", closedReason:null`); a manual close never reopens. `closePoll` (mutations.ts:121–150) is idempotent: an already-closed poll returns unchanged WITHOUT overwriting its closedReason (so cron-closed stays auto).
**Invariant:** all-day = 24h must agree in BOTH the SQL arm and the TS mirror or reopen/close disagree at day boundaries; auto-close deliberately does NOT touch `updated_at` so closing doesn't reset the inactivity clock that delete-inactive-polls keys off; only `open` polls are closed (scheduled/canceled untouched).
**Probe:** `apps/web/src/features/poll/mutations.test.ts` closePoll suite ("is idempotent and does not update an already-closed poll", :184).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "autoClosePolls closed_reason", limit: 5 });
```

## Verdict
Adopt the three-state closedReason ladder verbatim — it is the reusable contract; adapt the raw-SQL dialect to your DB (Prisma can't express start+duration); omit the Hono route shell if you have your own scheduler.
