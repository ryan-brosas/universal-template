<!-- capsule-v2 -->
# Naming and types — are symbols descriptive where global and typedefs justified?

**Source:** Linux kernel coding style §3.1, §4, §5. **Question:** Do pointers, globals, locals, and typedefs follow kernel naming and sparse-type rules?

## Spacing and pointers seam
**Path/Symbol:** expressions and declarations in kernel C.
**Signature:** `char *name`; space after keywords; tight parens.
**Data Shape:** no spaces inside `( )`; binary operators spaced.

### Decisive pattern
```c
char *linux_banner;
unsigned long long memparse(char *ptr, char **retptr);

if (condition)
	do_this();
s = sizeof(struct file);
```

**Flow:** space after keywords `if`, `switch`, `case`, `for`, `do`, `while` → no space after `sizeof`, `typeof`, `alignof`, `__attribute__` → no spaces inside parenthesized expressions → attach `*` to the data or function name, not the type (`char *p`, not `char* p`) → one space around binary/ternary operators; no space after unary operators; no space around `.`/`->`.
**Invariant:** `sizeof( struct x )` or `char* p` fails kernel spacing review.
**Probe:** spot-check declarations and sizeof calls in diff.

## Naming seam
**Flow:** global functions and globals must be descriptive English (`count_active_users`) — never `foo` or `cntusr` → local names may be short when unambiguous (`i`, `tmp`) → avoid mixedCase and Hungarian type encoding → for new symbols/docs avoid master/slave and blacklist/whitelist; prefer primary/replica, denylist/allowlist unless preserving userspace ABI or mandated hardware spec terminology.
**Invariant:** terse global identifier or new non-inclusive pairing without documented exception fails kernel naming review.
**Probe:** review exported symbols and new comments for naming and terminology table.

## Typedef seam
**Flow:** do not typedef structs/pointers for readability — use `struct type *p` → typedef allowed only for: opaque objects (`pte_t`) with accessors; sized integers (`u8`/`u16`/`u32`/`u64`) when helpful; sparse artificial types; config-dependent widths with clear reason → when editing existing files, match local typedef convention.
**Invariant:** new `foo_t` struct typedef without opaque/size/sparse justification fails review.
**Probe:** grep new `_t` typedefs; confirm category (a–d) in commit message.

## Verdict
Pointer star on name, keyword spacing, descriptive globals, short locals, limited typedefs, inclusive terminology. Learning note: `linux-kernel-style-learning-note.md`.
