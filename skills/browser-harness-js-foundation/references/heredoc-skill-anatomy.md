<!-- capsule-v2 -->
# Heredoc skill anatomy — how does a zero-dependency bash CLI ship safe JS to the daemon?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What are the quoting/substitution rules that keep shell args out of JS-injection trouble?

## Quoted heredoc + placeholder function-replacement (multi-arg) or sed single-quote escape (single arg)
**Path/Symbol:** `AGENTS.md` conventions (:95-135); template instance `skills/gsearch/scripts/gsearch` (`follow` subcommand = node placeholder path; main path = sed escape); gmaps named as the multi-value template by AGENTS.md.
**Signature:** script shape: `#!/usr/bin/env bash` + `set -euo pipefail` → auto-fix header (symlink sibling `../cdp/sdk/browser-harness-js` if missing from PATH) → arg parsing → `browser-harness-js <<'EOF' … EOF` returning a string or object.
**Data Shape:** quoted heredoc means backticks/`$`/regex backslashes in page-side JS need NO bash escaping; values enter via exactly two sanctioned channels.

### Decisive source
```bash
# Placeholder substitution (preferred, multiple values):
final=$(node -e '
let c=require("fs").readFileSync(0,"utf8");
c=c.replace(/__GSEARCH_URL__/g,()=>JSON.stringify(url))
    .replace(/__GSEARCH_SELECTOR__/g,()=>JSON.stringify(selector));
process.stdout.write(c);' "$url" "$selector" <<<"$code")

# Inline escaping (single value):
js_query=$(printf '%s' "$query" | sed -e 's/\\/\\\\/g' -e 's/\$/\\$/g' -e 's/`/\\`/g' -e "s/'/\\\\'/g")
```
The recorded trap: the old `s/\$/\\$\$/g` form treated `$` as the EOL anchor and appended `$` to every line — the `$` rule must match a literal `\$`.

**Flow:** parse args in bash → build the QUOTED heredoc with `__TOKEN__` placeholders → rewrite tokens via a node one-liner using FUNCTION-replacements (`() => JSON.stringify(v)`) which dodge the `&`/`$`/`\` semantics that BOTH bash `${var//pat/repl}` and JS `String.replace` apply to plain replacement strings → pipe into `browser-harness-js` (stdin form for multi-statement code — remember explicit `return`) → print raw body.
**Invariant:** (1) NEVER `export VAR` and read `process.env` in snippets — the daemon is long-lived and won't see it. (2) NEVER unquoted heredocs. (3) Function-replacement is mandatory wherever values may contain `&`/`$`. (4) The auto-fix header resolves the CLI RELATIVE TO THE SCRIPT so the same file works from repo and installed copy.
**Probe:** no unit tests for scripts (live-browser CLIs, exit 77 when browser unreachable). Deterministic probes: the two canonical implementations — `grep -n "__GSEARCH_URL__\|()=>JSON.stringify" skills/gsearch/scripts/gsearch`; convention source `AGENTS.md:117-135`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "gsearch", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt this anatomy verbatim when adding skills that drive any eval-daemon from bash; adapt token names/arg parsing per tool; omit nothing from the substitution rules — they are the difference between a CLI and an injection vector.
