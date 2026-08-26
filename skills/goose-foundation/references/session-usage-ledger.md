<!-- capsule-v2 -->
# Session usage ledger — how do you bill tokens/cost durably across schema upgrades, subagent trees, and conversation rewrites?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** How do I record per-turn usage so totals survive pre-ledger databases, parent/child (subagent) session trees, and full conversation replacement?

## Ledger reconciliation plane
**Path/Symbol:** `crates/goose/src/session/session_manager.rs` : `SessionStorage.record_usage_metrics` (2163-2251), `insert_usage_ledger_row` (859-894), `get_session_usage_totals` (2253-2335).
**Signature:** `async fn record_usage_metrics(&self, session_id: &str, schedule_id: Option<String>, current_usage: Usage, model: &str, ledger: &MessageUsage) -> Result<()>`.
**Data Shape:** Append-only `usage_ledger(id, session_id, created_timestamp, model, 5 token columns, cost, cost_source ∈ {provider_reported, estimated, carried_forward}, is_compaction)` + cache columns on `sessions` (`usage`, `accumulated_usage`, `accumulated_cost`).

### Decisive source
```sql
-- statement 1 of the tx: capture POSITIVE DRIFT between the accumulated
-- columns and SUM(ledger) as a carried_forward row (pre-v15 spend)
INSERT INTO usage_ledger (...) SELECT s.id, strftime('%s','now'),
   MAX(COALESCE(s.accumulated_input_tokens,0) - l.input_sum, 0), ...
FROM sessions s, (SELECT COALESCE(SUM(input_tokens),0) AS input_sum, ... FROM usage_ledger WHERE session_id = ?) l
WHERE s.id = ? AND (COALESCE(s.accumulated_input_tokens,0) > l.input_sum OR ... OR COALESCE(s.accumulated_cost,0.0) > l.cost_sum + 1e-9)
```
```sql
-- statement 2: cache update — current = snapshot; accumulated += ledger delta
UPDATE sessions SET total_tokens = ?, ...,
    accumulated_total_tokens = COALESCE(accumulated_total_tokens,0) + ?, ...,
    accumulated_cost = CASE WHEN ? IS NULL THEN accumulated_cost
                            ELSE COALESCE(accumulated_cost,0) + ? END
WHERE id = ?
```
```sql
-- totals: recursive tree over parent_session_id, per-node max(acc, ledger), then sum
WITH RECURSIVE tree(id) AS (
    SELECT id FROM sessions WHERE id = ?
    UNION SELECT s.id FROM sessions s JOIN tree ON s.parent_session_id = tree.id)
```
Rust fold: `let larger = |acc, ledger| acc.unwrap_or(0).max(ledger.unwrap_or(0));` per column per node.

**Flow:** turn end → single IMMEDIATE tx: reconcile drift → update cache columns → append real ledger row. Totals query → walk descendant tree → per node take max(cache, ledger-sum) → sum nodes.
**Invariant:** The ledger is truth and never deleted except with the session (delete removes ledger rows explicitly); `replace_conversation` deletes messages but NEVER touches usage_ledger. Reconciliation only fires when a column genuinely exceeds its ledger sum, so repeated calls are stable. Legacy sessions without ledger rows read through via the max() fold.
**Probe:** tests `test_ledger_reconciles_spend_recorded_on_pre_v15_builds` (drift row created once; second reconcile stays consistent), `test_usage_totals_include_subagent_tree` (140 = 100+40 through parent), `test_usage_totals_read_through_unreconciled_drift`, `test_usage_ledger_survives_conversation_replace`, `test_usage_totals_mixed_legacy_and_ledger_tree`. Run: `cargo test -p goose --lib session::session_manager`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "usage_ledger carried_forward reconciliation accumulated drift totals parent tree", limit: 8, fields: ["lines"] });
```

## Verdict
Adopt: append-only ledger + derived cache columns + drift-reconciliation insert + recursive-tree totals with per-node max(). Adapt cost sources/column names to your host. Omit goose's MessageUsage/Usage plumbing and CostSource enum spellings.
