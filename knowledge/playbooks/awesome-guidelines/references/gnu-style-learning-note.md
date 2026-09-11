# GNU C coding standards — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `gnu-style-*.md` capsules, `gnu-c-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [GNU Coding Standards — Writing C](https://www.gnu.org/prep/standards/html_node/Writing-C.html) (primary; `standards.texi` tarball when HTML subpages 403) | 79-column lines; function open-brace column 1; GNU `indent` flags; spaces before `(`; nested brace style; comments; syntactic conventions; naming; Gnulib/Autoconf portability |
| [GNU Coding Standards — Program Behavior](https://www.gnu.org/prep/standards/html_node/Program-Behavior.html) (primary; texi) | Check syscalls and `malloc`/`realloc`; fatal vs interactive OOM; `strerror` in errors; `getopt_long`; avoid low-level struct hacks |
| Linux kernel coding style (secondary pointer) | Overlapping C themes — **kernel uses tabs/8-col**; do not apply kernel layout to GNU tree without local override |
| `c-coding-practices` (secondary) | Shared portable C safety (init, headers) — GNU adds layout, comment, and ecosystem rules |

**Scope:** C code in **GNU packages** (coreutils, binutils, emacs, gnulib consumers). **Apache httpd:** `httpd-c-coding-practices` (4-space, different cast/brace profile). **Linux kernel:** separate style doc.

## Mental model

GNU C quality is **Emacs- and tool-friendly layout plus explicit, documented behavior**:

1. **Formatting** — ≤79 columns; function name column 1; function `{` column 1; 2-space body indent; space before `(`; GNU `indent` recipe.
2. **Naming/files** — lowercase English with underscores; macros/enums ALL_CAPS; meaningful globals; option flags named by meaning not letter.
3. **Comments/conditionals** — English sentences; two spaces after period; per-function and static-var comments; `#endif` annotated with sense.
4. **Constructs/portability** — explicit types; no `extern` inside functions; brace nested `if`/`else`; Autoconf/Gnulib; check syscalls and allocators; `_GNU_SOURCE` on GNU builds.

## Decision tables

### Formatting (GNU indent default)

| Topic | Rule |
|---|---|
| Line length | ≤79 characters |
| Function def | name starts column 1; return type may be on prior line |
| Function `{` | column 1 (defun-friendly for Emacs/tools) |
| Inner `{` | not column 1 inside functions |
| Indent | 2 spaces per level (GNU `indent` 1.2+ defaults) |
| Calls | space before `(` and after `,`: `foo (bar, baz)` |
| Wrap | split before operator; extra parens for nesting clarity |
| `do-while` | `do`/`while` layout per standards example |
| Pages | formfeed (Ctrl-L) alone on line between logical sections (not inside functions) |
| Tooling | `indent -nbad -bap -nbc -bbo -bl -bli2 -bls -ncdb -nce -cp1 -cs -di2 -ndj -nfc1 -nfca -hnl -i2 -ip5 -lp -pcs -psl -nsc -nsob` |

### Naming

| Entity | Convention |
|---|---|
| Functions/globals | lowercase English, words separated by `_` |
| Locals | may be shorter; still clear in context |
| Macros / enum constants | UPPER_CASE |
| Abbreviations | few, documented; avoid `iCantReadThis` |
| CLI flags | variable named for meaning; comment gives letter |
| Integer constants | prefer `enum` over `#define` when integral |
| File names | lowercase; mind `doschk` on hostile FS (legacy 14-char note) |

### Comments

| Topic | Rule |
|---|---|
| Program | top-of-main-file one-liner purpose |
| Each file | name + purpose blurb |
| Language | English |
| Functions | what/args/return; note nonstandard arg uses |
| Sentences | capitalized; two spaces after `.` |
| Arg names in prose | UPPER when meaning value (`NODE_NUM`) |
| Static globals | block comment before each |
| `#endif` | comment condition and sense (except short non-nested) |

### Clean C constructs

| Topic | Rule |
|---|---|
| Types | explicit on all objects and parameters |
| `-Wall` | team choice — compiler is servant not master |
| Lint/clang extras | don't uglify code to silence false positives |
| `extern` | near top of file or in header — never inside function |
| Locals | one purpose per variable; smallest scope |
| Multi-decl | don't span lines with aligned vars — separate lines |
| Nested if/else | always brace inner `if`/`else` chains |
| `else if` | single line `else if` or braced nested `if` |
| Assign in `if` | avoid; split assignment and test |
| struct tag | declare tag separately from typedef/vars |

### Portability & system calls

| Topic | Rule |
|---|---|
| Autoconf/Gnulib | preferred for Unix portability |
| Declarations | never roll your own system function declarations |
| POSIX/C standard | use modern interfaces where clear |
| GNU extensions | OK when they improve maintainability |
| `_GNU_SOURCE` | define when compiling on GNU/glibc |
| `malloc`/`realloc` | check NULL; interactive vs fatal policy |
| Syscalls | check errors; include `strerror` + file + utility name |
| `int` width | assume ≥32 bits; don't target 16-bit |
| Pointer/int casts | avoid when possible |
| `write` bytes | use `unsigned char` buffer, not `&int` |

## Anti-patterns

- Function `{` not in column 1
- Lines >79 without wrap
- `foo(bar)` without space before `(`
- Terse global names hiding meaning
- CamelCase identifiers (`iCantReadThis`)
- Flag variable named only for option letter
- Missing `#endif /* condition */` on nested conditionals
- `extern` declaration inside function body
- Nested `if`/`else` without braces (dangling-else risk)
- Assignment inside `if` condition
- Multi-line split variable declaration block
- Unchecked `malloc`/`realloc`/syscall return
- Error message without `strerror` context
- Custom declaration of libc function (conflict risk)
- Applying kernel 8-tab style to GNU sources
- Applying httpd 4-space/cast rules as if they were GNU defaults

## Skill trace

| Artifact | Role |
|---|---|
| `gnu-style-formatting-layout.md` | 79 cols, defun braces, indent flags |
| `gnu-style-naming-files.md` | identifiers, enums, CLI flags, paths |
| `gnu-style-comments-conditionals.md` | English comments, `#endif` sense |
| `gnu-style-constructs-portability.md` | types, control flow, Gnulib, errors |
| `gnu-c-coding-practices/SKILL.md` | GNU package patch/review workflow |

## Relation to sibling skills

| Topic | GNU | httpd | kernel | generic `c-coding-practices` |
|---|---|---|---|---|
| Indent | 2 spaces | 4 spaces | tabs (8) | project default |
| Function `{` | column 1 | aligned with type text | kernel rules | K&R common |
| Space before `(` | yes | no | kernel differs | project |
| Column limit | 79 | 80 | 80 | 78–80 |
| Ecosystem | Autoconf/Gnulib/gettext | httpd build | kbuild | portable C safety |
