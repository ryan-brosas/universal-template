<!-- capsule-v2 -->
# Functions and control flow — are ANSI signatures and if/switch layout canonical?

**Source:** Apache httpd C style guide §Function Declaration, §Flow-Control, §switch. **Question:** Do functions and control keywords follow httpd spacing and brace placement?

## Function seam
**Path/Symbol:** functions in httpd modules and core.
**Signature:** ANSI prototypes; `void` when empty; no space before `(`; spaced commas.
**Data Shape:** return type + name line; `{` on following line under return type.

### Decisive pattern
```c
int main(int argc, char **argv)
{
    f(a, b);
}

void noop(void)
{
    return;
}
```

**Flow:** declare functions with ANSI argument lists — use `(void)` when there are no parameters → put return type on the same line as the function name → no space between function name and opening `(` in definitions or calls → single space after commas in argument lists and after semicolons in `for` headers → place function opening `{` on the line after the signature, indented to align with the return-type text; indent body four spaces → keep functions short and understandable; add comments when behavior is not obvious from code alone.
**Invariant:** K&R-style parameter list without prototypes, space before `(`, or missing space after comma fails httpd function review.
**Probe:** prototype scan; call-site spacing check.

## Flow seam
**Flow:** `if`/`while`/`for`: space after keyword; `{` on same line as keyword expression; `else` on next line aligned with matching `if` → `for (a; b; c)` with spaces after semicolons → `switch`: `case` labels aligned with `switch` line; case bodies indented +4; braces like other control keywords.
**Invariant:** `else` aligned with wrong `if` column or `case` over-indented to body level fails control-flow review.
**Probe:** switch/if sample alignment walk on changed functions.

## Verdict
ANSI void/non-void signatures, httpd call spacing, if/else/switch/for brace rhythm. Learning note: `httpd-style-learning-note.md`.
