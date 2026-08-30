# House style examples

Every prohibited form below sits inside a fence so this file passes the
linter that it teaches.

## Before and after

```
Before: The gate fails — fix the import.
After:  The gate fails; fix the import.

Before: This actually works really well.
After:  This works.

Before: We leverage the cache to underscore speed.
After:  The cache makes lookups faster.

Before: It is important to note that retries are bounded.
After:  Retries are bounded.

Before: In conclusion, the gate is green.
After:  The gate is green.

Before: This is not only faster but also safer.
After:  This is faster and safer.

Before: We perform validation of the input payload.
After:  We validate the input payload.

Before: a robust high-availability worker queue configuration system
After:  the worker queue config
```

## Technical contrast that stays

Contrast carrying technical meaning is good writing, not a violation:

```
Use the thread ID, not the comment ID.

Allowed:  setuid binaries
Rejected: shell scripts with the setuid bit
```

## Protected content that stays exact

```
> The mentor said: hold the boundary — not the feeling.

gh pr create --title "..." --body-file /tmp/body.md

{"retry": {"max": 3, "backoff": "exponential"}}
```

The quotation, the command, and the payload keep their exact form. The
explanation around them follows the house style.
