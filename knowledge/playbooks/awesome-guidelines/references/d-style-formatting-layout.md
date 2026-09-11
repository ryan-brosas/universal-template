<!-- capsule-v2 -->
# Formatting and layout — is whitespace and line length consistent?

**Source:** D Style §Whitespace, §Additional Requirements for Phobos. **Question:** Does layout match dstyle/Phobos probes without harming readability?

## Whitespace seam
**Path/Symbol:** D source files in application or library modules.
**Signature:** 4-space indent; spaces not tabs; one statement per line.
**Data Shape:** Allman braces in official-style trees; soft 80 / hard 120 cols.

### Decisive pattern
```d
void process(int param)
{
    if (param < 0)
    {
        handleNegative(param);
    }
    else
    {
        handlePositive(param);
    }
}
```

**Flow:** 4 columns per indent level → space after `if`/`for`/`while` → space around binary operators → braces on own line (Phobos/official) → keep lines ≤80 when practical, never >120.
**Invariant:** tab indentation, K&R braces in Phobos submissions, or lines >120 fail review.
**Probe:** dfmt / project formatter; line-length lint on changed files.

## Import seam
```d
import std.algorithm;
import std.range : zip, iota;
import myapp.util : transmogrify;
```

**Flow:** prefer local selective imports → space around `:` in selective import → sort imports lexicographically → avoid blanket `import std.stdio` when only `writeln` needed.
**Invariant:** unsorted global imports or missing space in `import m:sym` fail Phobos-style review.
**Probe:** import sorter / manual review on new modules.

## Verdict
4-space Allman layout, 80/120 columns, sorted selective imports. Learning note: `d-style-learning-note.md`.
