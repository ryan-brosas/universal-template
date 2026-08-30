<!-- capsule-v2 -->
# Comments and conditionals — is every function, static, and #endif documented in GNU English style?

**Source:** GNU Coding Standards §Commenting Your Work. **Question:** Do files, functions, static globals, and preprocessor branches meet GNU comment conventions?

## File and function seam
**Path/Symbol:** top of each `.c`; comment block before each function.
**Signature:** English; complete sentences; two spaces after period; args/return documented.
**Data Shape:** main file opens with one-line program purpose; each file notes name + role.

### Decisive pattern
```c
/* fmt - filter for simple filling of text.  */

/* Set *LEN to the number of bytes in BUF.  Return zero on success.
   If BUF is NULL, store nothing but still set *LEN.  */
int
measure (char *buf, size_t *len)
{
  ...
}
```

**Flow:** start program's main source file with brief purpose comment → begin every source file with file name and overall purpose → write comments in English → document each function: behavior, arguments (including nonstandard uses), return value meaning → use argument names in prose; write value references in UPPER_CASE (`NODE_NUM`) while identifiers stay lowercase → use complete sentences; capitalize first word; two spaces after sentence-ending period → do not restate function name in comment unless comment is very long → comment each static variable with meaning of zero vs nonzero (or analogous states).
**Invariant:** function lacking arg/return documentation or comments not in English fails GNU documentation review.
**Probe:** spot-check new functions for `@param`-level detail in block comments; sentence spacing scan.

## Preprocessor seam
```c
#ifdef HAVE_FOO
  ...
#else /* not HAVE_FOO */
  ...
#endif /* not HAVE_FOO */

#ifndef HAVE_FOO
  ...
#endif /* not HAVE_FOO */
```

**Flow:** every `#endif` gets a comment stating the condition and its sense — except short, non-nested conditionals → `#else` comments describe the condition and sense of following code → for `#ifndef`, follow inverted-sense examples in the standards (e.g. `#endif /* not foo */` when matching `#ifndef foo`).
**Invariant:** nested `#if` without `#endif /* condition */` fails conditional readability review.
**Probe:** grep `#endif` lines missing `/*`; verify nested blocks annotated.

## Verdict
English function/file/static comments, two-space sentences, annotated `#endif` sense. Learning note: `gnu-style-learning-note.md`.
