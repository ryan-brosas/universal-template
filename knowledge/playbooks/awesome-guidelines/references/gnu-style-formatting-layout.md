<!-- capsule-v2 -->
# Formatting and layout — does C match GNU defun-friendly column rules?

**Source:** GNU Coding Standards §Formatting Your Source Code. **Question:** Are lines ≤79 cols, function names/`{` at column 1, and GNU indent spacing applied?

## Function definition seam
**Path/Symbol:** `.c` function definitions in GNU tree.
**Signature:** name column 1; opening `{` column 1; 2-space body indent.
**Data Shape:** GNU `indent` 1.2+ flag set from standards.

### Decisive pattern
```c
static char *
concat (char *s1, char *s2)
{
  /* ... */
}

int
lots_of_args (int an_integer, long a_long, short a_short,
              double a_double, float a_float)
{
  /* ... */
}
```

**Flow:** keep source lines to 79 characters or less → start function name in column one (return type may sit on the line above) → put the function body opening brace in column one so Emacs/tools recognize defuns → never put `{`, `(`, or `[` in column one inside a function body → for `struct`/`enum`, braces in column one unless entire type fits one line → indent function body with two spaces per level (GNU `indent` defaults) → put spaces before open-parenthesis in calls and after commas: `foo (bar, baz)` → when splitting expressions, break before operators, not after → add parentheses so nested precedence is visible in indentation → format `do { ... } while (...)` as in the standards example → separate logical file sections with formfeed (Ctrl-L) alone on a line, not inside functions → when contributing to an existing program, match its established style → optional mechanical format: `indent` with GNU flags `-nbad -bap -nbc -bbo -bl -bli2 -bls -ncdb -nce -cp1 -cs -di2 -ndj -nfc1 -nfca -hnl -i2 -ip5 -lp -pcs -psl -nsc -nsob`.
**Invariant:** function `{` not in column 1, line >79 without wrap, or `call(arg)` without space before `(` fails GNU formatting review.
**Probe:** column-1 brace check on function defs; `grep -E '.{80}'` on changed lines; optional GNU `indent` diff.

## Control-flow layout seam
```c
if (x < foo (y, z))
  haha = bar[4] + 5;
else
  {
    while (z)
      {
        haha += foo (z, z);
        z--;
      }
    return ++x + bar ();
  }
```

**Flow:** align inner blocks with 2-space indent; inner `{` not column 1.
**Invariant:** inner open-brace at column 1 inside function breaks defun heuristics.
**Probe:** visual scan of nested blocks; Emacs `beginning-of-defun` navigation spot-check.

## Verdict
79-column, defun column-1 function braces, 2-space indent, spaces before `(`. Learning note: `gnu-style-learning-note.md`.
