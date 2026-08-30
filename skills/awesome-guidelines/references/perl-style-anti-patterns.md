<!-- capsule-v2 -->
# Anti-patterns — are objects, loops, and regexes modern Perl?

**Source:** perl-begin bad-elements list; perlstyle §grep/map/regex. **Question:** Would a maintainer hit indirect-object or void-map surprises?

## Object/control seam
**Path/Symbol:** OO construction, loops, list operators.
**Signature:** `Class->new`; no prototypes; no void map/grep.
**Data Shape:** `foreach`/`while` with named iterators.

### Decisive pattern
```perl
use v5.36;

use MyApp::Widget;

sub find_active {
    my ($widgets) = @_;

    foreach my $widget (@{$widgets}) {
        return $widget if $widget->is_active;
    }

    return;
}

my $widget = MyApp::Widget->new(name => 'main');
my @active = grep { $_->is_active } @{$widgets};  # use return value
```

**Flow:** construct with `MyClass->new(...)` never indirect `new MyClass …` → do not use subroutine prototypes → avoid C-style `for (my $i=0; $i<@a; $i++)` when `foreach my $e (@a)` or `0..$#a` suffices → never map/grep/backticks in void context → localize `$_` only in short blocks; name loop variables otherwise → use `$ref->[$i]` / `$ref->{$k}` not `$$ref[$i]` → replace magic numbers with named constants → use `chomp` not `chop`.
**Invariant:** indirect object syntax, void `map {}`, or long-block `$_` fails perl-begin review.
**Probe:** perlcritic ProhibitIndirectSyntax; void map/grep grep.

## Regex/module seam
**Flow:** hairy regexes use `/x` or `/xx` with whitespace; avoid `/` delimiter when pattern contains slashes → do not interpolate raw strings into regex — use `\Q...\E` or regcomp → don't parse XML/JSON/CSV with regex alone → use CPAN modules (IO::Socket, File::Find, Path::Tiny) instead of reinventing → document public subs with Pod (`=head`, `C<>` for code tokens) consistently.
**Invariant:** structured-data regex parser or undocumented exported sub fails maintainability review.
**Probe:** Pod coverage on `@EXPORT_OK`; regex /x on complex patterns.

## Verdict
Direct constructors, named iterators, valued map/grep, module-backed I/O, Pod docs. Learning note: `perl-style-learning-note.md`.
