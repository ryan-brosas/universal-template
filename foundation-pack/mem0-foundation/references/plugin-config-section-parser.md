<!-- capsule-v2 -->
# Repo-carried config section grammar — how does a project's plain markdown file become typed configuration without a schema engine?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when config must live in a human-edited `mem0.md` inside each repo, what parsing grammar extracts typed sections (retention days, ignore globs, prose policy) while staying silent about malformed input?

## parse_mem0_config.py — one heading regex, five typed readers
**Path/Symbol:** `integrations/mem0-plugin/scripts/parse_mem0_config.py` — `find_mem0_config` (27–33), `parse_retention` (36–91), `parse_section_kv` (94–113), `parse_section_list` (116–132), `parse_section_text` (135–154), `parse_ignore_patterns` (157–176), `load_full_config` (179–238), `load_retention_policies` (241–260).
**Signature:** `parse_retention(content: str) -> dict[str, int | None]`; `load_full_config(cwd: str | None = None) -> dict`.
**Data Shape:** assembled keys, present only when non-empty: `retention` (`cat→int|None`, None = forever), `search`/`identity`/`settings` (kv), `categories`+alias `default_categories` (list), `ignore` (globs), `instructions`+`agent_instructions` (collapsed prose). CLI: default prints retention JSON; `--full` everything; `--key a.b.c` prints scalar or empty string.

### Decisive source
```python
    # Find the ## Retention section (allow any amount of trailing whitespace /
    # extra words, but the heading must start with "## Retention").
    section_match = re.search(
        r"^##\s+Retention[^\n]*\n(.*?)(?=^##\s|\Z)",
        content,
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    ...
        if value == "forever":
            policies[category] = None
        else:
            days_match = re.match(r"^(\d+)d$", value)
            if days_match:
                policies[category] = int(days_match.group(1))
            # else: malformed value — skip silently
```
`parse_section_text` drops full-line `#` comments but PRESERVES inline `#` ("prose may reference e.g. issue ``#123``") and joins lines to one string.

**Flow:** locate `<cwd>/mem0.md` → run the shared heading regex (`^##\s+<H>[^\n]*\n` with lazy DOTALL body up to lookahead `(?=^##\s|\Z)`, case-insensitive) per needed section → type each body: retention values are strictly `\d+d` or `forever`; kv strips comments then splits first colon; list accepts `- `/`* `/bare lines; text collapses to one line. Missing file, missing section, unreadable file → `{}`. Writers consume only `_instructions.load_instructions(cwd)` (which calls `load_full_config` for the two instruction keys); retention currently surfaces only through this module's own CLI.
**Invariant:** every reader is total and silent: no exception path, no partial dicts from bad lines — a malformed value is skipped, not defaulted (reject-don't-guess at line granularity). Sections end at the NEXT `##` heading or EOF, so extra words on a heading line are tolerated but nested content is never bled across sections.
**Probe:** `integrations/mem0-plugin/tests/test_parse_mem0_config.py` — unit matrix pins valid-day extraction, `forever→None`, no-section→`{}`, stops-at-next-heading, malformed-lines-skipped, inline-comment stripping, case-insensitive heading, plus subprocess CLI tests (`--full`, `--key`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.trace_path({ project: "mem0", function_name: "parse_retention", direction: "inbound" });
```
Executed live: inbound trace shows the consumer chain `_instructions.load_instructions → load_full_config → parse_*` plus the standalone `main`/`load_retention_policies` CLI lane — proving writers touch only instruction keys today.

## Verdict
Adopt the single-heading-regex + per-type reader decomposition and the skip-malformed-silently posture for human-edited config; adopt the keys-only-when-non-empty assembly so consumers can't distinguish absent vs empty. Adapt section names/value syntax to your format; keep `--key dotted.path` returning "" for absent (shell-friendly). Omit nothing else. Cross-reference: pass-8 capsule `plugin-instructions-policy-merge.md` covers the CONSUMER side (merge into add bodies); this capsule covers the PARSER itself. Coverage: fully indexed, whole 316L file read.
