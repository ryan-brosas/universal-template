<!-- capsule-v2 -->
# Macros and safety — are resources and errors handled explicitly?

**Source:** CMU C Coding Standard §Macros, §Initialize, §Error Return; Linux kernel §Functions. **Question:** Will macros expand safely and failures propagate?

## Macro seam
**Path/Symbol:** `#define` helpers and constant expressions.
**Signature:** ALL_CAPS; parenthesized parameters; `do-while(0)` for multi-statement.
**Data Shape:** package-prefixed names; prefer `static inline` for small functions (C99+).

### Decisive pattern
```c
#define MYAPP_STREQ(a, b) (strcmp((a), (b)) == 0)

#define MYAPP_SET_MAX(v, w, x, y)          \
    do {                                   \
        (v) = (x) + (y);                   \
        (w) = (y) + 2;                     \
    } while (0)

static inline int myapp_max(int x, int y) {
    return (x > y) ? x : y;
}
```

**Flow:** parenthesize macro args and whole expression → multi-statement macros use `do { } while (0)` → prefix names to avoid `MAX`/`MIN` clashes → use inline functions when debugging matters.
**Invariant:** `#define ADD(a,b) a + b` or side-effecting macro args fail review.
**Probe:** macro expansion tests; grep for bare `MAX(` without package prefix.

## Initialization and errors seam
```c
int process_file(const char *path) {
    FILE *fp = NULL;
    char *buf = NULL;
    int rc = -1;

    fp = fopen(path, "r");
    if (NULL == fp) {
        goto cleanup;
    }
    buf = malloc(BUF_SIZE);
    if (NULL == buf) {
        goto cleanup;
    }
    rc = 0;
cleanup:
    free(buf);
    if (NULL != fp) {
        fclose(fp);
    }
    return rc;
}
```

**Flow:** initialize every variable at declaration → check every `malloc`/syscall unless explicitly ignored (cast to void) → replace magic numbers with named constants → prefer `#if FLAG` over `#ifdef FLAG`.
**Invariant:** uninitialized locals, unchecked `malloc`, or bare `42` status codes fail review.
**Probe:** `-Wuninitialized` / static analyzer; code review for syscall return checks.

## Verdict
Safe macros, init-all, checked allocations, named constants. Learning note: `c-style-learning-note.md`.
