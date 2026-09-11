<!-- capsule-v2 -->
# Expressions and casts — are operators and wraps readable past column 80?

**Source:** Apache httpd C style guide §Expressions, §Indentation examples. **Question:** Are unary/binary spacing and cast syntax exactly as httpd specifies?

## Expression seam
**Path/Symbol:** expressions, casts, and long conditionals in httpd C.
**Signature:** spaced binary operators; tight unary; `(type)*` pointer casts.
**Data Shape:** boolean wraps with operators at line start when split.

### Decisive pattern
```c
a = b;
a = -b;
a = !b;
++a;

j = (int)i;
p = (char *)buf;

if (cond1 && (item2 || item3)
    && (!item4) && item5) {
    handle();
}
```

**Flow:** surround assignment and binary operators with single spaces → do not space unary increment/decrement/negation from their operand (`++a`, `!b`, `-b`) → no whitespace between a cast and the value cast: `(int)j` not `(int) j` → for pointer casts, space before `*`: `(char *)i` not `(char*)i` → when expressions exceed 80 columns, wrap at convenient points; indent continuation under the first term → when wrapping conditionals, keep parenthesized terms atomic; prefer boolean operators at the start of continuation lines.
**Invariant:** `(int) j`, `(char*)i`, or binary operator jammed without spaces fails expression review.
**Probe:** cast-spacing grep; long conditional wrap sample on changed code.

## Call/decl wrap seam
**Flow:** wrap long declarations and invocations like long expressions — continuation under first argument/term.
**Invariant:** arguments wrapped to random column without anchoring under first term fails wrap review.
**Probe:** >80 char call/decl formatting spot check.

## Verdict
httpd operator spacing, cast rules, anchored 80-column wraps. Learning note: `httpd-style-learning-note.md`.
