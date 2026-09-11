<!-- capsule-v2 -->
# Formatting and control flow — is layout readable and comparisons safe?

**Source:** CMU C Coding Standard §Formatting; Linux kernel §Indentation/Functions. **Question:** Can a maintainer see block boundaries and avoid assignment-in-condition bugs?

## Brace and line seam
**Path/Symbol:** C control-flow blocks in `.c` files.
**Signature:** K&R braces; ≤78–80 columns; one statement per line.
**Data Shape:** space after keywords; no space before `(` on functions.

### Decisive pattern
```c
if (6 == error_num) {
    error_num = 0;
} else if (STATE_OPEN == state) {
    handle_open();
} else {
    log_unhandled_state(state);
}
```

**Flow:** opening `{` on same line as `if`/`while`/`for` → always brace multi-line bodies → keep lines ≤78 chars → one statement per line.
**Invariant:** `if (x = y)` tests or multiple statements on one line without braces fail review.
**Probe:** clang-format / project style check; manual scan for assignment inside `if` condition.

## Yoda and switch seam
```c
switch (opcode) {
case OP_READ:
    read_block();
    break;
case OP_WRITE:
{
    int bytes = payload_len;
    write_block(bytes);
    break;
}
default:
    return EINVAL;
}
```

**Flow:** literal/compare constant on left for `==`/`!=` → `default` in every `switch` → comment intentional fallthrough → wrap case-local declarations in block.
**Invariant:** `if (strcmp(a, b))` without explicit `== 0` comparison fails review.
**Probe:** grep `if\s*\([^=]*=[^=]` for suspicious conditions; switch coverage lint.

## Verdict
K&R braces, short lines, Yoda equality, explicit switch default. Learning note: `c-style-learning-note.md`.
