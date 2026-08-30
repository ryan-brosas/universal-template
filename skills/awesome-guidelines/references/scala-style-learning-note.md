# Scala style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `scala-style-*.md` capsules, `scala-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Scala Style Guide](https://docs.scala-lang.org/style/) (primary) | 2-space indent; line wrap rules; naming (Upper/lower camelCase); package Java conventions; accessor/`name_=` mutators; parentheses = side effects; avoid symbolic methods; type inference vs public explicit types; control-structure spacing; Scaladoc |
| [Databricks Scala Guide](https://github.com/databricks/scala-style-guide) (secondary) | 100-char lines; rule of 30; explicit types on public methods; `override` always; immutable case classes; avoid `return` in closures; avoid `null`/`Option.get`; symbolic methods banned except arithmetic; `@tailrec` when recursive |
| [Scala Best Practices](https://github.com/alexandru/scala-best-practices) (secondary) | no `return`; immutable data; no `var` in case class; no catch `Throwable`; explicit public return types; case classes final |

**Not duplicated here:** Akka actor/Cake pattern chapters — use stack capsules in `foundation-pack/`. Full Scalafmt config — project formatter wins.

## Mental model

Scala style in this catalog is **official layout/naming plus functional-safety idioms**:

1. **Layout** — 2 spaces; wrap with continued indent; space after `if`/`for`/`while`; functional `if` may omit braces when single-expression.
2. **Naming** — UpperCamelCase types; lowerCamelCase members; Java-style packages; acronyms as words (`maxId`); parentheses signal effects on nullary methods.
3. **Types** — infer locally when obvious; explicit types on all public methods; `A => B` spacing; prefer immutable `val` and case classes.
4. **API & docs** — Scaladoc on packages/types/methods; `override` always; Option over null; avoid symbolic operators except DSL/math.

## Decision tables

### Formatting

| Topic | Rule |
|---|---|
| Indent | 2 spaces, no tabs |
| Line length | ~80–100 (project standard) |
| Wrap | +2 spaces from first line of expression |
| Control | space after keyword (`if (x)`) |
| Functional if | omit braces when both branches single expr |
| Multi-gen for | braces + `yield`; loop form uses `;` in parens |

### Naming

| Element | Convention |
|---|---|
| Class/trait/object | UpperCamelCase |
| Method/val/var | lowerCamelCase |
| Package | lowercase reverse-DNS |
| Constant (official) | UpperCamelCase in object (`Pi`) |
| Constant (Spark style) | SCREAMING_SNAKE in companion — pick one per repo |
| Type param | `A`, `B` or descriptive `Key`, `Value` |
| Mutator | `prop_=(v)` with accessor `prop` |
| Acronyms | treat as words (`xHtml`, not `XHTML`) |

### Nullary methods

| Declaration | Call | Meaning |
|---|---|---|
| `def foo` | `foo` | accessor-like, no side effect |
| `def foo()` | `foo()` | may have side effects |

### Types & immutability

| Case | Rule |
|---|---|
| Private/local | infer when obvious |
| Public method | explicit return type |
| Case class | immutable params; prefer `final` |
| Override | always `override` keyword |
| Option | no `.get`; no `null` |
| Exceptions | don't use for validation flow; don't catch `Throwable` |

### API design

| Case | Rule |
|---|---|
| Symbolic methods | avoid except `+`, `::`, DSL |
| `return` | avoid in closures; guard OK at method level |
| Scaladoc | every package/class/trait/method |
| Implicits | minimize; explicit types on implicit defs |

## Anti-patterns

- 4-space indent or tabs
- `XHTML` acronym casing
- `def update()` instead of `name_=`
- Side-effect nullary method without `()`
- `channel ! msg` in general API (symbolic)
- `Option.get` / `null`
- `var` in case class
- Missing `override`
- Public method without return type
- `return` inside `{ ... }` callback/async closure

## Skill trace

| Artifact | Role |
|---|---|
| `scala-style-formatting-layout.md` | indent, wrap, control spacing |
| `scala-style-naming-packages.md` | names, packages, accessors, parens |
| `scala-style-types-immutability.md` | inference, case classes, override, Option |
| `scala-style-control-api.md` | return, for, Scaladoc, symbolic bans |
| `scala-coding-practices/SKILL.md` | Scalafmt/Scalafix in CI |
