<!-- capsule-v2 -->
# Billed-session zombie reaper — how do you page a cloud API for live resources and stop only the stale ones, with per-item failure isolation?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness` (agent-workspace plane, zero graph citations before this pass). **Question:** A domain skill must clean up leaked paid sessions via the public REST surface — what wire-shape contracts does it pin (pagination predicate, ISO-8601 parsing, string-typed costs, exit-code taxonomy)?

## finishedAt-filtered pagination + Z-swap timestamps + string-cost tolerance
**Path/Symbol:** `agent-workspace/domain-skills/browser-use-cloud/cleanup-zombies.py:list_active_browsers/_parse_started/_to_float/stop_browser/main` (:58-159); documented by the sibling skill manual `cloud.md`.
**Signature:** `list_active_browsers() -> list[dict]`; `_parse_started(b) -> datetime`; `stop_browser(browser_id)` = `PATCH /browsers/{id}` body `{"action": "stop"}`.
**Data Shape:** GET `/api/v3/browsers?pageSize=100&pageNumber=N` → `{items: [...], totalItems}`; item keys {id, startedAt (ISO-8601 UTC trailing `Z`), finishedAt?, browserCost/proxyCost/proxyUsedMb as STRINGS-or-null}; auth header is the non-standard `X-Browser-Use-API-Key`. Exit codes: 0 = ran (stopped or nothing to do), 1 = API error, 2 = bad args.

### Decisive source
```python
# liveness filter + termination predicate in ONE loop
items = listing.get("items") or []
if not items:
    break
out.extend(b for b in items if not b.get("finishedAt"))     # alive = no finishedAt
if len(out) + sum(1 for b in items if b.get("finishedAt")) >= listing.get("totalItems", len(items)):
    break                                                    # seen == total ⇒ stop paging

# Python <3.11 cannot parse a trailing 'Z' — swap it explicitly
return datetime.datetime.fromisoformat(b["startedAt"].replace("Z", "+00:00"))

# cost/proxy fields arrive as STRINGS (or None): tolerate both
def _to_float(v): return float(v) if v else 0.0
```

**Flow:** env key required (`X-Browser-Use-API-Key`) → page GET /browsers accumulating non-finished items until seen-count ≥ totalItems → compute age from startedAt vs UTC cutoff (`--older-than`, default 30min; negative refused at parse time) → zombies get PATCH stop UNLESS `--dry-run` (action becomes `would_stop`) → per-item try isolates HTTPError/URLError into `stop_failed: …` records so one bad id never aborts the sweep → machine output `--json` = one JSON object per inspected browser vs tagged human lines `[STOP|DRY|OK] id age=… cost=$…` → final summary line counts.
**Invariant:** "active" is defined by ABSENCE of `finishedAt`, never by status enums (wire-shape gotcha pinned in the sibling cloud.md manual); pagination terminates on a COUNT comparison, not on a short page (a full-but-final page would otherwise trigger one extra request); timestamps are parsed with an explicit Z→+00:00 swap because `fromisoformat` rejects `Z` before Python 3.11; money arrives as strings — naive float conversion crashes on empty values; destructive action is gated twice (age cutoff AND dry-run flag) while failures degrade to per-record annotations with exit code still 0 — the run REPORTS what failed instead of abandoning remaining browsers.
**Probe:** no automated test upstream — the script IS declared "the live regression artefact" for the cloud.md skill (its docstring), i.e. running it against the real API exercises every documented gotcha; deterministic anchors verified at source :66-68 (filter+termination), :74-75 (Z-swap), :78-80 (string costs). Coverage caveat: live-API behavior untested in CI.
**Coverage caveat:** agent-workspace scripts sit outside the indexed src tree; verified by direct read at the pinned commit.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "browsers stop patch cleanup", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the absence-of-terminal-field liveness predicate + count-based pagination stop + explicit Z-swap + string-tolerant numeric coercion for any cloud-resource reaper; adapt endpoint/headers. Omit cost accounting if your provider doesn't bill per session.
