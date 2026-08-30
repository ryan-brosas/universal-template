<!-- capsule-v2 -->
# Constructs and portability — are types explicit, control flow braced, and system calls checked?

**Source:** GNU Coding Standards §Clean Use of C Constructs, §Calling System Functions, §Program Behavior. **Question:** Does code avoid nested-if traps, declare system interfaces correctly, and handle errors like a GNU program?

## Type and declaration seam
**Path/Symbol:** functions, locals, externs in GNU C.
**Signature:** explicit types on all objects; externs at file scope or header.
**Data Shape:** one variable per declaration line when splitting; no shadowing globals.

### Decisive pattern
```c
foo = (char *) malloc (sizeof *foo);
if (foo == NULL)
  fatal ("virtual memory exhausted");
```

**Flow:** explicitly declare types on all objects and parameters — do not omit `int` return types → place `extern` declarations near top of file or in headers — never inside functions → declare separate locals per purpose; smallest scope that covers uses → do not declare multiple variables on one continuation line — use separate lines → do not let locals/parameters shadow globals (`-Wshadow` helpful) → avoid assignment inside `if` conditions; split assignment and test → declare struct tag separately from typedef/variable declarations → team's choice on `-Wall`; do not contort code solely to silence lint/clang false positives.
**Invariant:** `extern` inside function, assignment in `if (...)`, or unbraced nested `if`/`else` fails GNU construct review.
**Probe:** grep `extern` inside function bodies; review nested conditionals for braces.

## Control-flow brace seam
```c
if (foo)
  {
    if (bar)
      win ();
    else
      lose ();
  }
```

**Flow:** when `if` contains nested `if`/`else`, always brace the inner chain → use `else if` on one line or brace nested `if` under `else` — never leave dangling-else layout.
**Invariant:** nested if/else without braces fails readability and correctness review.
**Probe:** audit nested conditionals in diff.

## Portability and errors seam
**Flow:** use Autoconf/Gnulib for portable system interfaces — do not invent your own libc function declarations → prefer standard C/POSIX where clear; GNU extensions allowed when they improve maintainability → define `_GNU_SOURCE` when compiling on GNU/glibc to catch extension name clashes → check every syscall for failure unless deliberately ignored → include `strerror` text, file name if any, and utility name in error messages → check every `malloc`/`realloc` for NULL; fatal in noninteractive tools, abort command in interactive loops → on byte I/O use `unsigned char` temporaries, not `&c` from `int c` → avoid pointer-to-integer casts unless essential → assume `int` is at least 32 bits.
**Invariant:** unchecked `malloc`, bare `stat failed` message, or handwritten `read()` declaration fails GNU reliability review.
**Probe:** grep `malloc (` without nearby NULL check; error strings missing `strerror`; build with package `./configure && make check`.

## Verdict
Explicit types, braced nested if/else, Gnulib/Autoconf interfaces, checked alloc/syscalls with rich errors. Learning note: `gnu-style-learning-note.md`.
