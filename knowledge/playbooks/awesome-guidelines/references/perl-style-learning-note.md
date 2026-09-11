# Perl style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `perl-style-*.md` capsules, `perl-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [perlstyle](https://perldoc.perl.org/perlstyle) (primary) | `use v5.36` or strict/warnings; 4-column indent; closing brace aligns with keyword; uncuddled else; check syscalls; `/x` regexes; `and`/`or`; Pod docs; mnemonic snake_case; lowercase subs |
| [Perl Elements to Avoid](http://perl-begin.org/tutorials/bad-elements/) (secondary) | no strict; 2/3-arg open with lexical fh; no `&sub`; declare `my` at use; no prototypes; no indirect object; no `$_` overuse; named params; explicit return; uppercase modules; avoid magic numbers, slurp, C-style for |

**Not duplicated here:** Damian Conway *Perl Best Practices* book — overlaps perlstyle; cite project PBP/perltidy config when adopted.

## Mental model

Maintainable Perl is **lexical scope + explicit I/O + readable punctuation**:

1. **Pragmas** — `use v5.36` (or strict/warnings); never global `-w`/`$^W`.
2. **Layout** — 4-space indent; brace alignment; blank lines between chunks; vertical alignment for related lines.
3. **Scope/naming** — `my` at innermost use; `$snake_case`; `Package::Name` modules; leading `_` for internal.
4. **Subs/I/O** — 3-arg `open my $fh, '<', $path`; unpack `@_`/shift; named hash args when long; explicit `return`.
5. **Anti-patterns** — no indirect objects, prototypes, void map/grep, barewords, magic numbers, regex parse of structured data.

## Decision tables

### Pragmas & scope

| Topic | Rule |
|---|---|
| Baseline | `use v5.36;` or `use strict; use warnings;` every file |
| Disable | scoped `no warnings`/`no strict` with reason only |
| Avoid | `-w`, `$^W` |
| Variables | `my` at first use, innermost scope |
| Loop vars | `foreach my $x (@xs)` not predeclared `$x` |
| Globals | package globals rare; prefer modules + exports |
| Internal | leading `_` on private subs |

### Layout (perlstyle)

| Topic | Rule |
|---|---|
| Indent | 4 columns |
| Braces | opening `{` same line as keyword when fits; space before `{` on multi-line BLOCK |
| Close brace | aligns with starting keyword |
| Else | uncuddled |
| Operators | spaces around most; space inside complex subscripts |
| Calls | no space before `(` after function name |
| Lines | break after operators; align corresponding items |
| Paragraphs | blank lines between logical chunks |

### Naming

| Entity | Convention |
|---|---|
| Locals | `$var_names_like_this` |
| Constants | `$ALL_CAPS_HERE` (avoid clash with perl vars) |
| Package globals | `$Some_Caps_Here` sparingly |
| Functions/methods | lowercase `as_string()` |
| Modules | `Mixed::Case` (not lowercase pragma names) |
| Filehandles | `$input_fh`, `$output_fn` not `$file` |

### Subs, I/O, errors

| Case | Rule |
|---|---|
| open | `open my $fh, '<', $path or die "... $!"` |
| Filehandles | lexical `my $fh`; no bareword FH |
| Sub calls | `foo(@args)` not `&foo(@args)` |
| Args | `my ($a,$b)=@_` or shift; not `$_[0]` indexing |
| Many args | hash ref named parameters |
| Arrays/hashes to subs | pass refs, don't flatten into `@_` |
| Return | explicit `return` on non-trivial subs |
| Syscalls | check return; die/warn with `$!` to STDERR |
| Lines | `while (my $line = <$fh>)` not `foreach (<$fh>)` |
| Slurp | Path::Tiny or local `$/` pattern, not `` `cat` `` |

### Anti-patterns (perl-begin)

| Avoid | Prefer |
|---|---|
| Prototypes | plain subs; Devel::Declare if needed |
| Indirect object | `Class->new(...)` |
| `$$ref[$i]` | `$ref->[$i]` |
| C-style `for ($i=0;…)` | `foreach my $e (@a)` or `0..$#a` |
| Void map/grep/backticks | foreach / system with checks |
| `$_` in long blocks | named loop variable |
| chop | chomp |
| Magic numbers | named constants |
| `//` comments in published code | `#` or Pod |
| Parsing XML/JSON with regex | proper modules |
| Switch.pm, bareword filehandles | given/when module choice; lexical fh |
| Predeclare all vars at top | declare at use |

## Skill trace

| Artifact | Role |
|---|---|
| `perl-style-formatting-layout.md` | indent, braces, alignment |
| `perl-style-strict-scoping.md` | v5.36, my, naming |
| `perl-style-subs-io.md` | open, args, returns, errors |
| `perl-style-anti-patterns.md` | perl-begin traps, regex/modules |
| `perl-coding-practices/SKILL.md` | perlcritic/perltidy/prove in CI |
