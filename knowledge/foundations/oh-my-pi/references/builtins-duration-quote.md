<!-- capsule-v2 -->
# GNU duration + shell-quote helpers — what do sleep/timeout/timeout-rebuilders share?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** How is a GNU time interval parsed (including `inf`), and how is a command line rebuilt so a child shell re-parses it identically?

## parse_duration / quote_arg
**Path/Symbol:** `crates/pi-builtins/src/host.rs:620-646` `parse_duration`, `host.rs:654-666` `quote_arg`; consumers `sleep.rs`, `timeout.rs` (`-k KILL_AFTER` uses the same parser), rebuilders `timeout.rs:219-225` and `nohup.rs:129-138`.
**Signature:** `pub(crate) fn parse_duration(input: &str) -> Option<Duration>`; `pub(crate) fn quote_arg(arg: &str) -> String`.
**Data Shape:** Accepted: optional leading `+`, decimal number, optional suffix `s/m/h/d` (default seconds); `inf`/`infinity` any case; NaN/negative → None (usage error); infinite or overflow → `Duration::MAX` saturation ("sleep until cancelled"). Sub-millisecond precision preserved (`sleep 0.0001` = 100 µs).

### Decisive source
```rust
let value = number.parse::<f64>().ok()?;
if value.is_nan() || value.is_sign_negative() { return None; }
if value.is_infinite() { return Some(Duration::MAX); }
// Only overflow remains once NaN and negatives are excluded; saturate.
Duration::try_from_secs_f64(value * multiplier).map_or(Some(Duration::MAX), Some)
```
```rust
// quote_arg: safe set = alnum - _ . / :  else wrap in single quotes with '"'"' escaping.
let safe = arg.chars().all(|ch| ch.is_ascii_alphanumeric()
	|| matches!(ch, '-' | '_' | '.' | '/' | ':' | '+'));
```

**Flow:** `timeout`/`nohup` reconstruct the command they were handed as ONE string re-parsed by the inner shell (`run_string`) — every arg that could be re-split or re-expanded must be quoted first, empty arg becomes `''`.
**Invariant:** Zero duration is VALID and means "no timeout" for timeout (checked at the select site, not in the parser). The safe-character allowlist deliberately excludes `=`, space, `$`, backtick — anything with expansion meaning gets quoted even if it looks harmless.
**Probe:** deterministic anchor: `grep -c 'Sub-millisecond precision' crates/pi-builtins/src/host.rs` = 1. Direct tests live on consumers: `sleep.rs:96 infinity_operand_parses_and_sleep_is_cancellable`, `timeout.rs:474 invalid_duration_preserves_diagnostic` + :559 `zero_duration_disables_the_timeout`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "parse_duration infinity sleep timeout suffix", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: rank-1 `sleep.infinity_operand_parses_and_sleep_is_cancellable sleep.rs:96-131`.

## Verdict
Adopt both helpers verbatim — they encode GNU corner semantics (`inf`, zero, negative rejection, saturation) that ad-hoc parsers get wrong. Adapt error reporting to your CLI framework; keep quoting BEFORE rebuilding any command line destined for re-parsing.
