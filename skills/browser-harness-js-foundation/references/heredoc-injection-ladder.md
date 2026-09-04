<!-- capsule-v2 -->
# Heredoc Injection Ladder — three escaping regimes and when each is safe

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How does bash safely inject user text (queries, place names, URLs) into a JS snippet piped to the REPL — and which of the three regimes in this repo should a porter copy?

## Path / Symbol
- Regime A (sed-escape + unquoted heredoc): `gsearch/scripts/gsearch` :139-142, `xsearch/scripts/xsearch` :37-40, `ytdl/scripts/ytdl` :113-116, `ttdl/scripts/ttdl` :128-130.
- Regime B (node placeholder substitution + quoted heredoc): `gmaps/scripts/gmaps` :137-146 (comment) + :565-583, `gnews/scripts/gnews` :70-77 + :185-198, `rsearch/scripts/rsearch` :120-129 + :252-266, `gsearch follow` branch :36-43 + :125-134.

## Signature
```bash
# Regime A: unquoted <<EOF, escape for a JS single-quoted string
js_query=$(printf '%s' "$query" | sed -e 's/\\/\\\\/g' -e 's/\$/\\$/g' -e 's/`/\\`/g' -e "s/'/\\\\'/g")
raw=$(browser-harness-js <<EOF ... encodeURIComponent('${js_query}') ... EOF)

# Regime B: quoted <<'EOF' heredoc with __X__ placeholders, node replaces them
final=$(node -e 'let c=require("fs").readFileSync(0,"utf8");
  c=c.replace(/__GMAPS_QUERY__/g,()=>JSON.stringify(query)) ...' "$query" <<<"$code")
printf '%s' "$final" | browser-harness-js
```

## Data Shape
Regime B passes raw argv to node; node's `JSON.stringify` produces a guaranteed-safe JS string literal; **function-replacements** (`() => JSON.stringify(v)`) are load-bearing: plain replacement strings interpret `$&`, `$'`, `$\`` — a place name like "Cafe & Bakery" or a query containing `$` would corrupt.

## Decisive source
- gmaps :137-145 comment states the full rationale: "The inputs are injected below by placeholder substitution so the heredoc can stay quoted (backticks, $, and regex backslashes in the in-page JS need no bash escaping). The substitution itself is done in node: it JSON.stringifies the raw values into safe JS literals and uses function-replacements, which are immune to the & / $ / \\ semantics that bash ${var//pat/repl} and JS String.replace both apply to plain replacement strings."
- gsearch :136-138 comment records the REGRESSION that justifies the ladder: "The old \"s/\\$/\\\\\\$/g\" form treated $ as end-of-line anchor, appending $ to every query." — i.e. regime A has a known historical bug class.
- xsearch :76-78 adds the twin constraint for regime A: no backticks anywhere in an unquoted heredoc body ("a lone backtick opens command substitution and trips an EOF parse error"), and unquoted CSS attribute selectors `[data-testid=tweet]` are used precisely so no escaped double quotes are needed inside the outer single-quoted JS string.
- ytdl/ttdl use regime A but only after normalizing input to an 11-char video ID / URL — bounded-alphabet inputs make the weaker regime safe.
- findata uses a THIRD minimal regime: `esc()` = sed escaping for a DOUBLE-quoted JS string (backslash + doublequote only), valid because its injected values are whitelisted tokens (ticker/period/interval/range).

## Flow / Invariant
1. Quoted heredoc (`<<'EOF'`) + node placeholder injection (regime B) is the safe default for arbitrary user text — copy this for any new skill.
2. Unquoted heredoc (regime A) requires escaping backslash, dollar, backtick, single-quote AND banning backticks from the snippet body; acceptable only for short snippets or pre-normalized inputs.
3. Never interpolate shell variables directly into the snippet text (`${count}` in gsearch is fine only because it was validated numeric upstream — see data-skill-anatomy).

## Probe (direct tests)
gmaps smoke test asserts special characters survive the whole pipeline: `expect "special chars: query echoed verbatim" "café & boulangerie Paris"` (scripts/test :66-68) — an `&`-bearing query round-trips through regime B unchanged. Deterministic grep probe at this pin: `grep -c "JSON.stringify" skills/gmaps/scripts/gmaps` → 6 substitution functions present.

## Retrieve
`search_graph --project browser-harness-js --semantic-query '["placeholder"]'` or grep-first: the `__<SKILL>_...__` token family is unique per script.

## Verdict
ADOPT regime B as the porting default; record regime A's `$`-anchor regression as the reason not to "simplify" back to pure sed.
