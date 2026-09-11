<!-- capsule-v2 -->
# Subroutines and I/O — are opens safe and failures checked?

**Source:** perlstyle §readability/errors; perl-begin §open-function-style, §explicit_return, §subroutine-arguments. **Question:** Do syscalls die with context and subs avoid `@_` index fragility?

## I/O seam
**Path/Symbol:** file/process opens and read loops.
**Signature:** 3-arg `open my $fh`; `or die` with `$!`; `while` line read.
**Data Shape:** lexical filehandles only.

### Decisive pattern
```perl
use v5.36;

sub read_lines {
    my ($filename) = @_;

    open my $input_fh, '<', $filename
        or die "Cannot open '$filename' for reading: $!\n";

    my @lines;
    while (my $line = <$input_fh>) {
        chomp $line;
        push @lines, $line;
    }

    close $input_fh
        or warn "Cannot close '$filename': $!\n";

    return \@lines;
}
```

**Flow:** always `open my $fh, '<', $path` three-argument form → never bareword filehandles or two-arg `"<$path"` open → check every open/close/rename and die/warn with program context + `$!` to STDERR → read files with `while (my $line = <$fh>)` not `foreach (<$fh>)` → slurp only deliberately (Path::Tiny / local `$/`), never `` `cat $file` `` → prefer here-documents over repeated prints for long text.
**Invariant:** two-arg open, unchecked syscall, or foreach-on-handle slurp fails review.
**Probe:** perlcritic InputOutput::ProhibitTwoArgOpen; open-or-die grep.

## Subroutine seam
**Flow:** call `foo(@args)` without leading `&` → unpack args via `my (@args) = @_` or `shift`, not `$_[3]` → pass arrays/hashes as refs → use named hash-ref parameters when arity grows → explicit `return` on non-trivial subs → use `Getopt::Long` for CLI beyond simple `@ARGV` unpack.
**Invariant:** `&foo`, prototype declarations, or `$_[n]` indexing in maintained code fails review.
**Probe:** prototype grep; sub argument style spot check.

## Verdict
Lexical 3-arg open, checked syscalls, explicit sub args/returns. Learning note: `perl-style-learning-note.md`.
