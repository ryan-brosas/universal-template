# R style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `r-style-*.md` capsules, `r-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Tidyverse style guide](https://style.tidyverse.org/) (primary) | snake_case; `<-`; 2-space indent; `\|>` pipe; 80 cols; braces/ control flow; roxygen2; styler + lintr; explicit `return` only early |
| [Google R Style Guide](https://google.github.io/styleguide/Rguide.html) (secondary) | fork of tidyverse; **BigCamelCase** functions; `.PrivateFunc`; always explicit `return()`; `pkg::fun()` qualification; no `attach()`; **no** right-hand `->` assignment |

**Baseline:** adopt tidyverse + styler/lintr unless project AGENTS declares Google R guide (then apply naming/return/namespace deltas).

## Mental model

Modern R style is **pipe-first data verbs + mechanical formatting**:

1. **Syntax/layout** — 2-space indent; aligned `}`; spaces around infix; `<-` not `=`; no semicolons.
2. **Naming/files** — snake_case (tidyverse) or BigCamelCase (Google); verb functions; machine/human-readable filenames.
3. **Functions/pipes** — native `|>`; one primary object per pipe; early `return` in own block; `\()` short lambdas.
4. **Docs/verify** — roxygen2 markdown; qualified imports (Google); styler + lintr in CI.

## Decision tables

### Syntax & layout

| Topic | Rule |
|---|---|
| Assign | `<-` not `=` |
| Indent | 2 spaces inside `{}` |
| Braces | `{` last on line; `}` first on line |
| Commas | space after, never before |
| Calls | no space before `(` for regular calls |
| if/for/while | space before `(` |
| Infix | spaces around `==`, `+`, `<-`; exceptions: `::`, `$`, `^`, `:`, unary `-` |
| Lines | ~80 chars; break long calls one arg per line |
| Semicolons | avoid |
| Logical | `TRUE`/`FALSE` not `T`/`F` |
| Strings | double quotes default |

### Naming (pick project baseline)

| Entity | Tidyverse | Google |
|---|---|---|
| Objects/vars | snake_case | snake_case (moving away from dot.case) |
| Functions | snake_case verbs | BigCamelCase verbs |
| Private | leading `_` internal | `.DotPrefixed` |
| Packages in code | `pkg::fun()` preferred at Google | `pkg::fun()` required |
| Avoid | shadow `c`, `mean`, `T` | same |

### Functions & pipes

| Case | Rule |
|---|---|
| Pipe | `\|>` with space before; newline after; +2 indent steps |
| magrittr | avoid `%>%` in new code unless needed |
| Pipe scope | one primary object; name intermediates when helpful |
| Assignment | `x <- data \|> …` (Google: no `->` at pipe end) |
| Return | tidyverse: implicit last value; explicit only early returns in `{}` block |
| Return | Google: always `return()` |
| Anonymous | `\ (x) x + 1` short; `function(x) {` multi-line |
| Control | `&&`/`||` in `if`; no vector `&`/`|` in conditions |
| attach | never |

### Files & docs

| Case | Rule |
|---|---|
| Filenames | lowercase; `-` or `_`; `.R` extension |
| Script structure | libraries at top; `# ----` section breaks |
| Roxygen | sentence title; `@param` sentences; `@noRd` internal |
| Google imports | `@importFrom` per function; avoid `@import` whole package |

## Anti-patterns

- `=` assignment
- `T`/`F` instead of TRUE/FALSE
- Dots in function names (S3 confusion)
- CamelCase/snake mix without project rule
- `%>%` in new tidyverse-first code
- Right-hand `->` (Google ban; tidyverse discouraged vs `<-` at start)
- Implicit return when Google baseline
- Unqualified external functions in Google codebase
- `@import` entire package (Google)
- `attach()`
- Semicolons / multiple statements per line
- Single-line braced `if` bodies
- `if (length(x))` numeric coercion
- `&`/`|` in scalar `if`
- `if (x > 0) return(x)` same line
- Partial arg matching (`t = 3`)
- Assignment inside call `(x <- f())`
- Overlong unbroken pipes
- `~` formula lambdas for new short anonymous fns
- Spaces inside `{{ }}` embracing
- Final/final2 filenames
- Missing roxygen on exported functions

## Skill trace

| Artifact | Role |
|---|---|
| `r-style-formatting-syntax.md` | spacing, braces, assignment |
| `r-style-naming-files.md` | snake_case vs BigCamelCase, files |
| `r-style-functions-pipes.md` | pipes, return, control flow |
| `r-style-docs-verify.md` | roxygen, namespaces, styler/lintr |
| `r-coding-practices/SKILL.md` | styler/lintr/testthat in CI |
