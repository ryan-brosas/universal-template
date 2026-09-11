<!-- capsule-v2 -->
# Strict pragmas and scoping — is every binding lexical and warned?

**Source:** perlstyle §strict/warnings; perl-begin §no-strict, §declaring_all_vars_at_top. **Question:** Would a typo create a new global instead of failing fast?

## Pragma seam
**Path/Symbol:** file headers and variable declarations.
**Signature:** `use v5.36;` or strict+warnings; `my` at innermost use.
**Data Shape:** `$snake_case` locals; `Package::Module` names.

### Decisive pattern
```perl
use v5.36;

package MyApp::Parser;

use strict;
use warnings;

sub parse_line {
    my ($line) = @_;

    my $token_count = 0;
    while ($line =~ /\S+/g) {
        $token_count++;
    }

    return $token_count;
}
```

**Flow:** start every file with `use v5.36;` or `use strict; use warnings;` → never use `-w` or `$^W` for project-wide warnings → disable warnings/strict only in narrow blocks with documented reason → declare with `my` at first use in innermost scope, not predeclare all vars at subroutine top → use `foreach my $item (@items)` / `while (my $line = <$fh>)` not assign-from-`$_` → locals `$names_with_underscores`; modules/packages `Mixed::Case` starting uppercase → subs/methods lowercase; leading `_` for internal helpers → constants `$ALL_CAPS` sparingly.
**Invariant:** missing strict/warnings, global `-w`, or predeclared unused block locals fail review.
**Probe:** `use strict` grep head of `.pm`/`.pl`; perlcritic ProhibitBarewordFilehandles companion checks.

## Naming seam
**Flow:** mnemonic identifiers; avoid `$a`/`$b` outside sort blocks; don't name variables `file` — use `$input_fh` / `$filename`.
**Invariant:** ambiguous `file` variable or lowercase `package mytool;` fails review.
**Probe:** package name capitalization audit.

## Verdict
v5.36/strict/warnings, my-at-use, snake_case, Mixed::Case modules. Learning note: `perl-style-learning-note.md`.
