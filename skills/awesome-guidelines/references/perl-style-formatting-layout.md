<!-- capsule-v2 -->
# Formatting and layout — do blocks align and chunks breathe?

**Source:** perlstyle §layout aesthetics. **Question:** Does closing `}` line up with its controlling keyword?

## Layout seam
**Path/Symbol:** `.pl`/`.pm` scripts and modules.
**Signature:** 4-space indent; uncuddled `else`; aligned closing braces.
**Data Shape:** vertically aligned related assignments.

### Decisive pattern
```perl
use v5.36;

sub process_files {
    my ($paths, $verbose) = @_;

    foreach my $path (@{$paths}) {
        if (-f $path) {
            analyze($path);
        }
        else {
            warn "Skipping non-file $path\n";
        }
    }

    return;
}

my $idx = $ST_MTIME;
$idx   = $ST_ATIME if $opt_u;
$idx   = $ST_CTIME if $opt_c;
```

**Flow:** indent 4 spaces → put opening `{` on same line as keyword when it fits; space before `{` on multi-line BLOCK → closing `}` of multi-line BLOCK aligns with starting keyword (`if`, `sub`, `foreach`) → uncuddled `else` on its own line → blank lines between chunks doing different things → break long lines after operators (not after `and`/`or`) → align corresponding assignments vertically when it aids scanning → no space before semicolon; omit `;` on short one-line BLOCK when clear.
**Invariant:** cuddled `else`, misaligned closing brace, or unreadable unbroken lines fail perlstyle review.
**Probe:** perltidy profile; visual brace-column check.

## Punctuation seam
**Flow:** space around most operators; space inside complex subscripts; no space between function name and `(`; space after comma; use `and`/`or` to reduce `&&`/`||` parenthesis noise.
**Invariant:** padded function calls `func ( $x )` fail consistency review.
**Probe:** perltidy/perlcritic layout policies.

## Verdict
Four-space, aligned blocks, uncuddled else, vertical rhythm. Learning note: `perl-style-learning-note.md`.
