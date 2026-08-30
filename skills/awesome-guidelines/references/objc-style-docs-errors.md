<!-- capsule-v2 -->
# Documentation and errors — is the public surface documented and failures NSError-shaped?

**Source:** Google §Declaration Comments/Exceptions; GitHub §Documentation/Exceptions. **Question:** Can a consumer know nil rules and failure modes without reading implementations?

## Documentation seam
**Path/Symbol:** public headers and `#pragma mark` sections in `.m`.
**Signature:** Doxygen adjacent comments; grouped marks; NSError out-params.
**Data Shape:** Tomdoc/Doxygen blocks on every public method.

### Decisive pattern
```objc
#pragma mark Lifecycle

/**
 * Creates a Foo configured with the given bar.
 *
 * @param bar Required bar instance. Must not be nil.
 * @return Initialized Foo, or nil if @c bar is invalid.
 */
+ (instancetype)fooWithBar:(Bar *)bar;

#pragma mark Operations

/**
 * Performs work using @c input.
 *
 * @param input Text to process. Nil returns NO and sets @c error.
 * @param error Error out-parameter on failure.
 * @return YES when work completes.
 */
- (BOOL)doWorkWithInput:(NSString *)input error:(NSError **)error;
```

**Flow:** document every non-trivial `@interface`, property, and public method with Doxygen (`/** … */`, `@param`, `@return`) → state whether object parameters accept `nil` → use `#pragma mark` to group properties, lifecycle, drawing, protocol conformances, superclass overrides → wrap comments at ~80 chars when using Tomdoc-style (GitHub) → explain tricky implementation only in `.m`; keep declaration comments in headers → signal failures with `NSError **` parameters; reserve `@throw` for programmer errors, not control flow → prefer object literals and boxed expressions in examples and code.
**Invariant:** undocumented exported selector, silent nil acceptance, or exception-driven normal failures fails API review.
**Probe:** header doc coverage grep; NSError usage on failure paths; exception flow audit.

## Block seam
**Flow:** space between block return type and name; omit void arg lists when empty; name block parameters unless immediately used inline.
**Invariant:** undocumented complex block typedef on public API fails review.
**Probe:** block typedef doc spot check.

## Verdict
Doxygen headers, pragma structure, NSError errors, no exception flow control. Learning note: `objc-style-learning-note.md`.
