# Apache httpd C style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `httpd-style-*.md` capsules, `httpd-c-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Apache Developers' C Language Style Guide](https://httpd.apache.org/dev/styleguide.html) (primary) | 4-space indent; no tabs; 80-col wrap; K&R-ish braces; ANSI prototypes; function/call spacing; switch case indent; operator/cast spacing; comments at code indent |
| GNU `indent` recipe on same page (primary) | `-i4 -npsl -di0 -br -nce -d0 -cli0 -npcs -nfc1 -nut` |
| `c-coding-practices` / CMU baseline (secondary) | httpd covers layout; keep CMU safety rules (init-all, header discipline, error checks) when not contradicted |

**Scope:** C code for **Apache httpd** and compatible modules/patches. Generic portable C without httpd tree: use `c-coding-practices`. Linux kernel/GNU tabs: follow local tree docs.

## Mental model

httpd C quality is **readable layout for reviewers** — short functions, explicit ANSI signatures, consistent indent/wrap:

1. **Indent/format** — four spaces, never tabs; 80 columns; GNU indent profile.
2. **Functions/flow** — return type line; void when no args; if/else/switch/for brace rhythm.
3. **Expressions/casts** — spaced binary operators; unary tight; `(type)*` pointer casts.
4. **Comments/verify** — rationale comments; reformat with project indent flags; `-Wall` + project tests.

## Decision tables

### Formatting

| Topic | Rule |
|---|---|
| Indent | 4 spaces per level; never tabs |
| Line length | wrap past column 80; continuation under first term |
| Braces open | same line as statement or line after function signature |
| Braces close | own line; align with text start of opening line |
| Comments | indent to surrounding code level |
| Tooling | GNU indent args from style guide |

### Functions

| Topic | Rule |
|---|---|
| Declarations | ANSI prototypes; `void` if no parameters |
| Name/paren | no space before `(` in def/call |
| Commas | single space after commas in arg lists |
| Layout | return type on same line as name; `{` on next line aligned with return type text |
| Length | short, understandable (intro guidance) |

### Control flow

| Topic | Rule |
|---|---|
| if/while/for | space after keyword; `{` on same line as keyword line |
| else | on line after closing `}`; aligned with matching `if` |
| for | space after `;` separators |
| switch | `case` aligned with `switch`; case body +4 spaces |
| Long conditions | wrap keeping terms atomic; boolean ops at line start (preferred) or end |

### Expressions

| Topic | Rule |
|---|---|
| Binary ops | space before and after |
| Unary | no space (`++a`, `!b`, `-b`) |
| Casts | no space after cast: `(int)j` |
| Pointer casts | space before `*`: `(char *)i` not `(char*)i` |

### Comments & clarity

| Topic | Rule |
|---|---|
| When | non-obvious code; function behavior; rationale |
| Style | same indent as code; explain why not what |
| Break rules | allowed when clarity improves layout (intro note) |

## Anti-patterns

- Tab characters for indentation
- Lines >80 without intentional wrap
- Non-ANSI function declarations (K&R params)
- Space between function name and `(`
- Missing space after comma in calls
- `case` labels indented inside case body level incorrectly
- Space after cast `(int) j`
- Missing space in pointer cast `(char*)i`
- Cryptic code without rationale comments
- Overlong functions without decomposition
- Applying httpd brace rules to kernel tab-based trees without project approval
- Replacing CMU/httpd safety checks (error paths, headers) with layout-only review

## Skill trace

| Artifact | Role |
|---|---|
| `httpd-style-formatting-indent.md` | spaces, 80 cols, indent tool |
| `httpd-style-functions-flow.md` | ANSI functions, if/else/switch |
| `httpd-style-expressions-casts.md` | operators, wraps, casts |
| `httpd-style-comments-verify.md` | comments, indent verify, build |
| `httpd-c-coding-practices/SKILL.md` | httpd patch/module CI |

## Relation to `c-coding-practices`

| httpd-specific | Keep from generic C skill |
|---|---|
| 80-col + GNU indent profile | initialize all variables |
| Cast spacing rules | no data in headers |
| switch case column alignment | checked malloc/syscall returns |
| httpd brace alignment examples | safe macros / Yoda if team uses |
