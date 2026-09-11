<!-- capsule-v2 -->
# Macros, docs, and verify — are macros safe, API documented, and patches checkpatch-clean?

**Source:** Linux kernel coding style §8, §12, §14, §9. **Question:** Do macros avoid control-flow traps, exported API use kernel-doc, alloc uses kmalloc_obj, and CI runs checkpatch?

## Comments and kernel-doc seam
**Path/Symbol:** exported functions and file headers.
**Signature:** WHAT/WHY comments; kernel-doc on public API; block comment ` *` column.
**Data Shape:** `tools/docs/kernel-doc`; one data decl per line.

### Decisive pattern
```c
/**
 * count_active_users() - Return number of active users.
 * @state: global state pointer.
 *
 * Return: active user count or negative errno.
 */
int count_active_users(struct state *state)
{
	...
}
```

**Flow:** comment WHAT code does, not HOW — keep function-body comments minimal → document exported/kernel API with kernel-doc; avoid boilerplate repeating the signature → use multi-line block style with asterisk column → declare one data object per line so each may carry a brief use comment → do not break user-visible message strings for grep convenience (see printk rules in style guide).
**Invariant:** exported symbol without kernel-doc update fails upstream API documentation review.
**Probe:** `./scripts/kernel-doc` or maintainers check; checkpatch on patch.

## Macro seam
**Flow:** prefer `static inline` over function-like macros → multi-statement macros use `do { ... } while (0)` → never use macros that `return` from the caller, depend on magic local names, assign to macro args (l-values), or omit parentheses on expression constants → enum preferred for related constants; `#define CONSTANT` caps for scalar constants.
**Invariant:** control-flow macro disguised as function call fails kernel macro policy.
**Probe:** grep new `#define` with `return` or unparenthesized expressions.

## Memory seam
```c
p = kmalloc_obj(*p, GFP_KERNEL);
arr = kmalloc_objs(*arr, n, GFP_KERNEL);
```

**Flow:** size allocations with `kmalloc_obj(*ptr, ...)` / `kmalloc_objs(*ptr, n, ...)` tied to pointer type — not bare `sizeof(struct foo)` disconnected from variable → do not cast `void *` allocator returns → check NULL; default allocators already warn on failure — avoid redundant failure printk.
**Invariant:** `kmalloc(sizeof(struct foo), ...)` when `foo` type changes independently fails bug-risk review.
**Probe:** grep allocator calls in diff for `_obj` forms.

## Verify seam
**Flow:** run `scripts/checkpatch.pl` on patches before submit → optional `scripts/Lindent` or `indent -kr -i8` for formatting (not a substitute for clear code) → follow tree `.editorconfig`; clang-format only where documented → fix trailing whitespace and checkpatch warnings on touched files.
**Invariant:** checkpatch errors on style or obvious issues block many subsystem maintainers.
**Probe:**
```bash
./scripts/checkpatch.pl --strict --file path/to/file.c
# or on patch:
./scripts/checkpatch.pl --strict patchfile.patch
```

## Verdict
kernel-doc on exports, safe macros/inline, kmalloc_obj sizing, checkpatch gate. Learning note: `linux-kernel-style-learning-note.md`.
