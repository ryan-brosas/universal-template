<!-- capsule-v2 -->
# Headers and modules — are declarations separated from definitions?

**Source:** CMU C Coding Standard §Miscellaneous/Structures; Linux kernel §Headers. **Question:** Will linking succeed and includes stay minimal?

## Header guard seam
**Path/Symbol:** `.h` public headers paired with `.c` implementation.
**Signature:** include guard; no variable definitions in headers.
**Data Shape:** `extern` declarations in `.h`; single owning `.c` for globals.

### Decisive pattern
```c
/* connection_pool.h */
#ifndef myapp_connection_pool_h
#define myapp_connection_pool_h

#include <stdint.h>

struct connection_pool;

int connection_pool_init(struct connection_pool *pool, int max_conn);
void connection_pool_destroy(struct connection_pool *pool);

#endif /* myapp_connection_pool_h */
```

```c
/* connection_pool.c */
#include "connection_pool.h"

static int g_pool_count;  /* file scope if needed */

int connection_pool_init(struct connection_pool *pool, int max_conn) {
    ...
}
```

**Flow:** guard macro without leading/trailing `_` → include what you use → never define variables in `.h` → `extern` in header + one `.c` definition → document include blocks.
**Invariant:** `int x = 0;` in a header or missing include guard fails review.
**Probe:** link multiple TUs including header — no multiply-defined symbols; include-what-you-use clean.

## Layering seam
**Flow:** modules talk through adjacent layers via narrow headers → document cross-layer jumps (performance) → keep structs opaque when possible (`struct foo;` forward decl).
**Invariant:** `.h` including half the tree for one enum fails review.
**Probe:** dependency graph / layering check on new includes.

## Verdict
Guarded headers, extern/define split, no header data, controlled layering. Learning note: `c-style-learning-note.md`.
