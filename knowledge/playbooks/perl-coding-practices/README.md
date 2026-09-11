---
title: perl-coding-practices
summary: Use when authoring or reviewing Perl, v5.36/strict/warnings, 4-space aligned layout, snake_case and Mixed::Case modules, 3-arg open, explicit subs/I/O, anti-pattern avoidance, and perlcritic/perltidy/prove in CI.
kind: playbook
---

# Perl Coding Practices

Application skill for Perl style. When project adopts PBP/perltidy profile, follow that formatter config first.

## Core Principle

Perl maintainability is **lexical scope + checked I/O**, strict warnings on, 3-arg open, explicit subs, avoid indirect objects and void map/grep.

## When to Use / NOT

- Perl scripts, `.pm` modules, CPAN-style distributions, Mojolicious/Dancer apps.
- Setting up perlcritic, perltidy, prove/t harness in CI.

**NOT when:**

- Raku (Perl 6), a different language.
- Generated `.pm` stubs, validate generators.

## Workflow

1. **Layout**, indent, braces, alignment.
2. **Scope**, v5.36, my, naming.
3. **Subs/I/O**, open, args, returns.
4. **Anti-patterns**, OO, loops, regex.
5. **Verify**, perlcritic, perltidy, prove on changed files.

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
