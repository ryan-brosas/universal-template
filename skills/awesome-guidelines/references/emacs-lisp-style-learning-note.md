# Emacs Lisp style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `emacs-lisp-style-*.md` capsules, `emacs-lisp-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [bbatsov/emacs-lisp-style-guide](https://github.com/bbatsov/emacs-lisp-style-guide) (primary) | spaces not tabs; Emacs indent rules; lexical-binding; lisp-case; library prefixes; `--` private; `-p` predicates; when/unless; `#'` sharp quote; macro vs function; provide/require/autoload; docstrings; comment levels; checkdoc/package-lint |
| [GNU Emacs Lisp Tips (tips.texi)](https://www.gnu.org/software/emacs/manual/html_node/elisp/Tips.html) (secondary) | loading must not change behavior; prefix globals; lexical-binding recommended; require not load; eval-when-compile for macros; cl-lib not cl; no hanging parens; reserved C-c keys; error message format; library header template |

**Not duplicated here:** Full major/minor mode API — use stack foundations. Every Flycheck rule — enable project-relevant linters.

## Mental model

Emacs Lisp style is **Emacs-native regularity + namespace hygiene**:

1. **Layout** — spaces only; trust `emacs-lisp-mode` indent; ≤80 columns; no hanging close-parens; blank lines between top-level forms; `;;; -*- lexical-binding: t; -*-` first line.
2. **Names** — `lisp-case`; library prefix on globals (`projectile-`); `--` for private; `-p` / `p` predicates; no `*-face` suffix on faces.
3. **Functions & macros** — prefer functions; `when`/`unless`; `#'` for function symbols; no hard-quoted lambdas; named functions for hooks; `cl-defun` keywords when >3 positional args.
4. **Packages** — standard file header; `require` idempotent loads; `(provide 'feature)` footer; autoload cookies only for user-facing defs; loading must not alter user config.

## Decision tables

### Layout & file header

| Topic | Rule |
|---|---|
| Indent | spaces (`indent-tabs-mode nil`); Emacs `=` reindents |
| Line length | ≤80 when feasible |
| Parens | trailing `)` on same line as body; space around non-adjacent parens |
| Top-level | blank line between forms; group related `defconst`s |
| Lexical | `;;; -*- lexical-binding: t; -*-` on line 1 |
| Header | `;;; foo.el --- Summary`; copyright; Author; Keywords; `provide` + `;;; foo.el ends here` |

### Naming

| Entity | Convention |
|---|---|
| Functions/vars | `lisp-case` (`some-fun`) |
| Globals | `library-prefix-name` |
| Private top-level | `library--private-fun` |
| Predicates | `evenp`, `buffer-live-p` |
| Unused locals | `_y` prefix |
| Faces | `widget-inactive` not `widget-inactive-face` |
| File/dir vars | `file-name` not `path` (GNU) |

### Syntax & functions

| Case | Rule |
|---|---|
| Multi-form if | `when` / `unless` not `(if ... (progn ...))` |
| else in if | no extra `progn` (implicit) |
| Boolean test on list | `null` for nil list; `not` elsewhere |
| cond default | `t` not `:else` |
| Compare range | `(< 5 x 10)` |
| Increment | `1+` / `1-` |
| Quote fn | `#'symbol` not `'symbol` |
| Lambda | never `'(lambda ...)`; named fn for hooks/keys |
| Side-effect loop | `dolist` / `seq-do` not `mapcar` discard |
| Deferred load | `with-eval-after-load` (personal); libraries avoid eval-after-load (GNU) |

### Macros & packages

| Topic | Rule |
|---|---|
| Macro need | only when compile-time transform required |
| Macro body | delegate to plain functions; `(declare (debug ...))` |
| Load deps | `require` not `load`; macro-only dep → `eval-when-compile` |
| Autoload | modes, setup commands — not internals/globals |
| Behavior on load | no side effects; explicit enable command (GNU) |
| CL extensions | `cl-lib` not deprecated `cl` |

### Docs & comments

| Level | Use |
|---|---|
| `;;;` | file/section heading |
| `;;` | purpose before code block |
| `;` | end-of-line margin (right-aligned in GNU style) |
| Docstring | imperative first sentence; args in UPCASE; no indent on continuation lines |
| Tools | `checkdoc`, `package-lint` |

## Anti-patterns

- Hard tabs or Windows CRLF in `.el` files
- Dynamic scoping on new files (missing lexical-binding)
- Unprefixed global symbols in libraries
- Hard-quoted lambdas in hooks/customs
- Anonymous lambdas for keymaps/hooks that should be named
- `(if pred (progn ...))` instead of `when`
- Hanging close-paren on its own line
- Autoload cookies on internal helpers or top-level setup side effects
- Loading a library that immediately changes user editing behavior
- `eval-after-load` in library code (GNU)
- `cl` instead of `cl-lib`
- Docstrings with indented continuation lines
- Binding `C-c letter` in packages (reserved for users)
- More than 3–4 positional parameters without keywords

## Skill trace

| Artifact | Role |
|---|---|
| `emacs-lisp-style-formatting-layout.md` | indent, parens, lexical-binding, line length |
| `emacs-lisp-style-naming-prefixes.md` | lisp-case, prefixes, private, predicates |
| `emacs-lisp-style-functions-macros.md` | when/unless, quotes, lambdas, macros |
| `emacs-lisp-style-packages-docs.md` | headers, require/provide/autoload, docstrings |
| `emacs-lisp-coding-practices/SKILL.md` | checkdoc/package-lint/byte-compile in CI |
