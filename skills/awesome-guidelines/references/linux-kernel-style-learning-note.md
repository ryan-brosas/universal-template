# Linux kernel C style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `linux-kernel-style-*.md` capsules, `linux-kernel-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Linux kernel coding style](https://www.kernel.org/doc/html/latest/process/coding-style.html) (primary; `coding-style.rst.txt`) | 8-char tab indent; 80 columns; K&R non-function braces; function `{` next line; switch/case alignment; spaces; naming; typedef limits; short functions; goto cleanup; kernel-doc; macro rules; kmalloc_obj; checkpatch/indent |
| `c-coding-practices` / CMU baseline (secondary) | Shared C safety themes — kernel doc supersedes layout; keep error-path discipline aligned with §7 goto patterns |
| GNU coding standards (secondary contrast) | **Not kernel** — GNU uses 2-space, space before `(`, defun column-1 braces (`gnu-c-coding-practices`) |

**Scope:** C (and style-adjacent rules) in **Linux kernel** trees. **Userspace:** not this skill. **Out-of-tree modules:** follow kernel style when targeting upstream merge.

## Mental model

Kernel C quality is **tab-based readability for reviewers and checkpatch**:

1. **Indent/braces** — tabs (width 8); 80-column lines; opening `{` on same line for control flow; function `{` on next line; `switch`/`case` same column.
2. **Naming/types** — descriptive globals; short locals (`i`, `tmp`); no Hungarian notation; typedef only for opaque/size/sparse types (`u32`, `pte_t`).
3. **Functions/goto** — one job per function; named parameters in prototypes; multi-exit cleanup via descriptive `goto` labels; split `err_free_*` labels.
4. **Macros/verify** — prefer `static inline` over function-like macros; kernel-doc on exported API; `kmalloc_obj`; `scripts/checkpatch.pl` + `scripts/Lindent`.

## Decision tables

### Indentation & lines

| Topic | Rule |
|---|---|
| Indent | tabs only (8-char visual depth); no spaces for code indent |
| Nesting | >3 levels → refactor |
| Line length | 80 columns preferred |
| Wrap | break into sensible chunks; align under `(` for arg lists |
| Strings | do not break user-visible `printk`/grep strings |
| Trailing WS | none — git/checkpatch warn |

### Braces & control flow

| Topic | Rule |
|---|---|
| if/switch/for/while/do | `{` end of header line; `}` own line |
| Functions | `{` on line after signature |
| `} else` | `else`/`while` on same line as closing `}` when continuing |
| Single statement | braces optional if both branches single; if one branch multi, brace both |
| switch | `case` labels same column as `switch` (not double-indented) |
| fallthrough | use `fallthrough;` macro where intentional |
| One line | no multiple statements/assignments per line; no comma tricks |

### Spaces & pointers

| Topic | Rule |
|---|---|
| Keywords | space after `if`, `switch`, `case`, `for`, `do`, `while` |
| No space after | `sizeof`, `typeof`, `alignof`, `__attribute__` |
| Parens | no spaces inside `( )` |
| Pointers | `char *p` — `*` with name not type |
| Binary ops | space around `= + - < > * / % \| & ^ == != ? :` |
| Unary | no space after `& * + - ~ !`; postfix `++`/`--` tight |

### Naming & typedefs

| Topic | Rule |
|---|---|
| Globals / exported | descriptive (`count_active_users`), not `foo`/`cntusr` |
| Locals | short when clear (`i`, `tmp`) |
| MixedCase | frowned upon |
| Hungarian | avoid |
| Inclusive terms | avoid new master/slave, blacklist/whitelist — use primary/replica, denylist/allowlist unless ABI/spec mandates |
| typedef | avoid struct/pointer typedefs except opaque (`pte_t`), sized integers (`u32`), sparse types, config-dependent width |

### Functions & exit paths

| Topic | Rule |
|---|---|
| Length | short; ~1–2 screens; split complex logic |
| Locals count | ~5–10 max — else split |
| Prototypes | include parameter names; no `extern` on declarations |
| Element order | storage class → attrs → return → name → params (documented order) |
| Export | `EXPORT_SYMBOL()` immediately after closing `}` |
| goto | OK for shared cleanup; descriptive labels (`out_free_buffer`); split chained free labels |

### Comments & docs

| Topic | Rule |
|---|---|
| Focus | WHAT/WHY, not HOW; avoid in-function essay comments |
| Exported API | kernel-doc format |
| Block style | `/*` + ` *` column + ` */` |
| Data | one declaration per line with short comment |

### Macros & memory

| Topic | Rule |
|---|---|
| Constants | `#define`/`enum` CAPS |
| Function-like | prefer `static inline`; `do { } while (0)` if macro |
| Avoid | control-flow macros, magic local names, l-value macro args |
| Alloc | `kmalloc_obj(*p, ...)`, `kmalloc_objs(*p, n, ...)`; no cast on void* |
| OOM | check NULL; no extra printk on default allocator failure |

### Tooling

| Tool | Use |
|---|---|
| `scripts/checkpatch.pl` | patch review gate |
| `scripts/Lindent` / `indent -kr -i8` | reformat (not substitute for clarity) |
| `clang-format` | limited helpers per `Documentation/dev-tools/clang-format.rst` |
| EditorConfig | kernel `.editorconfig` for basics |

## Anti-patterns

- Spaces used for code indentation
- Lines >80 without good reason
- Function `{` on same line as signature (non-kernel style)
- Double-indenting `case` labels under `switch`
- `sizeof( struct file )` with inner spaces
- `char* p` pointer star on type side
- Terse global names (`foo`, `cntusr`)
- gratuitous `typedef struct { ... } foo_t`
- Function-like macro that `return`s from caller
- Single `err:` label freeing nullable nested pointers
- Breaking grep strings in printk messages
- Casting `kmalloc` return value
- `sizeof(struct foo)` not tied to pointer variable type
- Applying GNU/httpd indent rules to kernel patches
- New master/slave or blacklist/whitelist terminology without ABI excuse

## Skill trace

| Artifact | Role |
|---|---|
| `linux-kernel-style-indent-braces.md` | tabs, 80 cols, braces, switch |
| `linux-kernel-style-naming-types.md` | names, typedefs, inclusive terms |
| `linux-kernel-style-functions-goto.md` | size, prototypes, goto cleanup |
| `linux-kernel-style-macros-verify.md` | macros, kernel-doc, alloc, checkpatch |
| `linux-kernel-coding-practices/SKILL.md` | kernel patch review workflow |

## Relation to sibling skills

| Topic | Kernel | GNU | httpd | generic C |
|---|---|---|---|---|
| Indent | tabs (8) | 2 spaces | 4 spaces | project |
| Space before `(` | no | yes | no | varies |
| Function `{` | next line | column 1 | next line aligned | K&R common |
| goto cleanup | encouraged | sparse | rare | cautious |
| Docs | kernel-doc | block comments | rationale comments | project |
| Verify | checkpatch | make check | httpd build | -Wall |
