<!-- capsule-v2 -->
# Indentation and braces — does layout pass kernel tab/K&R rules?

**Source:** Linux kernel coding style §1–3. **Question:** Are tabs used for indent, lines ≤80 cols, and brace placement kernel-correct?

## Tab indent seam
**Path/Symbol:** `.c`/`.h` in kernel tree (not Kconfig/comments).
**Signature:** tab indents (8-char depth); no space-based code indent.
**Data Shape:** `scripts/Lindent` / `indent -kr -i8`; EditorConfig kernel profile.

### Decisive pattern
```c
switch (suffix) {
case 'G':
case 'g':
	mem <<= 30;
	break;
case 'K':
case 'k':
	mem <<= 10;
	fallthrough;
default:
	break;
}

int function(int x)
{
	body_of_function();
}
```

**Flow:** indent exclusively with tabs (8-character tab stops) — never spaces for code indentation → treat >3 nesting levels as design smell → limit lines to 80 columns; wrap long expressions sensibly; align continuations under an opening `(` when breaking arg lists → never break user-visible strings (printk, etc.) that must remain grep-stable → for control flow (`if`/`switch`/`for`/`while`/`do`), put opening `{` at end of header line and closing `}` on its own line → for functions, place opening `{` on the next line after the signature → align `case` labels with `switch` (no extra case indent) → use `fallthrough;` for intentional case fall-through → do not put multiple statements or assignments on one line; do not use comma tricks instead of braces → remove trailing whitespace on every line.
**Invariant:** space-indented code body, double-indented `case` labels, or function `{` on header line fails kernel layout review.
**Probe:** `grep -P '^ +[^ ]'` on changed C (leading spaces in code); checkpatch `--strict`; visual 80-col scan.

## Brace minimization seam
**Flow:** omit braces only when a single simple statement per branch and both branches symmetric → if one branch needs braces, brace both → brace loops containing more than one simple statement.
**Invariant:** asymmetric single-line branch beside multi-statement branch without braces fails readability review.
**Probe:** review `if`/`else` pairs in diff for brace symmetry rule.

## Verdict
Tab indent, 80 columns, K&R control braces, function brace next line, switch/case aligned. Learning note: `linux-kernel-style-learning-note.md`.
