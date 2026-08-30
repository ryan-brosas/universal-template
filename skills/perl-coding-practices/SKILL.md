---
name: perl-coding-practices
description: "Use when authoring or reviewing Perl — v5.36/strict/warnings, 4-space aligned layout, snake_case and Mixed::Case modules, 3-arg open, explicit subs/I/O, anti-pattern avoidance, and perlcritic/perltidy/prove in CI."
disable-model-invocation: true
---

# Perl Coding Practices

Application skill for Perl style learning (`awesome-guidelines` deep ingest). When project adopts PBP/perltidy profile, follow that formatter config first.

## Core Principle

Perl maintainability is **lexical scope + checked I/O** — strict warnings on, 3-arg open, explicit subs, avoid indirect objects and void map/grep.

## When to Use / NOT

- Perl scripts, `.pm` modules, CPAN-style distributions, Mojolicious/Dancer apps.
- Setting up perlcritic, perltidy, prove/t harness in CI.

**NOT when:**

- Raku (Perl 6) — different language foundations.
- Generated `.pm` stubs — validate generators.

## Workflow

1. **Layout** — indent, braces, alignment (`perl-style-formatting-layout.md`).
2. **Scope** — v5.36, my, naming (`perl-style-strict-scoping.md`).
3. **Subs/I/O** — open, args, returns (`perl-style-subs-io.md`).
4. **Anti-patterns** — OO, loops, regex (`perl-style-anti-patterns.md`).
5. **Verify** — perlcritic, perltidy, prove on changed files.

## Red Flags

- Missing `use strict`/`use warnings` or `use v5.36`
- Global `-w` or `$^W`
- Tab/mixed indent fighting 4-space perlstyle
- Misaligned closing brace on multi-line BLOCK
- Cuddled `else`
- Two-arg or bareword `open`
- Unchecked open/close/system return
- Bareword filehandles
- `foreach (<$fh>)` line iteration
- `` `cat $file` `` slurp
- `&sub()` calls without cause
- Subroutine prototypes
- `$_[n]` argument indexing
- Flattening arrays/hashes into `@_` at call site
- Missing explicit `return` on non-trivial subs
- Indirect object notation (`new Class`)
- `$$ref[$i]` dereference
- C-style index `for` when foreach suffices
- Void `map`/`grep`/backticks
- Overuse of `$_` in long blocks
- `chop` instead of `chomp`
- Magic numbers
- Lowercase package/module names
- Variable named `file`
- snake_case smashed words (`@namesofpresidents`)
- Predeclaring all vars at block top
- Non-lexical loop iterator
- Parsing structured data with regex only
- Hairy regex without `/x`
- Undocumented exported subs (missing Pod)
- Switch.pm in new code
- String `eval` misuse
- Duplicate code / long subs without extraction

## Verification

- `perlcritic --severity 3` (or project `.perlcriticrc`) on changed paths
- `perltidy -b -bext='/'` or project profile dry-run
- `prove -l t/` or project test harness
- Head-of-file strict/v5.36 audit
- Capsule checklist on open-or-die and indirect-object grep

## Skill Result Contract

```xml
<skill_result>
  <skill>perl-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>pl/pm diff, perlcritic/perltidy/prove output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>global leak, open injection, indirect object bug, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/perl-style-learning-note.md`
- `awesome-guidelines/references/perl-style-formatting-layout.md`
- `awesome-guidelines/references/perl-style-strict-scoping.md`
- `awesome-guidelines/references/perl-style-subs-io.md`
- `awesome-guidelines/references/perl-style-anti-patterns.md`
