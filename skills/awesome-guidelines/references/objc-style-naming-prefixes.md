<!-- capsule-v2 -->
# Naming and prefixes — are symbols collision-safe and Apple-shaped?

**Source:** Google §Naming/Prefixes/Categories; GitHub §Categories/Declarations. **Question:** Would a new class or category method collide in the global ObjC namespace?

## Prefix seam
**Path/Symbol:** public classes, protocols, categories, globals.
**Signature:** 3+ char type prefix; PascalCase types; camelCase methods; prefixed category methods when shared.
**Data Shape:** `GTMExample`, `NSString+GTMParsing.h`, `gtm_encodedState`.

### Decisive pattern
```objc
/** An example service error domain. */
GTM_EXTERN NSString *const GTMExampleErrorDomain;

/** Sample model object. */
@interface GTMExample : NSObject
@end

/** Crash-reporting additions for view controllers. */
@interface UIViewController (GTMCrashReporting)

@property(nonatomic, setter=gtm_setUniqueIdentifier:) int gtm_uniqueIdentifier;

- (nullable NSData *)gtm_encodedState;

@end
```

**Flow:** prefix shared classes/protocols/globals with ≥3 chars (avoid Apple two-letter reservation) → PascalCase class/category/protocol names; camelCase methods and variables → acronym caps inside names (`URLWithString:`) → category files `Class+PrefixFeature.h`; shared category methods prefixed `prefix_name` → method names read as sentences; use prepositions only when parameters need clarity → accessors named for attribute (`delegate`, `height`) without `get` prefix → BOOL getter `-isGlorious` with property `glorious`.
**Invariant:** unprefixed shared category methods, `getDelegate`, or two-letter class prefixes fail review.
**Probe:** prefix audit on new public symbols; selector readability review.

## Category seam
**Flow:** name categories for focused capability, not umbrella buckets; private/testing helpers via `Class+Private` class extension.
**Invariant:** grab-bag category adding unrelated APIs fails maintainability review.
**Probe:** category file scope check.

## Verdict
Prefixed, sentence-like selectors, Apple acronym capitalization. Learning note: `objc-style-learning-note.md`.
