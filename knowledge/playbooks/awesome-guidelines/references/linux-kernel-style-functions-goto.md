<!-- capsule-v2 -->
# Functions and goto — are functions small with named prototypes and safe cleanup paths?

**Source:** Linux kernel coding style §6, §6.1, §7. **Question:** Do functions stay focused, prototypes document parameters, and multi-exit paths use descriptive gotos?

## Function size seam
**Path/Symbol:** function definitions in kernel `.c` files.
**Signature:** one purpose; ~1–2 screens; 5–10 locals max; blank line between functions.
**Data Shape:** helper functions; `EXPORT_SYMBOL()` after exported fn `}`.

### Decisive pattern
```c
int system_is_up(void)
{
	return system_state == SYSTEM_RUNNING;
}
EXPORT_SYMBOL(system_is_up);
```

**Flow:** keep functions short and single-purpose — split when complexity, indentation depth, or local count (~5–10) grows → separate functions with one blank line → for exported symbols, place `EXPORT_SYMBOL(name)` immediately after closing brace → in prototypes include parameter names and follow project element order (storage class, attrs, return type, name, params) → do not use `extern` on function declarations.
**Invariant:** kitchen-sink function with double-digit unrelated locals fails maintainability review.
**Probe:** line count and local variable count spot-check; verify EXPORT placement on new exports.

## Goto cleanup seam
```c
int fun(int a)
{
	int result = 0;
	char *buffer;

	buffer = kmalloc(SIZE, GFP_KERNEL);
	if (!buffer)
		return -ENOMEM;

	if (condition1) {
		result = 1;
		goto out_free_buffer;
	}
out_free_buffer:
	kfree(buffer);
	return result;
}
```

**Flow:** use early `return` when no shared cleanup → for shared cleanup across multiple exits, use `goto` with descriptive labels (`out_free_buffer`, `err_free_bar`) — not `err1`/`err2` → split chained error paths so each label only dereferences non-NULL objects (`err_free_bar:` then `err_free_foo:`) → test all error paths when possible.
**Invariant:** single `err:` label that frees `foo->bar` when `foo` may be NULL fails correctness review.
**Probe:** trace each `goto` label against allocation graph; simulate failure paths mentally or in tests.

## Verdict
Short named functions, EXPORT_SYMBOL placement, parameter-rich prototypes, descriptive goto cleanup labels. Learning note: `linux-kernel-style-learning-note.md`.
