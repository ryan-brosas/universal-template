# Java style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `java-style-*.md` capsules, `java-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html) | 2-space indent, 100 cols, K&R braces, no wildcard imports, one class per file, naming (UpperCamelCase/lowerCamelCase/UPPER_SNAKE_CASE), deterministic camelCase for acronyms, `@Override`, don't ignore caught exceptions, qualify statics, Javadoc on public API |
| [Alibaba Java Coding Guidelines](https://alibaba.github.io/Alibaba-Java-Coding-Guidelines/) (secondary) | `@Override` mandatory, `equals` on constant, POJO wrapper types, override hashCode with equals, collection footguns, exception/logging discipline, no magic values |

**Not duplicated here:** Spring/EE stack patterns — use `*-foundation` when stack is known. Full Alibaba layer naming (DO/DTO/VO) — optional enterprise convention, not universal.

## Mental model

Java style in this catalog is **Google mechanical + Alibaba defensive API habits**:

1. **Format** — spaces not tabs, 2-space indent, 100-char limit, one statement per line, braces always for control flow.
2. **File shape** — one public top-level class per file; imports: static group then non-static, ASCII sorted, no `*`.
3. **Naming** — no Hungarian prefixes (`mName`); classes `UpperCamelCase`, members `lowerCamelCase`, true constants `UPPER_SNAKE_CASE`; acronym camelCase algorithm (`XmlHttpRequest`).
4. **Practices** — `@Override` always; catch blocks explain or handle; static calls qualified by class; no `finalize`.
5. **Docs** — Javadoc on visible API with summary fragment (noun/verb phrase as sentence).

## Decision tables

### Formatting & imports

| Topic | Rule |
|---|---|
| Indent | 2 spaces |
| Width | 100 characters |
| Braces | required on if/for/while/do even single-line |
| Imports | no wildcard; static then non-static; ASCII sort |
| Files | `ClassName.java` matches top-level class |

### Naming

| Item | Convention |
|---|---|
| Package | lowercase, no underscores |
| Class/interface | UpperCamelCase |
| Method/field/param | lowerCamelCase |
| Constant | UPPER_SNAKE_CASE (deeply immutable static final only) |
| Test class | `*Test` |
| Acronyms | Google algorithm (`XmlHttpRequest`, `newCustomerId`) |

### Programming practices

| Case | Rule |
|---|---|
| Override | `@Override` whenever legal |
| Catch | never empty without comment; log/rethrow/wrap |
| Static access | `Foo.method()` not `instance.method()` |
| equals | prefer constant.equals(var) (Alibaba) |
| POJO fields | wrappers for nullable domain (Alibaba); no magic literals |
| finalize | do not use |

### Javadoc

| Element | Rule |
|---|---|
| Visibility | all public/protected classes and members |
| Summary | fragment capitalized like sentence, not `@return foo` only |
| Tags order | `@param`, `@return`, `@throws`, `@deprecated` |

## Anti-patterns

- `import java.util.*`
- Empty `catch (Exception e) {}`
- `mField` Hungarian prefixes
- Local `final` variables styled as `UPPER_SNAKE_CASE`
- Splitting overload groups with unrelated members
- `@return the id` one-liner without summary sentence

## Skill trace

| Artifact | Role |
|---|---|
| `java-style-formatting-imports.md` | layout, braces, imports |
| `java-style-naming-types.md` | classes, constants, acronyms |
| `java-style-exceptions-practices.md` | override, catch, static, equals |
| `java-style-javadoc-public-api.md` | visible API documentation |
| `java-coding-practices` | application skill |
