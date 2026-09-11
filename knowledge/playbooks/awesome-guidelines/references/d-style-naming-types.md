<!-- capsule-v2 -->
# Naming and types — do modules and symbols follow D conventions?

**Source:** D Style §Naming Conventions. **Question:** Are modules, types, and acronyms named predictably?

## Naming seam
**Path/Symbol:** modules, types, functions, constants in D code.
**Signature:** lowercase modules; PascalCase types; camelCase functions/vars.
**Data Shape:** uniform acronym casing; `_` only for keyword escape.

### Decisive pattern
```d
module myapp.http.client;

enum secondsPerMinute = 60;

enum Direction { bwd, fwd, both }

class UTFException : Exception { }

struct HttpRequest
{
    string url;
    int timeoutMsecs;
}

int doneProcessing(HttpRequest req) { ... }
```

**Flow:** modules/packages `[a-z0-9_]` → types PascalCase → functions camelCase → enum members camelCase → constants camelCase (not SCREAMING) → acronym all lower or all upper in symbol (`UTFException`, `asciiChar`) → append `_` when keyword conflict (`nothrow_`).
**Invariant:** `my_func`, `HTTPException`, or leading `_` on non-private symbols fails review.
**Probe:** naming review; grep snake_case identifiers outside module names.

## Template naming seam
```d
template isSomeType(T)
{
    enum isSomeType = is(T == SomeType);
}

template MyType(T)
{
    struct MyType { ... }
}
```

**Flow:** eponymous templates capitalize like inner symbol (type PascalCase, value camelCase) → non-eponymous templates follow general rules.
**Invariant:** template name mismatch with inner symbol kind fails review on eponymous templates.
**Probe:** template/API review checklist.

## Verdict
lowercase modules, PascalCase types, camelCase values, consistent acronyms. Learning note: `d-style-learning-note.md`.
