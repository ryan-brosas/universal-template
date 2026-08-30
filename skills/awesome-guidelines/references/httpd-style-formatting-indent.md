<!-- capsule-v2 -->
# Formatting and indent — does layout match httpd GNU indent profile?

**Source:** Apache httpd C style guide §Introduction, §Indentation. **Question:** Are tabs absent, wraps at 80 columns, and braces aligned the httpd way?

## Indent seam
**Path/Symbol:** `.c`/`.h` in httpd tree or compatible modules.
**Signature:** 4-space levels; 80-column wrap; closing brace aligned with opener text.
**Data Shape:** GNU indent `-i4 -npsl -di0 -br -nce -d0 -cli0 -npcs -nfc1 -nut`.

### Decisive pattern
```c
static apr_status_t
really_long_name(int i, int j, const char *args, void *foo, int k)
{
    if (cond1 && (item2 || item3) && (!item4)
        && (item5 || item6) && item7) {
        do_a_thing();
    }
}
```

**Flow:** indent each level with four spaces — never use tab characters → wrap lines past column 80; continue wrapped arguments/expressions under the first term on the line → place opening `{` on the same line as the statement or on the line after a function signature aligned with the return-type text → place closing `}` on its own line aligned with the start of text on the line holding the matching `{` → indent comments to the same level as surrounding code → prefer automated formatting with GNU indent using httpd flags: `-i4 -npsl -di0 -br -nce -d0 -cli0 -npcs -nfc1 -nut` → break layout rules only when clarity clearly improves (document in review if exceptional).
**Invariant:** tab-indented file, >80-col unwrapped expression, or misaligned closing brace fails httpd layout review.
**Probe:** `grep $'\t'`; column-80 spot check; optional GNU indent diff on changed files.

## Whitespace seam
**Flow:** comments at code indent; no stray trailing whitespace on committed lines.
**Invariant:** de-indent comment column unrelated to surrounding block fails readability review.
**Probe:** visual comment alignment scan.

## Verdict
Four-space, 80-col wraps, httpd brace alignment, GNU indent recipe. Learning note: `httpd-style-learning-note.md`.
