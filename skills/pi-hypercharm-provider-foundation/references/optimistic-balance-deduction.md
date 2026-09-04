<!-- capsule-v2 -->
# Optimistic balance deduction between polls — how does the footer balance tick down per turn without any extra API calls?

**Source:** pi-hypercharm-provider MIT `main@4520704`; Codebase Memory project `pi-hypercharm-provider`. **Question:** Between two `/v1/credits` polls (≥15 s apart), how do you show a live-updating balance from locally observed turn spend without ever double-counting or inventing money?

## Overwrite-reconciliation optimistic spend
**Path/Symbol:** `applyOptimisticSpend` `status.ts:106-110` (design comment `status.ts:99-105`); sole caller `commitPending` `index.ts:810-812` inside `index.ts:802-828`; reconciliation guarantee lives in `refreshCredits` (`index.ts:650-669`, every poll does `account.balance = balance`, never `-= `).
**Signature:** `applyOptimisticSpend(acc: AccountState, spendHc: number): void`.
**Data Shape:** mutates module-singleton `account.balance: number | null` in place; `spendHc` is the per-turn pending total in display hypercredits (20 hc = $1).

### Decisive source
```ts
export function applyOptimisticSpend(acc: AccountState, spendHc: number): void {
	if (spendHc > 0 && acc.balance !== null) {
		acc.balance = Math.max(0, acc.balance - spendHc);
	}
}
```
Caller context (`commitPending`, after folding pendings into `sessionStats`):
```ts
// Optimistic balance: deduct this turn's observed spend so the account
// line ticks down per turn with zero extra API calls. Every credits poll
// overwrites account.balance (never adjusts), so this cannot
// double-count; the agent_settled poll reconciles any drift.
applyOptimisticSpend(account, pendingSpendHc);
```

**Flow:** `turn_end` → tees settle → `commitPending` folds `pendingSpendHc` into session stats AND deducts it optimistically → footer shows the decremented balance immediately → next `agent_settled` activity-gated `refreshCredits(false)` OVERWRITES `account.balance` with server truth, absorbing estimation error.
**Invariant:** safety is NOT local to this function — it holds only because every writer of `account.balance` outside this path REPLACES the value (never adjusts it). A porter who adds an incrementing balance writer reintroduces double-counting. Three boundary rules: zero/negative spend is a no-op (no phantom refunds), `balance === null` stays `null` (unknown must not become a guess), and the estimate clamps at 0 — an estimated zero is NEVER treated as real exhaustion; only the observed 402 path flips `pendingSawOutOfCredits`/notify. Estimation error is bounded by one poll interval and self-heals at `agent_settled`.
**Probe:** direct test `tests/status.smoke.ts:69-80`: `applyOptimisticSpend(opt{249}, 0.5)` → 248.5; `(opt, 0)` no-op; `(opt, 300)` clamps to 0; `(unknown{null}, 1)` stays `null`. Runner: `node tests/status.smoke.ts` → "status.smoke: all assertions passed". Grep: `grep -c applyOptimisticSpend status.ts index.ts` → 2 total (def + import).
**Coverage caveat:** runtime wiring (commitPending call site) untested upstream; pure function is smoke-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "applyOptimisticSpend", limit: 3 });
// → pi-hypercharm-provider.status.applyOptimisticSpend Function status.ts 106-110
```

## Verdict
Adopt the overwrite-reconciles pattern verbatim for any locally-estimated counter displayed beside polled truth: estimate locally, clamp pessimistically, keep "unknown" distinct from zero, and make the authoritative poller a REPLACEMENT writer. Adapt units/thresholds to your currency.
