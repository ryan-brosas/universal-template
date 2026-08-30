# Ruby style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `ruby-style-*.md` capsules, `ruby-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [The Ruby Style Guide](https://rubystyle.guide) (RuboCop canonical) | 2-space indent; 80-char lines (up to 120 by team agreement); UTF-8; snake_case methods/files; CapitalCase classes; SCREAMING_SNAKE constants; `?`/`!` suffix rules; spacing; safe navigation; class layout; explicit namespace nesting; `module_function`; exception discipline; `&&`/`||` vs `and`/`or` |
| [Airbnb Ruby Style Guide](https://github.com/airbnb/ruby) (secondary) | keyword arguments over positional defaults; parentheses on value-returning calls; no class variables (`@@`); `def self.method`; access modifier spacing |

**Not duplicated here:** Rails/RSpec style guides — use `foundation-pack/*-foundation` when framework is known. Full hash-literal spacing debates — project RuboCop config wins.

## Mental model

Ruby style in this catalog is **RuboCop-community mechanical layout plus idiomatic naming and exception discipline**:

1. **Layout** — 2-space soft tabs, Unix LF, one expression per line, spaces around operators, trailing newline, no semicolons.
2. **Naming** — English identifiers; `snake_case` methods/variables/files; `CapitalCase` classes/modules (HTTP acronyms uppercase); predicates `?`, dangerous mutators `!` only with safe counterpart.
3. **Methods** — keyword args over positional defaults; parentheses when passing args or receiving values; short methods; blocks and endless methods only when single-expression and side-effect free.
4. **Classes & errors** — consistent class skeleton; explicit `module` nesting; no `@@` class variables; rescue `StandardError`, not flow control; never suppress without comment.

## Decision tables

### Layout (RuboCop guide)

| Topic | Rule |
|---|---|
| Indent | 2 spaces, no tabs |
| Line length | 80 default; team may allow 100–120 consistently |
| Encoding | UTF-8 |
| Endings | LF; file ends with newline |
| Operators | spaces around `=`, `+`, etc.; `{`/`}` spacing per hash/block style |
| Safe nav | `foo&.bar` not `foo && foo.bar` chains |
| Semicolons | never terminate statements |

### Naming

| Element | Convention | Example |
|---|---|---|
| Method/variable | snake_case | `some_method`, `some_var` |
| Class/module | CapitalCase | `SomeClass`, `SomeXML` |
| Constant | SCREAMING_SNAKE | `MAX_ITEMS` |
| File/dir | snake_case | `some_class.rb` |
| Predicate | `?` suffix | `empty?`, not `is_empty?` |
| Mutator | `!` if safe version exists | `save!` vs `save` |
| Discard | `_` | `a, b, _ = split` |

### Methods

| Case | Rule |
|---|---|
| Definition | `def foo` no parens; `def foo(x)` with parens |
| Calls returning value | use parens: `User.find(id)` |
| Calls no args | omit parens: `fork`, `empty?` |
| Defaults | keyword args (`gently: true`) not positional defaults |
| Boolean logic | `&&`/`||` in conditions; `and`/`or` for control flow only |
| Length | aim ≤10 LOC; avoid top-level defs outside scripts |

### Classes & modules

| Case | Rule |
|---|---|
| Structure | extend/include → constants → macros → class methods → `initialize` → public → protected/private |
| Mixins | one `include` per line |
| Singleton methods | `def self.method` not `def Class.method` |
| Namespace | explicit `module Foo; class Bar` not `class Foo::Bar` |
| Utility modules | `module_function` over `extend self` |
| Class variables | avoid `@@` |

### Exceptions

| Case | Rule |
|---|---|
| Flow control | guard clauses / `if d.zero?` — not rescue for logic |
| Rescue target | `StandardError` or bare `rescue => e`; never `Exception` |
| Suppress | forbidden unless commented why |
| Modifier rescue | avoid `read rescue nil` |
| raise form | `raise MyError, 'msg'` not `.new` instance |
| ensure | never `return` from ensure |

## Anti-patterns

- 4-space indent in shared Ruby code
- `def SomeMethod` / `someVar` camelCase
- `is_empty?` predicate prefix
- `update!` without non-bang counterpart
- `class Utilities::Store` (surprising constant lookup)
- `@@count` class variables
- `begin; n/d; rescue ZeroDivisionError` for expected branch
- `rescue Exception`
- Positional default arg list (`def f(a, b = true, c = [])`)

## Skill trace

| Artifact | Role |
|---|---|
| `ruby-style-formatting-layout.md` | indent, lines, spacing, safe nav |
| `ruby-style-naming-files.md` | identifiers, files, ?/! |
| `ruby-style-methods-blocks.md` | defs, calls, keywords, and/or |
| `ruby-style-classes-exceptions.md` | class layout, modules, rescue/raise |
| `ruby-coding-practices/SKILL.md` | when/how to run RuboCop |
