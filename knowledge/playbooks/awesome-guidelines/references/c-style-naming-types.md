<!-- capsule-v2 -->
# Naming — do identifiers reveal scope and intent?

**Source:** CMU C Coding Standard §Names; Linux kernel §Naming. **Question:** Can readers tell globals from locals and functions from data without hunting declarations?

## Variable and function seam
**Path/Symbol:** C identifiers in application/library code.
**Signature:** snake_case; verb functions; descriptive globals with `g_`.
**Data Shape:** units in names; `is_`/`get_`/`set_` prefixes where helpful.

### Decisive pattern
```c
struct connection_pool {
    struct connection_pool *next;
    int max_connections;
    int active_count;
};

static Logger g_log;

int count_active_users(const struct user_table *table);
bool is_retry_limit_reached(int retry_cnt, int retry_max);
uint32_t timeout_msecs;
```

**Flow:** functions as verbs (`dump_data_to_file`) → locals snake_case → globals `g_` and minimized → include units (`_msecs`, `_lbs`) → predicates `is_*`.
**Invariant:** abbreviated globals (`cntusr`), camelCase locals, or cryptic struct fields fail review.
**Probe:** grep `g_[a-z]` for globals; naming review on new public API.

## Pointer and constant seam
```c
char *name = NULL;
const int MAX_RETRIES = 5;
#define PACKAGE_MAX(a, b) (((a) > (b)) ? (a) : (b))
```

**Flow:** bind `*` to variable name → constants/macros `ALL_CAPS` → enum labels `ALL_CAPS` with error sentinel first when needed.
**Invariant:** `char* a, b` multi-declaration or mixed-case macro names fail review.
**Probe:** declare one pointer per line; macro names prefixed with package/module.

## Verdict
snake_case, g_ globals sparingly, ALL_CAPS constants, pointer star with variable. Learning note: `c-style-learning-note.md`.
