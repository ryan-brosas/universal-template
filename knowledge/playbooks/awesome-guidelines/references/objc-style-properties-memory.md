<!-- capsule-v2 -->
# Properties and memory — is ownership explicit through init and teardown?

**Source:** Google §Cocoa Features/Copy/Initialization; GitHub §Declarations/Expressions. **Question:** Can subclasses initialize safely without retain cycles or mutable leaks?

## Property seam
**Path/Symbol:** `@interface` property lists and `@implementation` ivars.
**Signature:** explicit attributes; copy immutables; designated initializers; `_ivar` direct access in init/dealloc.
**Data Shape:** properties → `+` factories → `-init` → instance methods.

### Decisive pattern
```objc
@interface Foo : NSObject

@property(nonatomic, copy) NSString *name;
@property(nonatomic, strong) Bar *bar;

+ (instancetype)fooWithBar:(Bar *)bar;
- (instancetype)initWithBar:(Bar *)bar NS_DESIGNATED_INITIALIZER;

@end

@implementation Foo

- (instancetype)initWithBar:(Bar *)bar {
  self = [super init];
  if (self) {
    _bar = bar;
    _name = @"";
  }
  return self;
}

- (void)setName:(NSString *)name {
  _name = [name copy];
}

@end
```

**Flow:** order declarations: properties, class methods/convenience constructors, initializers, instance methods → declare memory semantics on every property (`copy` for immutable NSString/NSArray/etc.; `strong` when exposing mutable surface) → keep ivars in `.m`; underscore prefix; access ivars directly in `-init`, `-dealloc`, custom accessors → mark designated initializers (`NS_DESIGNATED_INITIALIZER`); override superclass designated inits → avoid `+new`; do not re-nil/zero ivars redundantly in init → in init/dealloc avoid messaging `self` for overridable methods; use direct ivar ops → use dot syntax only for properties, not general methods → copy potentially mutable arguments before async retain; setter/init copy NSString/NSArray/etc.
**Invariant:** `@synthesize` without compiler need, property access of overridable `self` in `-init`, or returning mutable where immutable contract promised fails review.
**Probe:** ARC/copy audit; designated-init annotation grep; ivar vs dot usage in init/dealloc.

## Literal seam
**Flow:** prefer `@[]`, `@{}`, `@42`, boxed `@(flag)` over verbose constructors; explicit comparisons except `BOOL`.
**Invariant:** verbose `[[NSArray alloc] initWithObjects:…]` where literal suffices fails modern style review.
**Probe:** literal modernization spot check.

## Verdict
Copy-strong semantics, designated init chain, ivar-safe lifecycle. Learning note: `objc-style-learning-note.md`.
