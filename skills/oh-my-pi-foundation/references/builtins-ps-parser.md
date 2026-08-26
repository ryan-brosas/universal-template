<!-- capsule-v2 -->
# ps dual-dialect parser — BSD clusters vs long options, one argv walker

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** How does one parser accept `ps aux`, `ps -ef`, and `ps --format` without clap?

## parse_ps_args
**Path/Symbol:** `crates/pi-builtins/src/ps.rs:` `parse_ps_args` (:489-569), `take_ps_value` (:571-589), `parse_ps_flag_group` (:591-619+), tests (:1406-1489).
**Signature:** `fn parse_ps_args(argv: &[String]) -> Result<ParsePsResult, (u8, String)>` — errors carry exit code 1.
**Data Shape:** Operand classification order: `--` → everything after = pid list; long opts (`--pid=`, `--User` uppercase = REAL uid); `-cluster` with `x` ⇒ bsd_syntax; pure digit/comma tokens = pids; PURE ALPHABETIC bare words = BSD flag groups (`aux`) — anything else = unsupported operand.

### Decisive source
```rust
_ if arg.chars().all(|character| character.is_ascii_digit() || character == ',') => {
	parse_i32_list(arg, &mut options.pids)?;
},
_ if arg.chars().all(|character| character.is_ascii_alphabetic()) => {
	parse_ps_flag_group(arg, true, argv, &mut index, &mut options)?;   // bare "aux" cluster
},
```
```rust
'e' if !bsd => options.all = true,
'e' => {},                      // BSD -e is environment display, not select-all
'x' => { options.include_no_terminal = true; options.bsd_syntax = true; },
```

**Flow:** walk argv once → per-token classify → flag groups consumed with attached values where the flag takes one (`-o pid:8=PROCESS,user=args=COMMAND` style column spec with width/override, `--sort=-pcpu,+pid` with direction prefixes) → options box returned; formatting later picks BSD-style or AIX/long columns by which dialect won.
**Invariant:** (1) Same letter means different things by dialect context (`e`) — the `bsd` bit captured from the FIRST cluster governs the rest. (2) Bare-word clusters are only flags when purely alphabetic; `ps 1,2` selects pids. (3) Elapsed/start formatting has explicit boundary pins (mm:ss under an hour, H:MM:SS under a day, `d-HH:MM:SS` beyond; start shows time <24 h, `MonDD` <180 d, year beyond; `?` when unknown).
**Probe:** direct tests pin parsing + formats: `ps.rs:1410 parses_output_field_lists_and_overrides`, :1428 `rejects_unknown_output_field`, :1435 `parses_sort_keys_and_directions`, :1451 `formats_elapsed_time_boundaries` (`00:00`,`01:05`,`01:01:01`,`1-01:01:01`), :1459 `formats_start_time_by_age`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "parse_ps_args bsd syntax flag group", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (`parse_ps_args` ps.rs:489).

## Verdict
Adopt the single-walker dual-dialect classification for any ps-like tool. Adapt column tables to your needs; keep dialect-context-dependent letters explicit and the boundary-pinned time formatters.
