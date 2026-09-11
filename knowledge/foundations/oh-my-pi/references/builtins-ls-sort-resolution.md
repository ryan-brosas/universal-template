<!-- capsule-v2 -->
# ls last-wins sort resolution — argv-index arbitration among mutually exclusive flags

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils port); Codebase Memory `oh-my-pi`. **Question:** When `-t`, `-S`, `-U`, `--sort=…` and `-c/-u` time choices combine, which ordering wins?

## extract_sort
**Path/Symbol:** `crates/pi-builtins/src/ls.rs:` `extract_sort` (:1142-1200+), format mapping :1083-1084 (`single-column`→OneLine, `columns|vertical`→Columns), test modules :839/:2154.
**Signature:** `fn extract_sort(options: &clap::ArgMatches) -> Sort` — Sort ∈ {Name, Time, Size, Version, Extension, Width, None}.
**Data Shape:** Each candidate flag's LAST command-line occurrence index is taken (`value_source == CommandLine` guard excludes config/env-provided values); max index wins; index 0 (no flag) falls to the default ladder.

### Decisive source
```rust
let get_last_index = |flag: &str| -> usize {
	if options.value_source(flag) == Some(clap::parser::ValueSource::CommandLine) {
		options.index_of(flag).unwrap_or(0)
	} else { 0 }
};
...
match max_sort_index {
	0 => {
		// No explicit sort flag: -c/-u (with --time) imply TIME sort, else Name
		if !options.get_flag(options::format::LONG)
			&& (options.get_flag(options::time::ACCESS)
				|| options.get_flag(options::time::CHANGE)
				|| options.get_one::<String>(options::TIME).is_some())
		{ Sort::Time } else { Sort::Name }
	},
	idx if idx == unsorted_all_index || idx == none_index => Sort::None,
	...
}
```

**Flow:** collect indices of every sort-bearing flag → take max → map to variant; ties impossible because max picks one; default branch applies GNU's implicit rule that time-style options alone switch sorting to mtime.
**Invariant:** (1) value_source gating is what makes precedence apply to COMMAND-LINE occurrences only — a config-file `-t` must not outrank an explicit `-S`. (2) `--sort=none` and `-U` share the None arm but are distinct indices so later-of-two still wins. (3) The same last-wins pattern recurs for ls's other exclusive families (format, time style).
**Probe:** deterministic anchor: `grep -c 'fn extract_sort' crates/pi-builtins/src/ls.rs` = 1; behavior tests in ls.rs:839 module.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "extract_sort ls sort none version extension width", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (ls.rs:1142).

## Verdict
Adopt index-arbitrated last-wins resolution for any CLI with mutually exclusive selection flags. Adapt to your arg parser's occurrence tracking; keep the command-line-only source guard.
