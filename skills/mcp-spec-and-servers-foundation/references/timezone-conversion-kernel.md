<!-- capsule-v2 -->
# Timezone conversion kernel — how do you convert an HH:MM wall clock between IANA zones so DST is correct on both sides and fractional offsets render cleanly?

**Source:** modelcontextprotocol/servers MIT `main@599dafc1054550a6eeb87a6545c1e1b03b3ca827`; Codebase Memory `servers`. **Question:** what is the minimal correct arithmetic for cross-zone time tools, and how should invalid zone names surface?

## Offset-delta arithmetic anchored to today in the source zone (never naive datetime subtraction)
**Path/Symbol:** `src/time/src/mcp_server_time/server.py` — `TimeServer.get_current_time` :61–71; `TimeServer.convert_time` :73–120; `get_zoneinfo` :53–57; `get_local_tz` :41–50; schema-description local-tz embedding :128–180.
**Signature:** `convert_time(self, source_tz: str, time_str: str, target_tz: str) -> TimeConversionResult` where `TimeConversionResult = {source: TimeResult, target: TimeResult, time_difference: str}` and `TimeResult = {timezone, datetime (isoformat seconds), day_of_week (%A), is_dst (bool(dt.dst()))}`. `get_zoneinfo` raises `McpError(ErrorData(code=INVALID_PARAMS, ...))` on unknown IANA keys — a deliberate PROTOCOL-error mapping (:53–57).
**Data Shape:** input is bare `HH:MM` 24-hour wall clock plus two IANA names (no date — conversions are always "today"); output difference is a signed display string, integer hours as `+X.0h`, fractional via zero-stripping (`+4.75h` for Kathmandu, `+8.5h` for Lord Howe).

### Decisive source
```python
// src/time/src/mcp_server_time/server.py:80-104 (verbatim core)
        try:
            parsed_time = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            raise ValueError("Invalid time format. Expected HH:MM [24-hour format]")

        now = datetime.now(source_timezone)
        source_time = datetime(
            now.year, now.month, now.day,
            parsed_time.hour, parsed_time.minute,
            tzinfo=source_timezone,
        )

        target_time = source_time.astimezone(target_timezone)
        source_offset = source_time.utcoffset() or timedelta()
        target_offset = target_time.utcoffset() or timedelta()
        hours_difference = (target_offset - source_offset).total_seconds() / 3600

        if hours_difference.is_integer():
            time_diff_str = f"{hours_difference:+.1f}h"
        else:
            # For fractional hours like Nepal's UTC+5:45
            time_diff_str = f"{hours_difference:+.2f}".rstrip("0").rstrip(".") + "h"
```

**Flow:** both zones resolved through `get_zoneinfo` FIRST (invalid names fail as McpError/INVALID_PARAMS before any parsing) → HH:MM parsed strictly → wall clock anchored to TODAY's Y/M/D in the SOURCE zone → `.astimezone(target)` lets each side apply its own DST rule at that instant → difference computed from `utcoffset()` DELTAS at those instants, never from naive clocks. `get_current_time` is the same kernel degenerated to one zone (`datetime.now(tz)`, `is_dst=bool(current_time.dst())`). `serve()` resolves the host zone once via override-or-tzlocal-or-UTC (:41–50, :126) and INTERPOLATES it into every tool description string ("Use '{local_tz}' ... if no timezone provided by the user") so the model self-selects a default instead of guessing :128–180.
**Invariant:** THREE load-bearing rules: (1) **compute the difference from utcoffset() deltas AFTER astimezone** — during the week when Europe has left DST but America has not, Warsaw→New York is −5h then −6h after Nov 3; naive fixed-offset math or clock subtraction gets exactly these wrong, and they are the suite's pinned edge cases. (2) **anchor to today in the SOURCE zone**, accepting fold=0 first-occurrence semantics for ambiguous fall-back times — the reference does NOT disambiguate folds; porters needing unambiguous semantics must add fold handling themselves (tests deliberately avoid ambiguous inputs). (3) **bad IANA keys ride McpError(INVALID_PARAMS)** while bad HH:MM rides plain ValueError — an as-shipped split that CONTRASTS with SEP-1303's input-validation-prefers-isError guidance recorded in `validation-error-taxonomy.md`; know which surface your SDK gives each exception class before copying either choice. Formatting rule: sign always explicit, integer hours keep `.0`, fractional strips trailing zeros.
**Probe:** `src/time/test/time_server_test.py` (528L): freeze_time-pinned matrix of 16 conversions — Europe/USA DST-asymmetry window Oct 28 vs Nov 4 :168–210, Kathmandu ±4.75h :211–252, Lord Howe 30-minute DST shift (+11 vs +10:30) :253–295, Samoa +13 / Kiritimati +14 date-line crossings :296–317/:405–426, Chatham +12:45/+13:45 :427–448, historical Caracas −4:30 (2016) :339–360, Antarctica/Troll double-DST :383–404, Israel variable DST :361–382 — plus error mapping :85–120 and five get_local_tz cases incl. tzlocal-None→UTC fallback :465–527. Live-run 2026-08-25: **38 passed** (same venv, freezegun pinning the clock).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "mcp_server_time get_current_time convert_time timezone" });
await mcp.codebase_memory.get_code_snippet({ project: "servers", qualified_name: "servers.src.time.src.mcp_server_time.server.TimeServer.convert_time" });
```
(Live-executed at `599dafc1`: BM25 returns all 15 module symbols led by convert_time :73–120; get_code_snippet returns the method byte-identical to disk.)

## Verdict
Adopt the kernel: resolve zones up front, parse the wall clock strictly, anchor to today in the source zone, convert with astimezone, and derive the displayed difference from utcoffset() deltas — this single discipline survives DST asymmetry windows, 45/30-minute offsets, historical offset changes, and date-line zones without special cases. Embed the resolved local zone into tool descriptions rather than inventing a default-zone parameter convention, and decide EXPLICITLY whether invalid zone names are protocol errors (this server: McpError INVALID_PARAMS) or tool-execution errors before porting. Omit nothing from the freeze-time test style: every edge case above is only trustworthy because the clock is pinned. Direct-test coverage complete at `599dafc1`.
